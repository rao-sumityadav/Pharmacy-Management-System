from datetime import datetime, date
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import Bill, Medicine, MedicineReturn, Reservation
from auth.routes import role_required
from services.expiry_service import ExpiryService

pharmacist_bp = Blueprint("pharmacist", __name__, url_prefix="/pharmacist")

@pharmacist_bp.route("/dashboard")
@login_required
@role_required(["pharmacist", "admin"])
def dashboard():
    today = date.today()
    start_of_today = datetime.combine(today, datetime.min.time())

    # Today's shift bills
    today_bills = Bill.query.filter(
        Bill.created_at >= start_of_today,
        Bill.status != "cancelled"
    ).all()
    today_sales = sum(b.total_amount for b in today_bills)

    # Low stock & expiring counts
    active_meds = Medicine.query.filter_by(is_discontinued=False).all()
    low_stock = [m for m in active_meds if 0 < m.quantity <= m.reorder_threshold]
    out_of_stock = [m for m in active_meds if m.quantity <= 0]
    expiring_soon = ExpiryService.get_expiring_soon_medicines(30)
    pending_returns = MedicineReturn.query.filter_by(quality_status="pending_verification").count()
    notified_reservations = Reservation.query.filter_by(status="notified").all()

    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(8).all()

    return render_template(
        "dashboard/pharmacist_dashboard.html",
        today_sales=today_sales,
        today_bills_count=len(today_bills),
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        expiring_soon=expiring_soon,
        pending_returns=pending_returns,
        notified_reservations=notified_reservations,
        recent_bills=recent_bills
    )
