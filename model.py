import uuid
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer

db = SQLAlchemy()


def generate_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    gender = db.Column(db.String(10))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    address = db.Column(db.String(255))
    occupation = db.Column(db.String(100))
    staff_id = db.Column(db.String(30), unique=True)
    qualification = db.Column(db.String(150))
    date_employed = db.Column(db.Date)

    def get_reset_token(self):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps(
            {"user_id": self.id, "ph": self.password_hash[-10:]},
            salt="password-reset",
        )

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, salt="password-reset", max_age=max_age)
        except Exception:
            return None
        user = db.session.get(User, data["user_id"])
        if user and user.password_hash[-10:] == data["ph"]:
            return user
        return None


class SchoolClass(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50), nullable=False)
    teacher_id = db.Column(db.String(36), db.ForeignKey("user.id"))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    teacher = db.relationship("User")


class Student(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("user.id"))
    parent_id = db.Column(db.String(36), db.ForeignKey("user.id"))
    class_id = db.Column(db.String(36), db.ForeignKey("school_class.id"))
    admission_no = db.Column(db.String(30), unique=True, nullable=False)
    dob = db.Column(db.Date)
    common_sickness = db.Column(db.Text)
    previous_school = db.Column(db.Text)
    previous_class = db.Column(db.String(100))
    reason_for_leaving = db.Column(db.Text)
    contact_address = db.Column(db.Text)
    year_of_entry = db.Column(db.Integer)

    user = db.relationship("User", foreign_keys=[user_id])
    parent = db.relationship("User", foreign_keys=[parent_id])
    school_class = db.relationship("SchoolClass")

    @property
    def details_complete(self):
        return all([
            self.previous_school,
            self.previous_class,
            self.reason_for_leaving,
            self.contact_address,
            self.year_of_entry,
        ])


class Attendance(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    student_id = db.Column(db.String(36), db.ForeignKey("student.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)


class Result(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    student_id = db.Column(db.String(36), db.ForeignKey("student.id"), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    term = db.Column(db.String(40), nullable=False)
    ca = db.Column(db.Float, default=0)
    exam = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    grade = db.Column(db.String(2))


class Fee(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    student_id = db.Column(db.String(36), db.ForeignKey("student.id"), nullable=False)
    term = db.Column(db.String(40), nullable=False)
    amount_due = db.Column(db.Float, default=0)
    amount_paid = db.Column(db.Float, default=0)

    student = db.relationship("Student", backref="fees")


class Payment(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    fee_id = db.Column(db.String(36), db.ForeignKey("fee.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), nullable=False)
    paid_on = db.Column(db.Date, nullable=False)
    receipt_no = db.Column(db.String(30), unique=True, nullable=False)
    recorded_by = db.Column(db.String(36), db.ForeignKey("user.id"))

    fee = db.relationship("Fee", backref="payments")