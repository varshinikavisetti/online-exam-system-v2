"""
Online Examination System - application entry point.

Run with:  python app.py
"""
import logging
from flask import Flask, redirect, url_for, render_template, request
from flask_login import LoginManager, current_user

from config import Config, IS_PRODUCTION
from extensions import csrf, limiter, mail
from models import db
from models.user import User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- TEMPORARY DIAGNOSTIC: remove once the TiDB SSL issue is confirmed
    # fixed. Two different SSL fixes have produced the identical error, so
    # rather than guess a third time, this prints exactly what config is
    # active at process startup — visible in Render's logs on next deploy.
    print(
        f"[STARTUP DIAGNOSTIC] DB_SSL={Config.DB_SSL} "
        f"DB_HOST={Config.DB_HOST} DB_PORT={Config.DB_PORT} "
        f"SQLALCHEMY_ENGINE_OPTIONS={app.config.get('SQLALCHEMY_ENGINE_OPTIONS')}",
        flush=True,
    )

    # CSRF protection on every state-changing (POST/PUT/PATCH/DELETE) request.
    csrf.init_app(app)

    # Basic brute-force / abuse protection. Login and registration get
    # tighter, per-route limits (see routes/auth.py); this is the app-wide
    # backstop.
    limiter.init_app(app)

    # Optional email notifications (exam reminders). Safe to init even if
    # MAIL_SERVER isn't set — sending is just skipped, see email_service.py.
    mail.init_app(app)

    # Scheduling times are stored as UTC in the DB but everything shown to
    # or entered by a human (admin scheduling form, student messages) is in
    # IST — see utils/timezone_helper.py. Exposed as Jinja helpers so every
    # template converts the same way instead of drifting out of sync.
    from utils.timezone_helper import utc_to_ist
    app.jinja_env.filters["to_ist"] = utc_to_ist

    # Basic structured logging: every request's method/path/status gets logged
    # to stdout, which is exactly what cloud platforms (Render/Railway/Docker)
    # expect so their log viewers can pick it up automatically.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("exam_system")

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.is_admin():
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("student.dashboard"))
        return render_template("landing.html")

    @app.after_request
    def log_request(response):
        logger.info(
            "%s %s -> %s", request.method, request.path, response.status_code
        )
        return response

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(self), microphone=(), geolocation=()"
        )
        if IS_PRODUCTION:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    import os

    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true" and not IS_PRODUCTION
    app.run(debug=debug_mode)
