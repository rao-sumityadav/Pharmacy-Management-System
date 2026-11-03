from datetime import datetime, date, timedelta
import uuid
from models import db, Medicine, Bill, BillItem, Payment, Customer, User

class BillingError(Exception):
    pass

class BillingService:
    @staticmethod
    def calculate_bill_totals(items, discount_percent=0.0, tax_percent=5.0):
        """
        Calculate subtotal, discount, tax, and grand total.
        items: list of dicts with keys 'unit_price', 'quantity'
        """
        subtotal = 0.0
        for item in items:
            qty = int(item.get("quantity", 0))
            price = float(item.get("unit_price", 0.0))
            if qty <= 0:
                raise BillingError("Quantity must be greater than zero.")
            subtotal += round(qty * price, 2)

        subtotal = round(subtotal, 2)
        discount_percent = max(0.0, min(100.0, float(discount_percent or 0.0)))
        discount_amount = round(subtotal * (discount_percent / 100.0), 2)
        taxable_amount = max(0.0, subtotal - discount_amount)
        tax_percent = max(0.0, float(tax_percent if tax_percent is not None else 5.0))
        tax_amount = round(taxable_amount * (tax_percent / 100.0), 2)
        total_amount = round(taxable_amount + tax_amount, 2)

        return {
            "subtotal": subtotal,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "taxable_amount": taxable_amount,
            "tax_percent": tax_percent,
            "tax_amount": tax_amount,
            "total_amount": total_amount
        }

    @staticmethod
    def create_bill(
        customer_name,
        customer_phone,
        items_data,
        discount_percent=0.0,
        tax_percent=5.0,
        payment_method="cash",
        paid_amount=None,
        due_days=15,
        notes="",
        created_by_user_id=None
    ):
        """
        Atomic sale & bill generation with stock validation and deduction.
        """
        if not items_data or len(items_data) == 0:
            raise BillingError("Cannot create a bill with no items.")

        customer_name = (customer_name or "").strip()
        if not customer_name:
            customer_name = "Walk-in Customer"

        customer_phone = (customer_phone or "").strip()

        # Begin atomic operation
        try:
            # 1. Customer resolution or creation
            customer = None
            if customer_phone:
                customer = Customer.query.filter_by(phone_number=customer_phone).first()
                if not customer:
                    customer_code = f"CUST-{uuid.uuid4().hex[:6].upper()}"
                    customer = Customer(
                        customer_code=customer_code,
                        name=customer_name,
                        phone_number=customer_phone
                    )
                    db.session.add(customer)
                    db.session.flush()

            # 2. Validate all medicines & verify stock
            prepared_items = []
            for item in items_data:
                med_id = int(item.get("medicine_id"))
                qty = int(item.get("quantity", 0))

                if qty <= 0:
                    raise BillingError("Quantity must be at least 1.")

                # Lock the row or fetch fresh
                medicine = Medicine.query.filter_by(id=med_id).with_for_update().first()
                if not medicine:
                    raise BillingError(f"Medicine with ID {med_id} not found.")

                if medicine.is_discontinued:
                    raise BillingError(f"Medicine '{medicine.name}' is discontinued and cannot be sold.")

                # Expiry check - strict block!
                if medicine.is_expired:
                    raise BillingError(
                        f"CRITICAL: Medicine '{medicine.name}' (Batch: {medicine.batch_number}) "
                        f"expired on {medicine.expiry_date.strftime('%Y-%m-%d')} and cannot be sold!"
                    )

                # Stock check
                if medicine.quantity < qty:
                    raise BillingError(
                        f"Insufficient stock for '{medicine.name}'. "
                        f"Available: {medicine.quantity}, Requested: {qty}"
                    )

                unit_price = float(medicine.unit_price)
                line_subtotal = round(unit_price * qty, 2)

                prepared_items.append({
                    "medicine": medicine,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "cost_price": float(medicine.cost_price or 0.0),
                    "subtotal": line_subtotal
                })

            # 3. Calculate totals
            totals = BillingService.calculate_bill_totals(
                prepared_items, 
                discount_percent=discount_percent, 
                tax_percent=tax_percent
            )
            total_amount = totals["total_amount"]

            if paid_amount is None:
                paid_amount = total_amount
            else:
                paid_amount = float(paid_amount)

            if paid_amount < 0:
                raise BillingError("Paid amount cannot be negative.")

            due_amount = max(0.0, round(total_amount - paid_amount, 2))
            
            # Status determination
            if due_amount == 0.0:
                status = "paid"
                due_date = None
            elif paid_amount == 0.0:
                status = "due"
                due_date = date.today() + timedelta(days=due_days)
            else:
                status = "partial"
                due_date = date.today() + timedelta(days=due_days)

            # Bill number generation
            timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M")
            random_suffix = uuid.uuid4().hex[:4].upper()
            bill_number = f"INV-{timestamp_str}-{random_suffix}"

            # 4. Create Bill
            bill = Bill(
                bill_number=bill_number,
                customer_id=customer.id if customer else None,
                customer_name=customer_name,
                customer_phone=customer_phone,
                subtotal=totals["subtotal"],
                discount_percent=totals["discount_percent"],
                discount_amount=totals["discount_amount"],
                tax_percent=totals["tax_percent"],
                tax_amount=totals["tax_amount"],
                total_amount=total_amount,
                paid_amount=paid_amount,
                due_amount=due_amount,
                due_date=due_date,
                status=status,
                payment_method=payment_method,
                notes=notes,
                created_by_id=created_by_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(bill)
            db.session.flush()

            # 5. Create Bill Items and deduct stock atomically
            for item in prepared_items:
                medicine = item["medicine"]
                qty = item["quantity"]

                # Deduct stock
                medicine.quantity -= qty
                medicine.updated_at = datetime.utcnow()

                bill_item = BillItem(
                    bill_id=bill.id,
                    medicine_id=medicine.id,
                    medicine_name=medicine.name,
                    batch_number=medicine.batch_number,
                    quantity=qty,
                    unit_price=item["unit_price"],
                    cost_price=item["cost_price"],
                    subtotal=item["subtotal"]
                )
                db.session.add(bill_item)

            # 6. Record Payment if paid_amount > 0
            if paid_amount > 0:
                payment = Payment(
                    bill_id=bill.id,
                    payment_method=payment_method,
                    amount=paid_amount,
                    payment_status="success",
                    transaction_ref=f"TXN-{uuid.uuid4().hex[:8].upper()}",
                    notes=f"Initial payment for {bill.bill_number}"
                )
                db.session.add(payment)

            db.session.commit()
            return bill

        except Exception as e:
            db.session.rollback()
            if isinstance(e, BillingError):
                raise e
            raise BillingError(f"Billing transaction failed: {str(e)}")

    @staticmethod
    def settle_due(bill_id, payment_amount, payment_method="cash", notes=""):
        """
        Settle overdue balance and accumulated fine.
        """
        try:
            bill = Bill.query.filter_by(id=bill_id).first()
            if not bill:
                raise BillingError("Bill not found.")

            payment_amount = float(payment_amount)
            if payment_amount <= 0:
                raise BillingError("Payment amount must be greater than zero.")

            fine = bill.calculate_fine()
            total_payable = bill.due_amount + fine

            if payment_amount > total_payable:
                raise BillingError(f"Payment amount ({payment_amount}) exceeds total payable ({total_payable}).")

            # Apply payment: First towards fine, then towards principal due
            if fine > 0:
                bill.fine_amount = max(0.0, round(fine - min(fine, payment_amount), 2))
                remaining_payment = max(0.0, payment_amount - fine)
            else:
                remaining_payment = payment_amount

            bill.due_amount = max(0.0, round(bill.due_amount - remaining_payment, 2))
            bill.paid_amount = round(bill.paid_amount + payment_amount, 2)

            if bill.due_amount == 0.0:
                bill.status = "paid"
                bill.due_date = None
            else:
                bill.status = "partial"

            payment = Payment(
                bill_id=bill.id,
                payment_method=payment_method,
                amount=payment_amount,
                payment_status="success",
                transaction_ref=f"DUE-SETTLE-{uuid.uuid4().hex[:8].upper()}",
                notes=notes or f"Due settlement for {bill.bill_number}"
            )
            db.session.add(payment)
            db.session.commit()
            return bill

        except Exception as e:
            db.session.rollback()
            if isinstance(e, BillingError):
                raise e
            raise BillingError(f"Due settlement failed: {str(e)}")
