import os
from flask import Flask
from flask_mail import Mail
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from model import db, User, SchoolClass

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///school.db"

os.makedirs('instance', exist_ok=True)

with app.app_context():
    db.create_all()
    # Auto-create admin user
    try:
        from werkzeug.security import generate_password_hash
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
            db.session.commit()
            print("Admin created: admin / admin123")
    except Exception as e:
        print(f"Admin check error: {e}")

    
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = (
    "Good Foundation of Christ Group of School",
    os.environ.get("MAIL_USERNAME"),
)

db.init_app(app)
mail = Mail(app)

CLASS_NAMES = [
    "Nursery 1", "Nursery 2", "Nursery 3", "Nursery 4",
    "Primary 1", "Primary 2", "Primary 3", "Primary 4",
]


@app.cli.command("init-db")
def init_db():
    db.create_all()
    if not User.query.filter_by(email="admin@school.com").first():
        admin = User(
            email="admin@school.com",
            role="admin",
            full_name="School Admin",
            password_hash=generate_password_hash("admin123"),
        )
        db.session.add(admin)
        db.session.commit()
    print("Database ready. Login with admin@school.com / admin123")


@app.cli.command("init-classes")
def init_classes():
    added = 0
    for name in CLASS_NAMES:
        exists = SchoolClass.query.filter(
            db.func.lower(SchoolClass.name) == name.lower()
        ).first()
        if not exists:
            db.session.add(SchoolClass(name=name))
            added += 1
    db.session.commit()
    print(f"{added} classes added.")


import routes