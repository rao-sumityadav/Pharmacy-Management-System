from datetime import datetime, date, timedelta
import uuid
from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from models import db, Medicine, Bill, BillItem, Customer, Supplier, PurchaseOrder, Payment, MedicineReturn, Prescription
from services.billing_service import BillingService, BillingError
from services.inventory_service import InventoryService
from services.alert_service import AlertService
from services.expiry_service import ExpiryService
from auth.routes import role_required, pharmacist_or_admin_required, admin_required
from api import api_bp

@api_bp.route("/medicines/search", methods=["GET"])
def search_medicines():
    """
    Fast search for medicines by name, generic name, category, or batch number.
    Optional query params:
      - q: search keyword
      - category: filter category
      - active_only: 1 to exclude discontinued
      - sellable_only: 1 to exclude expired and out of stock items
    """
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sellable_only = request.args.get("sellable_only") == "1"
    active_only = request.args.get("active_only", "1") == "1"

    query = Medicine.query

    if active_only:
        query = query.filter(Medicine.is_discontinued == False)

    if category:
        query = query.filter(Medicine.category.ilike(f"%{category}%"))

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Medicine.name.ilike(search_pattern),
                Medicine.generic_name.ilike(search_pattern),
                Medicine.category.ilike(search_pattern),
                Medicine.batch_number.ilike(search_pattern),
                Medicine.manufacturer.ilike(search_pattern)
            )
        )

    medicines = query.order_by(Medicine.name.asc()).limit(50).all()
    results = []
    today = date.today()

    for m in medicines:
        is_expired = m.expiry_date < today
        if sellable_only and (is_expired or m.quantity <= 0):
            continue

        results.append({
            "id": m.id,
            "medicine_code": m.medicine_code,
            "name": m.name,
            "generic_name": m.generic_name or "",
            "category": m.category,
            "batch_number": m.batch_number,
            "quantity": m.quantity,
            "unit_price": m.unit_price,
            "cost_price": m.cost_price,
            "manufacturer": m.manufacturer,
            "expiry_date": m.expiry_date.strftime("%Y-%m-%d"),
            "is_expired": is_expired,
            "is_expiring_soon": m.is_expiring_soon,
            "stock_status": m.stock_status,
            "rack_location": m.rack_location
        })

    return jsonify({"success": True, "count": len(results), "medicines": results})

@api_bp.route("/medicines/<int:medicine_id>", methods=["GET"])
def get_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    return jsonify({"success": True, "medicine": medicine.to_dict()})

@api_bp.route("/bills/calculate", methods=["POST"])
@login_required
def calculate_bill():
    """Preview bill calculation without committing to the database."""
    data = request.get_json() or {}
    items = data.get("items", [])
    discount_percent = float(data.get("discount_percent", 0.0))
    tax_percent = float(data.get("tax_percent", 5.0))

    try:
        totals = BillingService.calculate_bill_totals(
            items, 
            discount_percent=discount_percent, 
            tax_percent=tax_percent
        )
        return jsonify({"success": True, "totals": totals})
    except BillingError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/bills/create", methods=["POST"])
@login_required
@pharmacist_or_admin_required
def create_bill_api():
    """
    Create a bill atomically. Deducts stock, validates expiry, records initial payment.
    """
    data = request.get_json() or {}
    customer_name = data.get("customer_name")
    customer_phone = data.get("customer_phone")
    items = data.get("items", [])
    discount_percent = float(data.get("discount_percent", 0.0))
    tax_percent = float(data.get("tax_percent", 5.0))
    payment_method = data.get("payment_method", "cash")
    paid_amount = data.get("paid_amount")
    due_days = int(data.get("due_days", 15))
    notes = data.get("notes", "")

    if not items:
        return jsonify({"success": False, "error": "No items provided."}), 400

    try:
        bill = BillingService.create_bill(
            customer_name=customer_name,
            customer_phone=customer_phone,
            items_data=items,
            discount_percent=discount_percent,
            tax_percent=tax_percent,
            payment_method=payment_method,
            paid_amount=paid_amount,
            due_days=due_days,
            notes=notes,
            created_by_user_id=current_user.id
        )

        return jsonify({
            "success": True,
            "message": "Bill created successfully!",
            "bill_id": bill.id,
            "bill_number": bill.bill_number,
            "total_amount": bill.total_amount,
            "paid_amount": bill.paid_amount,
            "due_amount": bill.due_amount,
            "status": bill.status
        })

    except BillingError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Unexpected error: {str(e)}"}), 500

