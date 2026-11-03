from datetime import datetime, date, timedelta
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Medicine, Bill, BillItem, Customer, Supplier, PurchaseOrder, MedicineReturn, Prescription
from auth.routes import admin_required
from services.expiry_service import ExpiryService

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    today = date.today()
    start_of_today = datetime.combine(today, datetime.min.time())
    
    # Key Metrics
    today_bills = Bill.query.filter(
        Bill.created_at >= start_of_today,
        Bill.status != "cancelled"
    ).all()
    today_sales = sum(b.total_amount for b in today_bills)
    today_profit = sum(
        sum(max(0.0, item.unit_price - item.cost_price) * item.quantity for item in b.items)
        for b in today_bills
    )

    # Monthly Sales
    first_of_month = datetime(today.year, today.month, 1)
    monthly_bills = Bill.query.filter(
        Bill.created_at >= first_of_month,
        Bill.status != "cancelled"
    ).all()
    month_sales = sum(b.total_amount for b in monthly_bills)

    # Inventory Metrics
    all_active_meds = Medicine.query.filter_by(is_discontinued=False).all()
    total_stock_units = sum(m.quantity for m in all_active_meds)
    total_inventory_value = sum(m.quantity * m.cost_price for m in all_active_meds)
    low_stock_count = sum(1 for m in all_active_meds if 0 < m.quantity <= m.reorder_threshold)
    out_of_stock_count = sum(1 for m in all_active_meds if m.quantity <= 0)

    # Expiry Metrics
    expired_meds = ExpiryService.get_expired_medicines()
    expiring_soon_meds = ExpiryService.get_expiring_soon_medicines(30)

    # Pending Actionables
    pending_returns_count = MedicineReturn.query.filter_by(quality_status="pending_verification").count()
    pending_rx_count = Prescription.query.filter_by(status="pending").count()
    overdue_dues_count = Bill.query.filter(Bill.due_amount > 0, Bill.due_date < today).count()

    # Recent 10 bills
    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(10).all()

    return render_template(
        "dashboard/admin_dashboard.html",
        today_sales=today_sales,
        today_bills_count=len(today_bills),
        today_profit=today_profit,
        month_sales=month_sales,
        total_inventory_value=total_inventory_value,
        total_stock_units=total_stock_units,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        expired_count=len(expired_meds),
        expiring_soon_count=len(expiring_soon_meds),
        pending_returns_count=pending_returns_count,
        pending_rx_count=pending_rx_count,
        overdue_dues_count=overdue_dues_count,
        recent_bills=recent_bills
    )

@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "pharmacist")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return redirect(url_for("admin.users"))

        if User.query.filter_by(email=email).first():
            flash("User with this email already exists.", "danger")
            return redirect(url_for("admin.users"))

        prefix = "ADM" if role == "admin" else "PHR"
        user_code = f"{prefix}-{uuid.uuid4().hex[:4].upper()}"

        new_user = User(
            user_code=user_code,
            name=name,
            email=email,
            role=role,
            phone=phone,
            address=address,
            is_active=True
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash(f"User {name} ({user_code}) added successfully!", "success")
        return redirect(url_for("admin.users"))

    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("users/index.html", users=all_users)

@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_user_status(user_id):
    if user_id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    status_label = "activated" if user.is_active else "deactivated"
    flash(f"User {user.name} has been {status_label}.", "info")
    return redirect(url_for("admin.users"))

@admin_bp.route("/reports")
@login_required
@admin_required
def reports():
    range_type = request.args.get("range", "month")
    today = date.today()

    if range_type == "today":
        start_date = datetime.combine(today, datetime.min.time())
    elif range_type == "week":
        start_date = datetime.combine(today - timedelta(days=7), datetime.min.time())
    elif range_type == "year":
        start_date = datetime(today.year, 1, 1)
    else:  # month default
        start_date = datetime(today.year, today.month, 1)

    bills = Bill.query.filter(
        Bill.created_at >= start_date,
        Bill.status != "cancelled"
    ).all()

    total_revenue = sum(b.total_amount for b in bills)
    total_tax = sum(b.tax_amount for b in bills)
    total_discount = sum(b.discount_amount for b in bills)
    total_dues = sum(b.due_amount for b in bills)

    total_cost = 0.0
    category_summary = {}

    for b in bills:
        for item in b.items:
            line_cost = item.cost_price * item.quantity
            total_cost += line_cost
            cat = item.medicine.category if item.medicine else "General"
            if cat not in category_summary:
                category_summary[cat] = {"units": 0, "sales": 0.0, "profit": 0.0}
            category_summary[cat]["units"] += item.quantity
            category_summary[cat]["sales"] += item.subtotal
            category_summary[cat]["profit"] += max(0.0, item.subtotal - line_cost)

    gross_profit = max(0.0, total_revenue - total_tax - total_cost)
    profit_margin = round((gross_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

    return render_template(
        "reports/index.html",
        range_type=range_type,
        bills_count=len(bills),
        total_revenue=total_revenue,
        total_tax=total_tax,
        total_discount=total_discount,
        total_dues=total_dues,
        total_cost=total_cost,
        gross_profit=gross_profit,
        profit_margin=profit_margin,
        category_summary=category_summary,
        bills=bills
    )

@admin_bp.route("/prescriptions", methods=["GET", "POST"])
@login_required
@admin_required
def prescriptions():
    if request.method == "POST":
        rx_id = int(request.form.get("prescription_id"))
        status = request.form.get("status")  # approved, rejected
        review_notes = request.form.get("review_notes", "")

        rx = Prescription.query.get_or_404(rx_id)
        rx.status = status
        rx.review_notes = review_notes
        rx.reviewed_by_id = current_user.id
        rx.reviewed_at = datetime.utcnow()
        db.session.commit()

        flash(f"Prescription {rx.rx_number} marked as {status}.", "success")
        return redirect(url_for("admin.prescriptions"))

    prescriptions = Prescription.query.order_by(Prescription.created_at.desc()).all()
    return render_template("admin/prescriptions.html", prescriptions=prescriptions)
