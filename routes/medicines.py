from datetime import datetime, date
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Medicine
from auth.routes import role_required, admin_required, pharmacist_or_admin_required
from services.expiry_service import ExpiryService

medicines_bp = Blueprint("medicines", __name__, url_prefix="/medicines")

@medicines_bp.route("/")
@login_required
@pharmacist_or_admin_required
def index():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    filter_status = request.args.get("filter", "all")
    today = date.today()

    query = Medicine.query.filter_by(is_discontinued=False)

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Medicine.name.ilike(pattern),
                Medicine.generic_name.ilike(pattern),
                Medicine.batch_number.ilike(pattern),
                Medicine.manufacturer.ilike(pattern)
            )
        )

    if category:
        query = query.filter(Medicine.category == category)

    medicines = query.order_by(Medicine.name.asc()).all()

    # In-memory filter for status
    if filter_status == "low_stock":
        medicines = [m for m in medicines if 0 < m.quantity <= m.reorder_threshold]
    elif filter_status == "out_of_stock":
        medicines = [m for m in medicines if m.quantity <= 0]
    elif filter_status == "expiring":
        medicines = [m for m in medicines if m.is_expiring_soon]
    elif filter_status == "expired":
        medicines = [m for m in medicines if m.is_expired]

    categories = db.session.query(Medicine.category).distinct().filter(Medicine.is_discontinued == False).all()
    categories = [c[0] for c in categories if c[0]]

    return render_template(
        "medicines/index.html",
        medicines=medicines,
        categories=categories,
        current_q=q,
        current_category=category,
        current_filter=filter_status
    )

@medicines_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        generic_name = request.form.get("generic_name", "").strip()
        category = request.form.get("category", "").strip()
        batch_number = request.form.get("batch_number", "").strip()
        quantity = int(request.form.get("quantity", 0))
        unit_price = float(request.form.get("unit_price", 0.0))
        cost_price = float(request.form.get("cost_price", 0.0))
        manufacturer = request.form.get("manufacturer", "").strip()
        mfg_date_str = request.form.get("manufacturing_date")
        exp_date_str = request.form.get("expiry_date")
        reorder_threshold = int(request.form.get("reorder_threshold", 10))
        rack_location = request.form.get("rack_location", "General").strip()

        if not name or not category or not batch_number or not mfg_date_str or not exp_date_str:
            flash("All required fields must be filled out.", "danger")
            return render_template("medicines/form.html", medicine=None)

        mfg_date = datetime.strptime(mfg_date_str, "%Y-%m-%d").date()
        exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()

        if exp_date <= mfg_date:
            flash("Expiry date must be after manufacturing date.", "danger")
            return render_template("medicines/form.html", medicine=None)

        medicine_code = f"MED-{uuid.uuid4().hex[:5].upper()}"

        med = Medicine(
            medicine_code=medicine_code,
            name=name,
            generic_name=generic_name,
            category=category,
            batch_number=batch_number,
            quantity=quantity,
            unit_price=unit_price,
            cost_price=cost_price,
            manufacturer=manufacturer,
            manufacturing_date=mfg_date,
            expiry_date=exp_date,
            reorder_threshold=reorder_threshold,
            rack_location=rack_location
        )
        db.session.add(med)
        db.session.commit()

        flash(f"Medicine '{med.name}' added successfully!", "success")
        return redirect(url_for("medicines.index"))

    return render_template("medicines/form.html", medicine=None)

@medicines_bp.route("/<int:medicine_id>/edit", methods=["GET", "POST"])
@login_required
@pharmacist_or_admin_required
def edit(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)

    if request.method == "POST":
        medicine.name = request.form.get("name", "").strip()
        medicine.generic_name = request.form.get("generic_name", "").strip()
        medicine.category = request.form.get("category", "").strip()
        medicine.batch_number = request.form.get("batch_number", "").strip()
        medicine.quantity = int(request.form.get("quantity", medicine.quantity))
        medicine.unit_price = float(request.form.get("unit_price", medicine.unit_price))
        if current_user.is_admin:
            medicine.cost_price = float(request.form.get("cost_price", medicine.cost_price))
        medicine.manufacturer = request.form.get("manufacturer", "").strip()
        
        mfg_str = request.form.get("manufacturing_date")
        exp_str = request.form.get("expiry_date")
        if mfg_str:
            medicine.manufacturing_date = datetime.strptime(mfg_str, "%Y-%m-%d").date()
        if exp_str:
            medicine.expiry_date = datetime.strptime(exp_str, "%Y-%m-%d").date()

        medicine.reorder_threshold = int(request.form.get("reorder_threshold", medicine.reorder_threshold))
        medicine.rack_location = request.form.get("rack_location", medicine.rack_location).strip()
        medicine.updated_at = datetime.utcnow()

        db.session.commit()
        flash(f"Medicine '{medicine.name}' updated successfully!", "success")
        return redirect(url_for("medicines.index"))

    return render_template("medicines/form.html", medicine=medicine)

@medicines_bp.route("/<int:medicine_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    # Soft delete
    medicine.is_discontinued = True
    db.session.commit()
    flash(f"Medicine '{medicine.name}' marked as discontinued (soft deleted).", "info")
    return redirect(url_for("medicines.index"))

@medicines_bp.route("/expiry")
@login_required
@pharmacist_or_admin_required
def expiry():
    """Dedicated Expiry Date Tracking module."""
    expired = ExpiryService.get_expired_medicines()
    expiring_soon = ExpiryService.get_expiring_soon_medicines(30)
    metrics = ExpiryService.get_expiry_metrics(30)

    return render_template(
        "medicines/expiry.html",
        expired=expired,
        expiring_soon=expiring_soon,
        metrics=metrics
    )
