from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Bill, BillItem, Payment
from auth.routes import role_required, pharmacist_or_admin_required
from services.billing_service import BillingService

bills_bp = Blueprint("bills", __name__, url_prefix="/bills")

@bills_bp.route("/")
@login_required
@pharmacist_or_admin_required
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    query = Bill.query

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Bill.bill_number.ilike(pattern),
                Bill.customer_name.ilike(pattern),
                Bill.customer_phone.ilike(pattern)
            )
        )

    if status:
        query = query.filter(Bill.status == status)

    bills = query.order_by(Bill.created_at.desc()).limit(100).all()
    return render_template("bills/index.html", bills=bills, current_q=q, current_status=status)

@bills_bp.route("/<int:bill_id>")
@login_required
@pharmacist_or_admin_required
def view_invoice(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    payments = bill.payments.order_by(Payment.created_at.asc()).all()
    return render_template("bills/invoice.html", bill=bill, payments=payments)

@bills_bp.route("/dues")
@login_required
@pharmacist_or_admin_required
def dues():
    """Track credit purchases and overdue fines (Rs. 10/day)."""
    due_bills = Bill.query.filter(Bill.due_amount > 0).order_by(Bill.due_date.asc()).all()
    total_principal_due = sum(b.due_amount for b in due_bills)
    total_fines = sum(b.calculate_fine() for b in due_bills)
    total_receivable = total_principal_due + total_fines

    return render_template(
        "bills/dues.html",
        bills=due_bills,
        total_principal_due=total_principal_due,
        total_fines=total_fines,
        total_receivable=total_receivable
    )

@bills_bp.route("/<int:bill_id>/settle", methods=["POST"])
@login_required
@pharmacist_or_admin_required
def settle_due(bill_id):
    amount = float(request.form.get("amount", 0.0))
    payment_method = request.form.get("payment_method", "cash")
    notes = request.form.get("notes", "").strip()

    try:
        bill = BillingService.settle_due(
            bill_id=bill_id,
            payment_amount=amount,
            payment_method=payment_method,
            notes=notes
        )
        flash(f"Payment of Rs. {amount:.2f} recorded for {bill.bill_number}.", "success")
    except Exception as e:
        flash(f"Error settling due: {str(e)}", "danger")

    return redirect(url_for("bills.dues"))
