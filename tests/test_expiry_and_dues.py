import unittest
from datetime import date, timedelta, datetime
from app import create_app
from config import TestConfig
from models import db, User, Medicine, Bill, MedicineReturn, Payment
from services.inventory_service import InventoryService
from services.billing_service import BillingService

class TestExpiryAndDues(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(
            user_code="ADM-TEST",
            name="Admin Tester",
            email="admin.test@pharma.com",
            role="admin"
        )
        self.user.set_password("adminpass")
        db.session.add(self.user)

        self.medicine = Medicine(
            medicine_code="MED-EXP-1",
            name="Test Syrup",
            category="Respiratory",
            batch_number="SYR-01",
            quantity=30,
            unit_price=50.00,
            cost_price=30.00,
            manufacturer="Syrup Pharma",
            manufacturing_date=date.today() - timedelta(days=100),
            expiry_date=date.today() + timedelta(days=20),  # Expiring soon (20 days)
            reorder_threshold=10
        )
        db.session.add(self.medicine)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_expiry_status_detection(self):
        """Test properties for near-expiry and expired states."""
        # 20 days remaining should flag as expiring soon
        self.assertTrue(self.medicine.is_expiring_soon)
        self.assertFalse(self.medicine.is_expired)
        self.assertEqual(self.medicine.days_until_expiry, 20)

        # Set to expired
        self.medicine.expiry_date = date.today() - timedelta(days=2)
        db.session.commit()

        self.assertTrue(self.medicine.is_expired)
        self.assertFalse(self.medicine.is_expiring_soon)

    def test_returns_quality_verification_workflow(self):
        """
        Test that returned medicine is quarantined in 'pending_verification'
        and ONLY restocked when quality verification explicitly approves it.
        """
        initial_stock = self.medicine.quantity
        return_qty = 3

        # 1. Create Return record in pending verification
        ret = MedicineReturn(
            return_number="RET-TEST-001",
            medicine_id=self.medicine.id,
            quantity=return_qty,
            refund_amount=150.0,
            return_reason="Patient allergy",
            quality_status="pending_verification"
        )
        db.session.add(ret)
        db.session.commit()

        # Stock should NOT have changed yet!
        med_refreshed = Medicine.query.get(self.medicine.id)
        self.assertEqual(med_refreshed.quantity, initial_stock)

        # 2. Pharmacist inspects and approves
        InventoryService.process_quality_verification(
            return_id=ret.id,
            verified_by_user_id=self.user.id,
            status="approved_restocked",
            notes="Seal intact and genuine packaging verified."
        )

        # Stock should now be increased by return_qty
        med_refreshed = Medicine.query.get(self.medicine.id)
        self.assertEqual(med_refreshed.quantity, initial_stock + return_qty)

    def test_overdue_fine_calculation(self):
        """Test that credit bills overdue past due date incur Rs. 10/day fine."""
        overdue_days = 7
        due_date = date.today() - timedelta(days=overdue_days)

        bill = Bill(
            bill_number="INV-TEST-DUE",
            customer_name="Overdue Customer",
            subtotal=100.0,
            total_amount=105.0,
            paid_amount=0.0,
            due_amount=105.0,
            due_date=due_date,
            status="due"
        )
        db.session.add(bill)
        db.session.commit()

        self.assertEqual(bill.overdue_days, overdue_days)
        expected_fine = overdue_days * 10.0  # 70.0
        self.assertEqual(bill.calculate_fine(rate_per_day=10.0), expected_fine)
        self.assertEqual(bill.total_outstanding, 105.0 + expected_fine)

    def test_settle_due_with_fine(self):
        """Test settling an overdue balance with accumulated fine."""
        due_date = date.today() - timedelta(days=3)  # 3 days overdue = Rs. 30 fine
        bill = Bill(
            bill_number="INV-TEST-SETTLE",
            customer_name="Settle Customer",
            subtotal=200.0,
            total_amount=210.0,
            paid_amount=100.0,
            due_amount=110.0,
            due_date=due_date,
            status="partial"
        )
        db.session.add(bill)
        db.session.commit()

        # Total payable = 110.0 (principal) + 30.0 (fine) = 140.0
        total_payable = bill.total_outstanding
        self.assertEqual(total_payable, 140.00)

        # Settle full amount
        settled_bill = BillingService.settle_due(
            bill_id=bill.id,
            payment_amount=140.00,
            payment_method="upi",
            notes="Settled with UPI"
        )

        self.assertEqual(settled_bill.due_amount, 0.0)
        self.assertEqual(settled_bill.status, "paid")
        self.assertEqual(settled_bill.fine_amount, 0.0)

if __name__ == "__main__":
    unittest.main()
