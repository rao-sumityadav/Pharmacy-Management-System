from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    user_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="pharmacist")  # admin, pharmacist
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    shop_name = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bills = db.relationship("Bill", backref="creator", lazy="dynamic")
    purchase_orders = db.relationship("PurchaseOrder", backref="creator", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_pharmacist(self):
        return self.role == "pharmacist"

    def to_dict(self):
        return {
            "id": self.id,
            "user_code": self.user_code,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "phone": self.phone,
            "address": self.address,
            "shop_name": self.shop_name,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None
        }


class Medicine(db.Model):
    __tablename__ = "medicines"

    id = db.Column(db.Integer, primary_key=True)
    medicine_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    generic_name = db.Column(db.String(150))
    category = db.Column(db.String(100), nullable=False, index=True)
    batch_number = db.Column(db.String(50), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_price = db.Column(db.Float, nullable=False)  # Selling price
    cost_price = db.Column(db.Float, nullable=False, default=0.0)  # Purchase price for profit analysis
    manufacturer = db.Column(db.String(150), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False, index=True)
    reorder_threshold = db.Column(db.Integer, default=10)
    rack_location = db.Column(db.String(50), default="General")
    is_discontinued = db.Column(db.Boolean, default=False)  # Soft-delete flag
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bill_items = db.relationship("BillItem", backref="medicine", lazy="dynamic")
    purchase_orders = db.relationship("PurchaseOrder", backref="medicine", lazy="dynamic")
    returns = db.relationship("MedicineReturn", backref="medicine", lazy="dynamic")
    reservations = db.relationship("Reservation", backref="medicine", lazy="dynamic")

    @property
    def is_expired(self):
        return self.expiry_date < date.today()

    @property
    def days_until_expiry(self):
        return (self.expiry_date - date.today()).days

    @property
    def is_expiring_soon(self):
        delta = self.days_until_expiry
        return not self.is_expired and 0 <= delta <= 30

    @property
    def stock_status(self):
        if self.quantity <= 0:
            return "out-of-stock"
        elif self.quantity <= self.reorder_threshold:
            return "low-stock"
        return "in-stock"

    def to_dict(self):
        return {
            "id": self.id,
            "medicine_code": self.medicine_code,
            "name": self.name,
            "generic_name": self.generic_name or "",
            "category": self.category,
            "batch_number": self.batch_number,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "cost_price": self.cost_price,
            "manufacturer": self.manufacturer,
            "manufacturing_date": self.manufacturing_date.strftime("%Y-%m-%d") if self.manufacturing_date else "",
            "expiry_date": self.expiry_date.strftime("%Y-%m-%d") if self.expiry_date else "",
            "reorder_threshold": self.reorder_threshold,
            "rack_location": self.rack_location,
            "is_discontinued": self.is_discontinued,
            "stock_status": self.stock_status,
            "is_expired": self.is_expired,
            "is_expiring_soon": self.is_expiring_soon,
            "days_until_expiry": self.days_until_expiry
        }


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    supplier_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    contact_number = db.Column(db.String(25), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    supplied_medicines = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    purchase_orders = db.relationship("PurchaseOrder", backref="supplier", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "supplier_code": self.supplier_code,
            "name": self.name,
            "contact_number": self.contact_number,
            "email": self.email,
            "address": self.address,
            "supplied_medicines": self.supplied_medicines,
            "order_count": self.purchase_orders.count()
        }


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(25), nullable=False, index=True)
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bills = db.relationship("Bill", backref="customer_rel", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_code": self.customer_code,
            "name": self.name,
            "phone_number": self.phone_number,
            "email": self.email,
            "address": self.address,
            "bill_count": self.bills.count()
        }


class Bill(db.Model):
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(25))
    
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    tax_percent = db.Column(db.Float, default=5.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    due_amount = db.Column(db.Float, nullable=False, default=0.0)
    due_date = db.Column(db.Date, nullable=True)
    fine_amount = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(20), default="paid")  # paid, partial, due, cancelled
    payment_method = db.Column(db.String(30), default="cash")  # cash, upi, card, mock_gateway
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    items = db.relationship("BillItem", backref="bill", lazy="joined", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="bill", lazy="dynamic", cascade="all, delete-orphan")
    returns = db.relationship("MedicineReturn", backref="bill", lazy="dynamic")

    @property
    def overdue_days(self):
        if self.due_amount > 0 and self.due_date and date.today() > self.due_date:
            return (date.today() - self.due_date).days
        return 0

    def calculate_fine(self, rate_per_day=10.0):
        days = self.overdue_days
        if days > 0:
            return round(days * rate_per_day, 2)
        return 0.0

    @property
    def total_outstanding(self):
        return round(self.due_amount + self.calculate_fine(), 2)

    def to_dict(self):
        return {
            "id": self.id,
            "bill_number": self.bill_number,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "subtotal": self.subtotal,
            "discount_amount": self.discount_amount,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "paid_amount": self.paid_amount,
            "due_amount": self.due_amount,
            "due_date": self.due_date.strftime("%Y-%m-%d") if self.due_date else None,
            "overdue_days": self.overdue_days,
            "fine_amount": self.calculate_fine(),
            "total_outstanding": self.total_outstanding,
            "status": self.status,
            "payment_method": self.payment_method,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "items_count": len(self.items)
        }


class BillItem(db.Model):
    __tablename__ = "bill_items"

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    medicine_name = db.Column(db.String(150), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False, default=0.0)
    subtotal = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "medicine_id": self.medicine_id,
            "medicine_name": self.medicine_name,
            "batch_number": self.batch_number,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal
        }


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)  # cash, upi, card, mock_gateway
    amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default="success")  # success, pending, failed
    transaction_ref = db.Column(db.String(100))
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "bill_id": self.bill_id,
            "payment_method": self.payment_method,
            "amount": self.amount,
            "payment_status": self.payment_status,
            "transaction_ref": self.transaction_ref,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"

    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="ordered")  # ordered, received, cancelled
    order_date = db.Column(db.Date, default=date.today)
    received_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "po_number": self.po_number,
            "supplier_name": self.supplier.name if self.supplier else "",
            "medicine_name": self.medicine.name if self.medicine else "",
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "total_cost": self.total_cost,
            "status": self.status,
            "order_date": self.order_date.strftime("%Y-%m-%d") if self.order_date else "",
            "received_date": self.received_date.strftime("%Y-%m-%d") if self.received_date else None
        }


