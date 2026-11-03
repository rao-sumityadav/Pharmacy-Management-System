import unittest
from datetime import date, timedelta
from app import create_app
from config import TestConfig
from models import db, User, Medicine, Customer, Bill
from services.billing_service import BillingService, BillingError

class TestBillingAndInventory(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed minimal test user
        self.pharmacist = User(
            user_code="PHR-TEST",
            name="Test Pharmacist",
            email="test@pharma.com",
            role="pharmacist"
        )
        self.pharmacist.set_password("pass123")
        db.session.add(self.pharmacist)

        # Seed fresh in-stock medicine
        self.med_fresh = Medicine(
            medicine_code="MED-TEST-1",
            name="Test Amoxicillin",
            category="Antibiotics",
            batch_number="BTH-001",
            quantity=50,
            unit_price=10.00,
            cost_price=6.00,
            manufacturer="Test Labs",
            manufacturing_date=date.today() - timedelta(days=60),
            expiry_date=date.today() + timedelta(days=300),
            reorder_threshold=10
        )

        # Seed expired medicine
        self.med_expired = Medicine(
            medicine_code="MED-TEST-2",
            name="Test Expired Paracetamol",
            category="Analgesics",
            batch_number="BTH-EXP",
            quantity=20,
            unit_price=5.00,
            cost_price=2.50,
            manufacturer="Test Labs",
            manufacturing_date=date.today() - timedelta(days=400),
            expiry_date=date.today() - timedelta(days=10),
            reorder_threshold=5
        )

        # Seed discontinued medicine
        self.med_discontinued = Medicine(
            medicine_code="MED-TEST-3",
            name="Test Discontinued Medicine",
            category="General",
            batch_number="BTH-DISC",
            quantity=15,
            unit_price=8.00,
            cost_price=4.00,
            manufacturer="Test Labs",
            manufacturing_date=date.today() - timedelta(days=100),
            expiry_date=date.today() + timedelta(days=200),
            is_discontinued=True
        )

        db.session.add_all([self.med_fresh, self.med_expired, self.med_discontinued])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_billing_calculation(self):
        """Test calculation of subtotal, discount, tax (GST), and total."""
        items = [
            {"unit_price": 20.0, "quantity": 2},  # 40.0
            {"unit_price": 10.0, "quantity": 1}   # 10.0
        ]
        # Subtotal: 50.0. Discount 10%: 5.0. Taxable: 45.0. Tax 5%: 2.25. Total: 47.25.
        totals = BillingService.calculate_bill_totals(items, discount_percent=10.0, tax_percent=5.0)
        self.assertEqual(totals["subtotal"], 50.00)
        self.assertEqual(totals["discount_amount"], 5.00)
        self.assertEqual(totals["taxable_amount"], 45.00)
        self.assertEqual(totals["tax_amount"], 2.25)
        self.assertEqual(totals["total_amount"], 47.25)

    def test_atomic_stock_deduction(self):
        """Test that a successful sale deducts exact units from stock."""
        initial_stock = self.med_fresh.quantity
        requested_qty = 5

        bill = BillingService.create_bill(
            customer_name="Test Customer",
            customer_phone="+91 9999999999",
            items_data=[{"medicine_id": self.med_fresh.id, "quantity": requested_qty}],
            discount_percent=0.0,
            tax_percent=5.0,
            payment_method="cash",
            created_by_user_id=self.pharmacist.id
        )

        self.assertIsNotNone(bill)
        self.assertIsNotNone(bill.bill_number)
        
        # Verify stock was deducted
        med_refreshed = Medicine.query.get(self.med_fresh.id)
        self.assertEqual(med_refreshed.quantity, initial_stock - requested_qty)

    def test_negative_stock_prevention(self):
        """Test that purchasing more than available stock fails and raises BillingError."""
        initial_stock = self.med_fresh.quantity
        excess_qty = initial_stock + 10  # 60 requested, only 50 available

        with self.assertRaises(BillingError) as ctx:
            BillingService.create_bill(
                customer_name="Test Customer",
                customer_phone="+91 9999999999",
                items_data=[{"medicine_id": self.med_fresh.id, "quantity": excess_qty}],
                created_by_user_id=self.pharmacist.id
            )

        self.assertIn("Insufficient stock", str(ctx.exception))

        # Ensure stock was NOT deducted
        med_refreshed = Medicine.query.get(self.med_fresh.id)
        self.assertEqual(med_refreshed.quantity, initial_stock)

    def test_expired_medicine_blocked(self):
        """Test that expired medicines are strictly blocked from being sold."""
        with self.assertRaises(BillingError) as ctx:
            BillingService.create_bill(
                customer_name="Test Customer",
                customer_phone="+91 9999999999",
                items_data=[{"medicine_id": self.med_expired.id, "quantity": 1}],
                created_by_user_id=self.pharmacist.id
            )

        self.assertIn("CRITICAL: Medicine", str(ctx.exception))
        self.assertIn("expired", str(ctx.exception).lower())

    def test_discontinued_medicine_blocked(self):
        """Test that soft-deleted/discontinued medicines cannot be sold."""
        with self.assertRaises(BillingError) as ctx:
            BillingService.create_bill(
                customer_name="Test Customer",
                customer_phone="+91 9999999999",
                items_data=[{"medicine_id": self.med_discontinued.id, "quantity": 1}],
                created_by_user_id=self.pharmacist.id
            )

        self.assertIn("discontinued", str(ctx.exception).lower())

if __name__ == "__main__":
    unittest.main()
