from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import limiter
from models import db
from models.user import User

auth_bp = Blueprint("auth", __name__)


def _password_is_strong_enough(password):
    """Minimal complexity bar: length plus at least one letter and one digit."""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("100 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        mobile_number = request.form.get("mobile_number", "").strip()
        year_of_study = request.form.get("year_of_study", "").strip()
        department = request.form.get("department", "").strip()
        roll_number = request.form.get("roll_number", "").strip()

        if not name or not email or not password or not mobile_number or not year_of_study:
            flash("All fields are required.", "danger")
            return redirect(url_for("auth.register"))

        digits_only = "".join(c for c in mobile_number if c.isdigit())
        if len(digits_only) < 10:
            flash("Please enter a valid mobile number.", "danger")
            return redirect(url_for("auth.register"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        if not _password_is_strong_enough(password):
            flash(
                "Password must be at least 8 characters and include a letter and a number.",
                "danger",
            )
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            name=name,
            email=email,
            role="student",
            mobile_number=mobile_number,
            year_of_study=year_of_study,
            department=department or None,
            roll_number=roll_number or None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("100 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            if user.is_admin():
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("student.dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
