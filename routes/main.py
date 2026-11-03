from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
from auth.routes import pharmacist_or_admin_required
from models import Medicine, Supplier, Customer, Bill
from datetime import date

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("pharmacist.dashboard"))
    
    # Public landing page with stats preview
    total_meds = Medicine.query.filter_by(is_discontinued=False).count()
    return render_template("landing.html", total_meds=total_meds)

@main_bp.route("/pos")
@login_required
@pharmacist_or_admin_required
def pos():
    """Interactive POS billing terminal."""
    return render_template("pos/index.html")
