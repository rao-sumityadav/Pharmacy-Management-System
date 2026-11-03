import os
from flask import Flask, render_template, send_from_directory, jsonify
from flask_login import LoginManager
from config import Config
from models import db, User
from services.alert_service import AlertService

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.main import main_bp
    from auth import auth_bp
    from api import api_bp
    from routes.admin import admin_bp
    from routes.pharmacist import pharmacist_bp
    from routes.medicines import medicines_bp
    from routes.suppliers import suppliers_bp
    from routes.bills import bills_bp
    from routes.returns import returns_bp
    from routes.customer import customer_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(pharmacist_bp)
    app.register_blueprint(medicines_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(customer_bp)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Route to serve prescription uploads
    @app.route("/uploads/prescriptions/<filename>")
    def uploaded_prescription(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    # Context processors for global templates
    @app.context_processor
    def inject_globals():
        try:
            alert_count = AlertService.get_alert_count()
        except Exception:
            alert_count = 0
        return {
            "app_name": "PharmaCare PMS",
            "alert_count": alert_count
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def access_forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("errors/500.html"), 500

    # Ensure DB tables are created
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
