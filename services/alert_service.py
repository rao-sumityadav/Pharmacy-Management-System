from datetime import date
from models import Medicine, Bill, MedicineReturn, Prescription, Reservation
from services.expiry_service import ExpiryService

class AlertService:
    @staticmethod
    def get_all_alerts():
        """
        Aggregate all system alerts for the in-app notification center.
        """
        alerts = []
        today = date.today()

        # 1. Expired Medicines
        expired = ExpiryService.get_expired_medicines()
        for m in expired:
            alerts.append({
                "type": "expired",
                "severity": "danger",
                "title": f"Expired: {m.name}",
                "message": f"Batch {m.batch_number} expired on {m.expiry_date.strftime('%Y-%m-%d')}. Stock: {m.quantity} units.",
                "link": f"/medicines?filter=expired",
                "created_at": m.updated_at
            })

        # 2. Expiring Soon (< 30 days)
        expiring_soon = ExpiryService.get_expiring_soon_medicines(30)
        for m in expiring_soon:
            days = m.days_until_expiry
            alerts.append({
                "type": "expiring_soon",
                "severity": "warning",
                "title": f"Expiring Soon: {m.name}",
                "message": f"Batch {m.batch_number} expires in {days} day{'s' if days != 1 else ''}. Stock: {m.quantity} units.",
                "link": f"/medicines?filter=expiring",
                "created_at": m.updated_at
            })

        # 3. Low Stock Items
        low_stock = Medicine.query.filter(
            Medicine.quantity <= Medicine.reorder_threshold,
            Medicine.is_discontinued == False
        ).all()
        for m in low_stock:
            alerts.append({
                "type": "low_stock",
                "severity": "danger" if m.quantity == 0 else "warning",
                "title": f"Low Stock: {m.name}",
                "message": f"Current stock is {m.quantity} (Threshold: {m.reorder_threshold}). Please reorder.",
                "link": f"/suppliers/purchase-orders/new?medicine_id={m.id}",
                "created_at": m.updated_at
            })

        # 4. Overdue Bills (Dues past due date)
        overdue_bills = Bill.query.filter(
            Bill.due_amount > 0,
            Bill.due_date < today
        ).all()
        for b in overdue_bills:
            fine = b.calculate_fine()
            alerts.append({
                "type": "overdue_due",
                "severity": "warning",
                "title": f"Overdue Payment: {b.bill_number}",
                "message": f"Customer: {b.customer_name}. Due: Rs. {b.due_amount:.2f} (+ Rs. {fine:.2f} fine, {b.overdue_days} days overdue).",
                "link": f"/bills/dues",
                "created_at": b.created_at
            })

        # 5. Pending Returns needing Quality Verification
        pending_returns = MedicineReturn.query.filter_by(
            quality_status="pending_verification"
        ).all()
        for r in pending_returns:
            alerts.append({
                "type": "pending_return",
                "severity": "info",
                "title": f"Return Verification: {r.return_number}",
                "message": f"{r.quantity} units of {r.medicine.name if r.medicine else 'medicine'} waiting for quality inspection.",
                "link": f"/returns",
                "created_at": r.created_at
            })

        # 6. Pending Prescriptions awaiting review
        pending_rx = Prescription.query.filter_by(status="pending").all()
        for rx in pending_rx:
            alerts.append({
                "type": "pending_prescription",
                "severity": "info",
                "title": f"New E-Prescription: {rx.rx_number}",
                "message": f"Submitted by {rx.customer_name} ({rx.customer_phone}). Needs pharmacist review.",
                "link": f"/admin/prescriptions",
                "created_at": rx.created_at
            })

        # 7. Restocked medicines with customer reservations
        notified_res = Reservation.query.filter_by(status="notified").all()
        for res in notified_res:
            alerts.append({
                "type": "restocked_reservation",
                "severity": "success",
                "title": f"Restocked Reservation: {res.medicine.name if res.medicine else 'Medicine'}",
                "message": f"{res.customer_name} ({res.customer_phone}) has a reservation ready for fulfillment.",
                "link": f"/customer/reservations",
                "created_at": res.created_at
            })

        return alerts

    @staticmethod
    def get_alert_count():
        alerts = AlertService.get_all_alerts()
        return len(alerts)
