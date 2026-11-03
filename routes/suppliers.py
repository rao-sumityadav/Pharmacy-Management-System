from datetime import datetime, date
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Supplier, Medicine, PurchaseOrder
from auth.routes import role_required, admin_required, pharmacist_or_admin_required
from services.inventory_service import InventoryService

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")

@suppliers_bp.route("/")
@login_required
@pharmacist_or_admin_required
def index():
    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template("suppliers/index.html", suppliers=suppliers)

@suppliers_bp.route("/new", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        supplied_medicines = request.form.get("supplied_medicines", "").strip()

        if not name or not contact_number:
            flash("Supplier name and contact number are required.", "danger")
            return render_template("suppliers/form.html")

        supplier_code = f"SUP-{uuid.uuid4().hex[:4].upper()}"
        supplier = Supplier(
            supplier_code=supplier_code,
            name=name,
            contact_number=contact_number,
            email=email,
            address=address,
            supplied_medicines=supplied_medicines
        )
        db.session.add(supplier)
        db.session.commit()

        flash(f"Supplier '{name}' added successfully!", "success")
        return redirect(url_for("suppliers.index"))

    return render_template("suppliers/form.html")

@suppliers_bp.route("/purchase-orders")
@login_required
@pharmacist_or_admin_required
def purchase_orders():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).all()
    return render_template("suppliers/purchase_orders.html", orders=orders)

@suppliers_bp.route("/purchase-orders/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_purchase_order():
    if request.method == "POST":
        supplier_id = int(request.form.get("supplier_id"))
        medicine_id = int(request.form.get("medicine_id"))
        quantity = int(request.form.get("quantity", 0))
        unit_cost = float(request.form.get("unit_cost", 0.0))
        notes = request.form.get("notes", "").strip()

        if quantity <= 0 or unit_cost <= 0:
            flash("Quantity and unit cost must be greater than zero.", "danger")
            return redirect(url_for("suppliers.create_purchase_order"))

        total_cost = round(quantity * unit_cost, 2)
        po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier_id,
            medicine_id=medicine_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            status="ordered",
            order_date=date.today(),
            notes=notes,
            created_by_id=current_user.id
        )
        db.session.add(po)
        db.session.commit()

        flash(f"Purchase Order {po_number} created successfully!", "success")
        return redirect(url_for("suppliers.purchase_orders"))

    suppliers = Supplier.query.order_by(Supplier.name.asc()).all()
    medicines = Medicine.query.filter_by(is_discontinued=False).order_by(Medicine.name.asc()).all()
    pre_selected_med_id = request.args.get("medicine_id", type=int)

    return render_template(
        "suppliers/create_po.html",
        suppliers=suppliers,
        medicines=medicines,
        pre_selected_med_id=pre_selected_med_id
    )

@suppliers_bp.route("/purchase-orders/<int:po_id>/receive", methods=["POST"])
@login_required
@pharmacist_or_admin_required
def receive_purchase_order(po_id):
    try:
        po = InventoryService.receive_purchase_order(po_id)
        flash(f"Purchase Order {po.po_number} received! Added {po.quantity} units to {po.medicine.name}.", "success")
    except Exception as e:
        flash(f"Failed to receive purchase order: {str(e)}", "danger")

    return redirect(url_for("suppliers.purchase_orders"))