@api_bp.route("/payments/mock-gateway", methods=["POST"])
@login_required
def mock_payment_gateway():
    """
    Simulated Razorpay / Stripe Payment Gateway API.
    Simulates payment initiation and instant response callback.
    Accepts: amount, currency, mode, simulate_failure (optional)
    """
    data = request.get_json() or {}
    amount = float(data.get("amount", 0.0))
    mode = data.get("mode", "card")  # card, upi, netbanking
    simulate_failure = bool(data.get("simulate_failure", False))

    if amount <= 0:
        return jsonify({"success": False, "error": "Invalid amount"}), 400

    # Simulate Gateway transaction
    if simulate_failure:
        return jsonify({
            "success": False,
            "status": "failed",
            "error_code": "PAYMENT_DECLINED",
            "message": "Simulated Gateway: Card declined or insufficient funds."
        }), 400

    txn_id = f"PAY-MOCK-{uuid.uuid4().hex[:12].upper()}"
    return jsonify({
        "success": True,
        "status": "authorized",
        "gateway": "PMS Mock Gateway (Stripe/Razorpay Engine)",
        "transaction_ref": txn_id,
        "amount": amount,
        "currency": "INR",
        "mode": mode,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Payment captured successfully via Mock Gateway."
    })

@api_bp.route("/bills/<int:bill_id>/settle-due", methods=["POST"])
@login_required
@pharmacist_or_admin_required
def settle_due_api(bill_id):
    """Settle overdue balance and accumulated fine."""
    data = request.get_json() or {}
    amount = float(data.get("amount", 0.0))
    payment_method = data.get("payment_method", "cash")
    notes = data.get("notes", "")

    try:
        bill = BillingService.settle_due(
            bill_id=bill_id,
            payment_amount=amount,
            payment_method=payment_method,
            notes=notes
        )
        return jsonify({
            "success": True,
            "message": "Payment recorded successfully!",
            "bill_number": bill.bill_number,
            "due_amount": bill.due_amount,
            "paid_amount": bill.paid_amount,
            "status": bill.status
        })
    except BillingError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/alerts", methods=["GET"])
@login_required
def get_alerts():
    """Fetch active alerts for the notification center."""
    alerts = AlertService.get_all_alerts()
    # Serialize for JSON response
    serialized = []
    for a in alerts:
        created = a.get("created_at")
        time_str = created.strftime("%Y-%m-%d %H:%M") if created else "Just now"
        serialized.append({
            "type": a["type"],
            "severity": a["severity"],
            "title": a["title"],
            "message": a["message"],
            "link": a["link"],
            "time": time_str
        })
    return jsonify({"success": True, "count": len(serialized), "alerts": serialized})

@api_bp.route("/reports/sales-chart", methods=["GET"])
@login_required
@admin_required
def sales_chart_data():
    """7-Day Sales & Profit Trends for Chart.js."""
    days = int(request.args.get("days", 7))
    today = date.today()
    labels = []
    sales_data = []
    profit_data = []

    for i in range(days - 1, -1, -1):
        target_date = today - timedelta(days=i)
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())

        bills = Bill.query.filter(
            Bill.created_at >= start_of_day,
            Bill.created_at <= end_of_day,
            Bill.status != "cancelled"
        ).all()

        daily_revenue = sum(b.total_amount for b in bills)

        # Calculate profit
        daily_profit = 0.0
        for b in bills:
            for item in b.items:
                profit_per_unit = max(0.0, item.unit_price - item.cost_price)
                daily_profit += profit_per_unit * item.quantity

        labels.append(target_date.strftime("%b %d"))
        sales_data.append(round(daily_revenue, 2))
        profit_data.append(round(daily_profit, 2))

    return jsonify({
        "success": True,
        "labels": labels,
        "sales": sales_data,
        "profit": profit_data
    })

@api_bp.route("/reports/category-chart", methods=["GET"])
@login_required
@admin_required
def category_chart_data():
    """Sales distribution by medicine category for Doughnut Chart."""
    results = db.session.query(
        Medicine.category,
        db.func.sum(BillItem.quantity * BillItem.unit_price)
    ).join(BillItem, Medicine.id == BillItem.medicine_id)\
     .group_by(Medicine.category).all()

    labels = [r[0] for r in results if r[0]]
    values = [round(float(r[1] or 0.0), 2) for r in results if r[0]]

    # Fallback if no sales yet
    if not labels:
        labels = ["General", "Antibiotics", "Analgesics"]
        values = [0, 0, 0]

    return jsonify({
        "success": True,
        "labels": labels,
        "values": values
    })

@api_bp.route("/reports/stock-chart", methods=["GET"])
@login_required
def stock_chart_data():
    """Stock health distribution for Chart.js."""
    all_meds = Medicine.query.filter_by(is_discontinued=False).all()
    in_stock = sum(1 for m in all_meds if m.quantity > m.reorder_threshold)
    low_stock = sum(1 for m in all_meds if 0 < m.quantity <= m.reorder_threshold)
    out_of_stock = sum(1 for m in all_meds if m.quantity <= 0)

    return jsonify({
        "success": True,
        "labels": ["In Stock", "Low Stock", "Out of Stock"],
        "values": [in_stock, low_stock, out_of_stock]
    })
