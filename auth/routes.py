from functools import wraps
import uuid
from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from auth import auth_bp

def role_required(allowed_roles):
    """Decorator to enforce role-based access control (RBAC)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for("auth.login", next=request.url))
            
            if current_user.role not in allowed_roles:
                if request.is_json:
                    return jsonify({"error": "Unauthorized role access"}), 403
                flash("You do not have permission to access this page.", "danger")
                if current_user.is_admin:
                    return redirect(url_for("admin.dashboard"))
                return redirect(url_for("pharmacist.dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required(["admin"])
pharmacist_or_admin_required = role_required(["admin", "pharmacist"])

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("pharmacist.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact the administrator.", "danger")
                return render_template("auth/login.html")

            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            if next_page and not next_page.startswith("//"):
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("pharmacist.dashboard"))
        else:
            flash("Invalid email or password. Please check your credentials.", "danger")

    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        role = request.form.get("role", "pharmacist").lower()
        if role not in ["admin", "pharmacist"]:
            role = "pharmacist"

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        shop_name = request.form.get("shop_name", "").strip() if role == "admin" else None

        # Validation
        if not name or not email or not password:
            flash("Name, email, and password are required fields.", "danger")
            return render_template("auth/signup.html", role=role)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/signup.html", role=role)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/signup.html", role=role)

        if User.query.filter_by(email=email).first():
            flash("A user with this email address already exists.", "danger")
            return render_template("auth/signup.html", role=role)

        # Auto-generate user ID (e.g. ADM-7821 or PHR-1934)
        prefix = "ADM" if role == "admin" else "PHR"
        user_code = f"{prefix}-{uuid.uuid4().hex[:4].upper()}"

        user = User(
            user_code=user_code,
            name=name,
            email=email,
            role=role,
            phone=phone,
            address=address,
            shop_name=shop_name,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Display on registration confirmation screen
        return render_template(
            "auth/confirmation.html",
            user=user,
            auto_generated_id=user.user_code,
            role=user.role,
            shop_name=user.shop_name
        )

    role_param = request.args.get("role", "pharmacist")
    return render_template("auth/signup.html", role=role_param)
