"""
One-time helper to create the first admin account.

Run with:  python -m utils.seed_admin
"""
from app import create_app
from models import db
from models.user import User

app = create_app()

with app.app_context():
    email = input("Admin email: ").strip().lower()
    if User.query.filter_by(email=email).first():
        print("A user with that email already exists.")
    else:
        name = input("Admin name: ").strip()
        password = input("Admin password: ").strip()

        admin = User(name=name, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin account created for {email}.")
