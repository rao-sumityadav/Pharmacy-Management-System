from datetime import datetime, date
from models import db, Medicine, PurchaseOrder, MedicineReturn, Reservation

class InventoryService:
    @staticmethod
    def adjust_stock(medicine_id, new_quantity, reason="Manual inventory adjustment"):
        """
        Adjust stock quantity directly with audit trail.
        """
        medicine = Medicine.query.get(medicine_id)
        if not medicine:
            raise ValueError("Medicine not found.")

        old_quantity = medicine.quantity
        medicine.quantity = max(0, int(new_quantity))
        medicine.updated_at = datetime.utcnow()

        # If restocked from 0 to positive, notify pending reservations
        if old_quantity <= 0 and medicine.quantity > 0:
            InventoryService.check_and_notify_reservations(medicine.id)

        db.session.commit()
        return medicine

    @staticmethod
    def receive_purchase_order(po_id):
        """
        Mark a purchase order as received and automatically replenish stock.
        """
        po = PurchaseOrder.query.get(po_id)
        if not po:
            raise ValueError("Purchase order not found.")
        if po.status == "received":
            raise ValueError("Purchase order has already been received.")

        medicine = Medicine.query.get(po.medicine_id)
        if not medicine:
            raise ValueError("Associated medicine not found.")

        old_stock = medicine.quantity
        medicine.quantity += po.quantity
        medicine.updated_at = datetime.utcnow()

        po.status = "received"
        po.received_date = date.today()

        # Check pending reservations
        if old_stock <= 0 and medicine.quantity > 0:
            InventoryService.check_and_notify_reservations(medicine.id)

        db.session.commit()
        return po

    @staticmethod
    def check_and_notify_reservations(medicine_id):
        """
        Find pending reservations for this medicine and mark as notified.
        """
        reservations = Reservation.query.filter_by(
            medicine_id=medicine_id, 
            status="pending"
        ).all()

        for res in reservations:
            res.status = "notified"

    @staticmethod
    def process_quality_verification(return_id, verified_by_user_id, status, notes=""):
        """
        Admin/Pharmacist quality verification on returned medicine.
        If approved_restocked -> adds quantity back to sellable stock.
        If rejected_damaged -> keeps item quarantined / written off.
        """
        ret = MedicineReturn.query.get(return_id)
        if not ret:
            raise ValueError("Return record not found.")

        if ret.quality_status != "pending_verification":
            raise ValueError(f"Return is already in '{ret.quality_status}' status.")

        if status not in ["approved_restocked", "rejected_damaged"]:
            raise ValueError("Invalid verification status.")

        medicine = Medicine.query.get(ret.medicine_id)
        if not medicine:
            raise ValueError("Associated medicine not found.")

        ret.quality_status = status
        ret.verification_notes = notes
        ret.verified_by_id = verified_by_user_id
        ret.verified_at = datetime.utcnow()

        if status == "approved_restocked":
            medicine.quantity += ret.quantity
            medicine.updated_at = datetime.utcnow()

        db.session.commit()
        return ret
