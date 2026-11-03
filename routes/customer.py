import os
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from models import db, Medicine, Reservation, Prescription
from flask_login import login_required
from auth.routes import pharmacist_or_admin_required

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@customer_bp.route("/")
def portal():
    """Customer medicine search portal."""
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = Medicine.query.filter_by(is_discontinued=False)

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Medicine.name.ilike(pattern),
                Medicine.generic_name.ilike(pattern),
                Medicine.category.ilike(pattern)
            )
        )

    if category:
        query = query.filter(Medicine.category == category)

    medicines = query.order_by(Medicine.name.asc()).limit(50).all()
    categories = db.session.query(Medicine.category).distinct().filter(Medicine.is_discontinued == False).all()
    categories = [c[0] for c in categories if c[0]]

    return render_template(
        "customer/portal.html",
        medicines=medicines,
        categories=categories,
        current_q=q,
        current_category=category
    )

@customer_bp.route("/reserve", methods=["GET", "POST"])
def reserve():
    """Reserve out-of-stock medicine."""
    if request.method == "POST":
        medicine_id = int(request.form.get("medicine_id"))
        customer_name = request.form.get("customer_name", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        customer_email = request.form.get("customer_email", "").strip()
        quantity = int(request.form.get("quantity", 1))
        notes = request.form.get("notes", "").strip()

        if not customer_name or not customer_phone or quantity <= 0:
            flash("Please provide your name, phone number, and a valid quantity.", "danger")
            return redirect(url_for("customer.reserve", medicine_id=medicine_id))

        medicine = Medicine.query.get_or_404(medicine_id)
        res_number = f"RES-{uuid.uuid4().hex[:6].upper()}"

        reservation = Reservation(
            reservation_number=res_number,
            medicine_id=medicine.id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            quantity=quantity,
            notes=notes,
            status="pending"
        )
        db.session.add(reservation)
        db.session.commit()

        flash(
            f"Reservation {res_number} confirmed for {medicine.name}! "
            "You will be notified as soon as fresh stock arrives at the pharmacy.",
            "success"
        )
        return redirect(url_for("customer.portal"))

    medicine_id = request.args.get("medicine_id", type=int)
    medicine = Medicine.query.get(medicine_id) if medicine_id else None
    out_of_stock_meds = Medicine.query.filter(
        Medicine.quantity <= 0,
        Medicine.is_discontinued == False
    ).all()

    return render_template(
        "customer/reserve.html",
        medicine=medicine,
        out_of_stock_meds=out_of_stock_meds
    )

@customer_bp.route("/prescription", methods=["GET", "POST"])
def prescription():
    """Customer prescription upload page."""
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        customer_email = request.form.get("customer_email", "").strip()
        notes = request.form.get("notes", "").strip()

        if not customer_name or not customer_phone:
            flash("Please provide your name and phone number.", "danger")
            return render_template("customer/prescription.html")

        file = request.files.get("prescription_file")
        if not file or file.filename == "":
            flash("Please select a prescription image or document to upload.", "danger")
            return render_template("customer/prescription.html")

        if not allowed_file(file.filename):
            flash("Invalid file format. Allowed formats: PNG, JPG, JPEG, WEBP, PDF.", "danger")
            return render_template("customer/prescription.html")

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        rx_number = f"RX-{uuid.uuid4().hex[:6].upper()}"
        rx = Prescription(
            rx_number=rx_number,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            file_path=unique_filename,
            notes=notes,
            status="pending"
        )
        db.session.add(rx)
        db.session.commit()

        flash(
            f"Prescription {rx_number} uploaded successfully! "
            "Our licensed pharmacist will review your prescription and contact you shortly.",
            "success"
        )
        return render_template("customer/prescription_success.html", prescription=rx)

    return render_template("customer/prescription.html")

@customer_bp.route("/reservations")
@login_required
@pharmacist_or_admin_required
def reservations_list():
    """Staff view of customer backorders / reservations."""
    reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template("customer/reservations_list.html", reservations=reservations)

@customer_bp.route("/reservations/<int:res_id>/fulfill", methods=["POST"])
@login_required
@pharmacist_or_admin_required
def fulfill_reservation(res_id):
    res = Reservation.query.get_or_404(res_id)
    res.status = "fulfilled"
    res.fulfilled_at = datetime.utcnow()
    db.session.commit()
    flash(f"Reservation {res.reservation_number} marked as fulfilled.", "success")
    return redirect(url_for("customer.reservations_list"))