class MedicineReturn(db.Model):
    __tablename__ = "medicine_returns"

    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    refund_amount = db.Column(db.Float, default=0.0)
    return_reason = db.Column(db.String(255), nullable=False)
    quality_status = db.Column(
        db.String(30), 
        default="pending_verification"
    )  # pending_verification, approved_restocked, rejected_damaged
    verification_notes = db.Column(db.Text)
    verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    verifier = db.relationship("User", foreign_keys=[verified_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "return_number": self.return_number,
            "bill_number": self.bill.bill_number if self.bill else "N/A",
            "medicine_name": self.medicine.name if self.medicine else "",
            "quantity": self.quantity,
            "refund_amount": self.refund_amount,
            "return_reason": self.return_reason,
            "quality_status": self.quality_status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    reservation_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(25), nullable=False)
    customer_email = db.Column(db.String(120))
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default="pending")  # pending, notified, fulfilled, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fulfilled_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "reservation_number": self.reservation_number,
            "medicine_name": self.medicine.name if self.medicine else "",
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "quantity": self.quantity,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }


class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    rx_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(25), nullable=False)
    customer_email = db.Column(db.String(120))
    file_path = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    review_notes = db.Column(db.Text)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Relationship
    reviewer = db.relationship("User", foreign_keys=[reviewed_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "rx_number": self.rx_number,
            "customer_name": self.customer_name,
            "customer_phone": self.customer_phone,
            "file_path": self.file_path,
            "notes": self.notes,
            "status": self.status,
            "review_notes": self.review_notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M")
        }
