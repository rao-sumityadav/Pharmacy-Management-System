from datetime import datetime
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, MedicineReturn, Medicine, Bill
from auth.routes import role_required, pharmacist_or_admin_required
from services.inventory_service import InventoryService

returns_bp = Blueprint("returns", __name__, url_prefix="/returns")

@returns_bp.route("/")
@login_required
@pharmacist_or_admin_required
def index():
    returns_list = MedicineReturn.query.order_by(MedicineReturn.created_at.desc()).all()
    pending_count = sum(1 for r in returns_list if r.quality_status == "pending_verification")
    return render_template("returns/index.html", returns=returns_list, pending_count=pending_count)

@returns_bp.route("/new", methods=["GET", "POST"])
@login_required
@pharmacist_or_admin_required
def create():
    if request.method == "POST":
        bill_number = request.form.get("bill_number", "").strip()
        medicine_id = int(request.form.get("medicine_id"))
        quantity = int(request.form.get("quantity", 1))
        refund_amount = float(request.form.get("refund_amount", 0.0))
        return_reason = request.form.get("return_reason", "").strip()

        bill = None
        if bill_number:
            bill = Bill.query.filter_by(bill_number=bill_number).first()

        medicine = Medicine.query.get_or_404(medicine_id)
        if quantity <= 0:
            flash("Quantity must be at least 1.", "danger")
            return redirect(url_for("returns.create"))

        return_number = f"RET-{uuid.uuid4().hex[:6].upper()}"

        ret = MedicineReturn(
            return_number=return_number,
            bill_id=bill.id if bill else None,
            medicine_id=medicine.id,
            quantity=quantity,
            refund_amount=refund_amount,
            return_reason=return_reason,
            quality_status="pending_verification"  # Held in verification!
        )
        db.session.add(ret)
        db.session.commit()

        flash(
            f"Return {return_number} logged! Status: Pending Quality Verification. "
            "Item will NOT be added to sellable stock until quality inspection is completed.", 
            "info"
        )
        return redirect(url_for("returns.index"))

    medicines = Medicine.query.filter_by(is_discontinued=False).order_by(Medicine.name.asc()).all()
    return render_template("returns/form.html", medicines=medicines)

@returns_bp.route("/<int:return_id>/verify", methods=["POST"])
@login_required
@pharmacist_or_admin_required
def verify(return_id):
    decision = request.form.get("decision")  # approved_restocked or rejected_damaged
    notes = request.form.get("notes", "").strip()

    try:
        ret = InventoryService.process_quality_verification(
            return_id=return_id,
            verified_by_user_id=current_user.id,
            status=decision,
            notes=notes
        )
        if decision == "approved_restocked":
            flash(f"Return {ret.return_number} verified and approved! {ret.quantity} units restocked to {ret.medicine.name}.", "success")
        else:
            flash(f"Return {ret.return_number} rejected due to quality check. Item damaged/discarded (not restocked).", "warning")
    except Exception as e:
        flash(f"Verification failed: {str(e)}", "danger")

    return redirect(url_for("returns.index"))
