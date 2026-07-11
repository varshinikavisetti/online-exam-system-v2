from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # College-requested student profile fields. Nullable/optional so admin
    # accounts and any pre-existing students don't break; the registration
    # form requires them going forward for new student signups.
    mobile_number = db.Column(db.String(20), nullable=True)
    year_of_study = db.Column(db.String(20), nullable=True)  # "1", "2", "3", "4"
    department = db.Column(db.String(100), nullable=True)
    roll_number = db.Column(db.String(50), nullable=True)

    results = db.relationship("Result", backref="student", lazy=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self):
        return self.role == "admin"
