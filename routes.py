import os
from datetime import date
from functools import wraps
from flask import (render_template, redirect, url_for, flash,
                   abort, session, g, request)
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, mail
from model import User, SchoolClass, Student, Fee, Payment, Attendance, Result, db
from forms import (LoginForm, ForgotPasswordForm, ResetPasswordForm,
                   AddStudentForm, AddTeacherForm, AddParentForm, AddAdminForm,
                   EditUserForm, ProfileForm, ChangePasswordForm,
                   ClassForm, EditClassForm, EditStudentForm,
                   ClassFeeForm, PaymentForm, SheetForm, PromoteForm,
                   PupilDetailsForm)

USER_FORMS = {
    "student": AddStudentForm,
    "teacher": AddTeacherForm,
    "parent": AddParentForm,
    "admin": AddAdminForm,
}

TERM_NAMES = ["First Term", "Second Term", "Third Term"]
CA_MAX = 40
EXAM_MAX = 60
DEFAULT_SUBJECTS = [
    "English Language", "Mathematics", "Basic Science", "Social Studies",
    "Civic Education", "Computer Studies", "Christian Religious Studies",
    "Creative Arts", "Phonics", "Handwriting",
]

SCHOOL_NAME = "Good Foundation of Christ Group of School"


def profile_todo(user):
    todo = []
    link = None

    if user.role == "admin":
        return todo, link

    if not (user.phone and user.address):
        todo.append("your phone number and address")
        link = url_for("profile", view="edit")

    if user.role == "parent":
        kids = db.session.execute(
            db.select(Student).where(Student.parent_id == user.id)
        ).scalars().all()
        pending = [k for k in kids if not k.details_complete]
        if pending:
            todo.append(
                "your child's school details" if len(pending) == 1
                else "your children's school details"
            )
            if link is None:
                link = url_for("profile", view="child", child=pending[0].id)

    return todo, link


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None
    if g.user and not g.user.is_active:
        session.clear()
        g.user = None

    if g.user and g.user.must_change_password and request.endpoint:
        on_password_page = (
            request.endpoint == "profile" and request.args.get("view") == "password"
        )
        if request.endpoint not in ("logout", "static") and not on_password_page:
            flash("Please change your temporary password to continue.", "info")
            return redirect(url_for("profile", view="password"))


@app.context_processor
def inject_user():
    user = g.get("user")
    todo, link = profile_todo(user) if user else ([], None)
    return {
        "current_user": user,
        "profile_todo": todo,
        "profile_todo_link": link,
    }


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "danger")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if g.user is None:
                flash("Please log in first.", "danger")
                return redirect(url_for("login", next=request.path))
            if g.user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def clean(value):
    return value.strip() if value and value.strip() else None


def money(amount):
    return f"₦{amount:,.2f}"


def full_url(endpoint, **values):
    base = app.config.get("APP_URL", "").rstrip("/")
    if base:
        return base + url_for(endpoint, **values)
    return url_for(endpoint, _external=True, **values)


def compose_email(recipient, subject, name, heading, intro, details=None,
                  credentials=None, steps=None, button=None, note=None):
    lines = [f"Dear {name},", ""]
    for paragraph in intro:
        lines += [paragraph, ""]
    if details:
        for label, value in details:
            lines.append(f"{label}: {value}")
        lines.append("")
    if credentials:
        lines += [
            "Your login details",
            f"Email: {credentials['email']}",
            f"Temporary password: {credentials['password']}",
            "",
        ]
    if steps:
        lines.append("What to do next")
        lines += [f"{i}. {step}" for i, step in enumerate(steps, 1)]
        lines.append("")
    if button:
        lines += [f"{button[0]}: {button[1]}", ""]
    if note:
        lines += [note, ""]
    lines += ["Warm regards,", SCHOOL_NAME]

    message = Message(subject=subject, recipients=[recipient], body="\n".join(lines))

    logo_path = os.path.join(app.root_path, "static", "img", "logo.png")
    has_logo = os.path.exists(logo_path)

    message.html = render_template(
        "email/message.html",
        school_name=SCHOOL_NAME,
        has_logo=has_logo,
        name=name,
        heading=heading,
        intro=intro,
        details=details,
        credentials=credentials,
        steps=steps,
        button=button,
        note=note,
    )

    if has_logo:
        with open(logo_path, "rb") as logo:
            message.attach(
                "logo.png", "image/png", logo.read(), "inline",
                headers=[("Content-ID", "<logo>")],
            )

    return message


def send_reset_email(user, link):
    message = compose_email(
        recipient=user.email,
        subject="Reset your password",
        name=user.full_name,
        heading="Reset your password",
        intro=[
            "We received a request to reset your password. "
            "Click the button below to choose a new one. This link expires in 30 minutes."
        ],
        button=("Reset password", link),
        note="If you did not ask for this, you can safely ignore this email. Your password will not change.",
    )
    mail.send(message)


def build_welcome_messages(user, password, student=None, fee=None):
    login_link = full_url("login")
    credentials = {"email": user.email, "password": password}

    steps = [
        "Log in with the details above.",
        "Change the temporary password to one only you know.",
        "Complete your profile by adding your phone number and address.",
    ]

    if user.role == "student":
        class_name = student.school_class.name if student and student.school_class else "To be confirmed"
        details = [
            ("Admission number", student.admission_no),
            ("Class", class_name),
        ]
        if fee:
            details.append((f"School fee ({fee[0]})", money(fee[1])))
        else:
            details.append(("School fee", "The school office will tell you the amount"))
        subject = f"Admission into {SCHOOL_NAME}"
        heading = "Congratulations on your admission"
        intro = [f"You have been admitted into {SCHOOL_NAME}. We are happy to have you with us."]
    elif user.role == "teacher":
        details = [("Role", "Teacher"), ("Staff ID", user.staff_id)]
        subject = f"Welcome to {SCHOOL_NAME}"
        heading = "Welcome to the team"
        intro = [f"You have been added as a teacher at {SCHOOL_NAME}."]
    elif user.role == "parent":
        details = [("Role", "Parent")]
        subject = f"Welcome to {SCHOOL_NAME}"
        heading = "Welcome"
        intro = [
            f"You have been added as a parent at {SCHOOL_NAME}.",
            "You will be able to see your child's results, attendance and fees online.",
        ]
        steps.append(
            "Fill in your child's school details: previous school, class in the former "
            "school, reason for changing school, contact address, year of entry and any "
            "common sickness."
        )
    else:
        details = [("Role", "Administrator")]
        subject = f"Welcome to {SCHOOL_NAME}"
        heading = "Welcome"
        intro = [f"You have been added as an administrator of {SCHOOL_NAME}."]

    messages = [compose_email(
        recipient=user.email,
        subject=subject,
        name=user.full_name,
        heading=heading,
        intro=intro,
        details=details,
        credentials=credentials,
        steps=steps,
        button=("Log in", login_link),
        note="Keep your password private. If you did not expect this email, please contact the school.",
    )]

    if student and student.parent and student.parent.email != user.email:
        class_name = student.school_class.name if student.school_class else "To be confirmed"
        parent_details = [
            ("Student", user.full_name),
            ("Admission number", student.admission_no),
            ("Class", class_name),
        ]
        if fee:
            parent_details.append((f"School fee ({fee[0]})", money(fee[1])))
        messages.append(compose_email(
            recipient=student.parent.email,
            subject=f"Admission into {SCHOOL_NAME}",
            name=student.parent.full_name,
            heading="Your child has been admitted",
            intro=[f"{user.full_name} has been admitted into {SCHOOL_NAME}."],
            details=parent_details,
            steps=[
                "Log in to your parent account.",
                "Fill in your child's school details: previous school, class in the former "
                "school, reason for changing school, contact address and year of entry.",
            ],
            button=("Log in", login_link),
        ))

    return messages


def send_welcome(user, password, student=None, fee=None):
    sent = True
    for message in build_welcome_messages(user, password, student, fee):
        try:
            mail.send(message)
        except Exception as e:
            print("Welcome email error:", repr(e))
            sent = False
    return sent


def make_code(prefix, column):
    model = column.class_
    year = date.today().year
    number = db.session.execute(
        db.select(db.func.count()).select_from(model).where(column.isnot(None))
    ).scalar() + 1
    code = f"{prefix}/{year}/{number:03d}"
    while db.session.execute(db.select(model.id).where(column == code)).first():
        number += 1
        code = f"{prefix}/{year}/{number:03d}"
    return code


def users_with_role(role, current_id=None):
    return db.session.execute(
        db.select(User)
        .where(User.role == role, (User.is_active.is_(True)) | (User.id == current_id))
        .order_by(User.full_name)
    ).scalars().all()


def classes_with_current(current_id=None):
    return db.session.execute(
        db.select(SchoolClass)
        .where((SchoolClass.is_active.is_(True)) | (SchoolClass.id == current_id))
        .order_by(SchoolClass.name)
    ).scalars().all()


def load_user_choices(form):
    form.parent_id.choices = [("", "-- Select parent (optional) --")] + [
        (p.id, f"{p.full_name} - {p.phone or p.email}") for p in users_with_role("parent")
    ]
    form.class_id.choices = [("", "-- Select class --")] + [
        (c.id, c.name) for c in classes_with_current()
    ]


def current_session():
    today = date.today()
    start = today.year if today.month >= 9 else today.year - 1
    return f"{start}/{start + 1}"


def visible_classes():
    query = db.select(SchoolClass).where(SchoolClass.is_active.is_(True)).order_by(SchoolClass.name)
    if g.user.role == "teacher":
        query = query.where(SchoolClass.teacher_id == g.user.id)
    return db.session.execute(query).scalars().all()


def class_pupils(class_id):
    return db.session.execute(
        db.select(Student)
        .join(User, Student.user_id == User.id)
        .where(Student.class_id == class_id, User.is_active.is_(True))
        .order_by(User.full_name)
    ).scalars().all()


def grade_for(total):
    if total >= 70:
        return "A"
    if total >= 60:
        return "B"
    if total >= 50:
        return "C"
    if total >= 45:
        return "D"
    if total >= 40:
        return "E"
    return "F"


def parse_score(raw, maximum):
    raw = (raw or "").strip()
    if raw == "":
        return None
    value = float(raw)
    if value < 0 or value > maximum:
        raise ValueError
    return round(value, 1)


def latest_class_fee(class_id):
    return db.session.execute(
        db.select(Fee.term, Fee.amount_due)
        .join(Student, Fee.student_id == Student.id)
        .where(Student.class_id == class_id)
        .order_by(Fee.term.desc())
        .limit(1)
    ).first()


def broadsheet_view(selected, term, academic_session, term_name):
    pupils = class_pupils(selected.id)
    ids = [s.id for s in pupils]

    found = []
    if ids:
        found = db.session.execute(
            db.select(Result).where(Result.student_id.in_(ids), Result.term == term)
        ).scalars().all()

    subjects = sorted({r.subject for r in found})

    table = {}
    for r in found:
        table.setdefault(r.student_id, {})[r.subject] = r.total

    rows = []
    for s in pupils:
        scores = table.get(s.id, {})
        total = round(sum(scores.values()), 1)
        average = round(total / len(scores), 1) if scores else 0
        rows.append({"student": s, "scores": scores, "total": total, "average": average})

    for row in rows:
        if row["scores"]:
            row["position"] = 1 + sum(
                1 for other in rows if other["scores"] and other["total"] > row["total"]
            )
        else:
            row["position"] = None

    return render_template(
        "broadsheet.html",
        selected=selected,
        term=term,
        term_name=term_name,
        academic_session=academic_session,
        subjects=subjects,
        rows=rows,
        title="Class Broadsheet",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    title = "Login"

    if g.user:
        return redirect(url_for("dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).where(User.email == form.email.data.strip().lower())
        ).scalar_one_or_none()

        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash("This account is inactive. Please contact the school admin.", "danger")
                return render_template("login.html", form=form, title=title)

            session.clear()
            session["user_id"] = user.id
            session.permanent = form.remember.data
            flash("Logged in successfully.", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form, title=title)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if g.user:
        return redirect(url_for("dashboard"))

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).where(User.email == form.email.data.strip().lower())
        ).scalar_one_or_none()

        if user and user.is_active:
            token = user.get_reset_token()
            link = full_url("reset_password", token=token)
            try:
                send_reset_email(user, link)
            except Exception as e:
                print("Reset email error:", repr(e))

        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect(url_for("login"))

    return render_template("forgot_password.html", form=form, title="Forgot Password")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.verify_reset_token(token)

    if not user or not user.is_active:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        user.must_change_password = False
        db.session.commit()
        session.clear()
        flash("Password updated. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", form=form, title="Reset Password")



@app.route("/dashboard")
@login_required
def dashboard():
    counts = {}
    stats = {}
    my_classes = []

    if g.user.role == "admin":
        for role in ("teacher", "parent", "student"):
            counts[role] = db.session.execute(
                db.select(db.func.count()).select_from(User).where(
                    User.role == role, User.is_active.is_(True)
                )
            ).scalar()

        todays = db.session.execute(
            db.select(Attendance.status, db.func.count())
            .where(Attendance.date == date.today())
            .group_by(Attendance.status)
        ).all()
        stats["attendance"] = {status: n for status, n in todays}

        term = db.session.execute(
            db.select(Fee.term).order_by(Fee.term.desc()).limit(1)
        ).scalar()
        stats["term"] = term
        if term:
            due, paid = db.session.execute(
                db.select(
                    db.func.coalesce(db.func.sum(Fee.amount_due), 0),
                    db.func.coalesce(db.func.sum(Fee.amount_paid), 0),
                ).where(Fee.term == term)
            ).one()
            stats["due"] = due
            stats["paid"] = paid
            stats["owing"] = db.session.execute(
                db.select(db.func.count()).select_from(Fee).where(
                    Fee.term == term, Fee.amount_due > Fee.amount_paid
                )
            ).scalar()

        stats["classes"] = db.session.execute(
            db.select(SchoolClass.name, db.func.count(Student.id))
            .select_from(SchoolClass)
            .outerjoin(Student, Student.class_id == SchoolClass.id)
            .where(SchoolClass.is_active.is_(True))
            .group_by(SchoolClass.id)
            .order_by(SchoolClass.name)
        ).all()

    elif g.user.role == "teacher":
        my_classes = visible_classes()

    return render_template(
        "dashboard.html",
        title="Dashboard",
        counts=counts,
        stats=stats,
        my_classes=my_classes,
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    view = request.args.get("view")
    if view not in ("edit", "password", "child"):
        view = "profile"

    child = None
    if view == "child":
        child = db.session.get(Student, request.args.get("child", ""))
        if g.user.role != "parent" or child is None or child.parent_id != g.user.id:
            abort(404)

    profile_form = ProfileForm(obj=g.user, prefix="p")
    password_form = ChangePasswordForm(prefix="c")
    child_form = PupilDetailsForm(obj=child, prefix="d") if child else None

    if child_form and request.method == "GET" and child.year_of_entry is None:
        child_form.year_of_entry.data = date.today().year

    if view == "edit" and profile_form.submit.data and profile_form.validate_on_submit():
        email = profile_form.email.data.strip().lower()

        existing = db.session.execute(
            db.select(User).where(User.email == email, User.id != g.user.id)
        ).scalar_one_or_none()

        if existing:
            flash("Another account already uses that email.", "danger")
        else:
            g.user.full_name = profile_form.full_name.data.strip()
            g.user.email = email
            g.user.phone = clean(profile_form.phone.data)
            g.user.address = clean(profile_form.address.data)
            db.session.commit()
            todo, link = profile_todo(g.user)
            if todo:
                flash("Saved. Please finish the rest of your profile.", "info")
                return redirect(link)
            flash("Your profile is complete.", "success")
            return redirect(url_for("profile"))

    if view == "password" and password_form.submit.data and password_form.validate_on_submit():
        if not check_password_hash(g.user.password_hash, password_form.current_password.data):
            flash("Your current password is incorrect.", "danger")
        elif check_password_hash(g.user.password_hash, password_form.password.data):
            flash("Please choose a password that is different from your current one.", "danger")
        else:
            g.user.password_hash = generate_password_hash(password_form.password.data)
            g.user.must_change_password = False
            db.session.commit()
            flash("Your password was changed.", "success")
            todo, link = profile_todo(g.user)
            if todo:
                flash("Next, please complete your profile.", "info")
                return redirect(link)
            return redirect(url_for("profile"))

    if view == "child" and child_form.submit.data and child_form.validate_on_submit():
        child.common_sickness = clean(child_form.common_sickness.data)
        child.previous_school = clean(child_form.previous_school.data)
        child.previous_class = clean(child_form.previous_class.data)
        child.reason_for_leaving = clean(child_form.reason_for_leaving.data)
        child.contact_address = clean(child_form.contact_address.data)
        child.year_of_entry = child_form.year_of_entry.data
        db.session.commit()
        todo, link = profile_todo(g.user)
        if todo:
            flash(f"Details for {child.user.full_name} were saved. Some items are still needed.", "info")
            return redirect(link)
        flash("Details saved. Your profile is complete.", "success")
        return redirect(url_for("profile"))

    student = None
    if g.user.role == "student":
        student = db.session.execute(
            db.select(Student).where(Student.user_id == g.user.id)
        ).scalar_one_or_none()

    children = []
    if g.user.role == "parent" and view == "profile":
        children = db.session.execute(
            db.select(Student)
            .join(User, Student.user_id == User.id)
            .where(Student.parent_id == g.user.id)
            .order_by(User.full_name)
        ).scalars().all()

    return render_template(
        "profile.html",
        view=view,
        student=student,
        children=children,
        child=child,
        child_form=child_form,
        profile_form=profile_form,
        password_form=password_form,
        title="My Profile",
    )


@app.route("/users")
@role_required("admin")
def users():
    role = request.args.get("role")
    status = request.args.get("status")
    query = db.select(User).order_by(User.role, User.full_name)
    if role in ("admin", "teacher", "parent", "student"):
        query = query.where(User.role == role)
    if status == "inactive":
        query = query.where(User.is_active.is_(False))
    elif status == "active":
        query = query.where(User.is_active.is_(True))
    all_users = db.session.execute(query).scalars().all()
    return render_template("users.html", users=all_users, title="Users")


@app.route("/users/add", methods=["GET", "POST"])
@role_required("admin")
def add_user():
    role = request.args.get("role", "")
    form_class = USER_FORMS.get(role)

    if form_class is None:
        return render_template("add_user.html", form=None, role="", title="Add User")

    form = form_class()
    if role == "student":
        load_user_choices(form)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        existing = db.session.execute(
            db.select(User).where(User.email == email)
        ).scalar_one_or_none()

        if existing:
            flash("A user with that email already exists.", "danger")
            return render_template("add_user.html", form=form, role=role, title="Add User")

        user = User(
            email=email,
            full_name=form.full_name.data.strip(),
            phone=clean(form.phone.data),
            gender=form.gender.data,
            role=role,
            password_hash=generate_password_hash(form.password.data),
            must_change_password=True,
        )

        if role == "teacher":
            user.staff_id = make_code("STF", User.staff_id)
            user.qualification = clean(form.qualification.data)
            user.date_employed = form.date_employed.data
        elif role == "parent":
            user.occupation = clean(form.occupation.data)
            user.address = clean(form.address.data)

        db.session.add(user)

        student = None
        fee_info = None

        if role == "student":
            fee_info = latest_class_fee(form.class_id.data)
            db.session.flush()
            student = Student(
                user_id=user.id,
                parent_id=form.parent_id.data or None,
                class_id=form.class_id.data,
                admission_no=make_code("ADM", Student.admission_no),
                dob=form.dob.data,
            )
            db.session.add(student)
            db.session.flush()
            if fee_info:
                db.session.add(Fee(
                    student_id=student.id,
                    term=fee_info[0],
                    amount_due=fee_info[1],
                    amount_paid=0,
                ))

        db.session.commit()

        emailed = send_welcome(user, form.password.data, student, fee_info)

        if emailed:
            flash(f"{user.full_name} was added as {role}. A welcome email was sent.", "success")
        else:
            flash(
                f"{user.full_name} was added as {role}, but the welcome email could not be sent. "
                "Please give them their login details yourself.",
                "danger",
            )
        return redirect(url_for("students" if role == "student" else "users"))

    if form.errors:
        print("ADD USER ERRORS:", form.errors)

    return render_template("add_user.html", form=form, role=role, title="Add User")


@app.route("/users/<user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user(user_id):
    user = db.get_or_404(User, user_id)
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        existing = db.session.execute(
            db.select(User).where(User.email == email, User.id != user.id)
        ).scalar_one_or_none()

        if existing:
            flash("Another user already has that email.", "danger")
            return render_template("edit_user.html", form=form, user=user, title="Edit User")

        if user.id == g.user.id and form.role.data != "admin":
            flash("You cannot remove your own admin role.", "danger")
            return render_template("edit_user.html", form=form, user=user, title="Edit User")

        if user.id == g.user.id and not form.is_active.data:
            flash("You cannot deactivate your own account.", "danger")
            return render_template("edit_user.html", form=form, user=user, title="Edit User")

        user.full_name = form.full_name.data.strip()
        user.email = email
        user.phone = clean(form.phone.data)
        user.role = form.role.data
        user.is_active = form.is_active.data

        if form.new_password.data:
            user.password_hash = generate_password_hash(form.new_password.data)
            if user.id != g.user.id:
                user.must_change_password = True

        db.session.commit()

        flash(f"{user.full_name} was updated.", "success")
        return redirect(url_for("users"))

    return render_template("edit_user.html", form=form, user=user, title="Edit User")


@app.route("/classes", methods=["GET", "POST"])
@role_required("admin")
def classes():
    form = ClassForm(prefix="a")
    promote_form = PromoteForm(prefix="m")

    form.teacher_id.choices = [("", "-- No class teacher yet --")] + [
        (t.id, t.full_name) for t in users_with_role("teacher")
    ]

    class_choices = [("", "-- Select class --")] + [
        (c.id, c.name) for c in classes_with_current()
    ]
    promote_form.from_id.choices = class_choices
    promote_form.to_id.choices = class_choices

    if form.submit.data and form.validate_on_submit():
        name = form.name.data.strip()

        existing = db.session.execute(
            db.select(SchoolClass).where(db.func.lower(SchoolClass.name) == name.lower())
        ).scalar_one_or_none()

        if existing:
            flash("A class with that name already exists.", "danger")
        else:
            db.session.add(SchoolClass(name=name, teacher_id=form.teacher_id.data or None))
            db.session.commit()
            flash(f"Class {name} was added.", "success")
            return redirect(url_for("classes"))

    if promote_form.submit.data and promote_form.validate_on_submit():
        if promote_form.from_id.data == promote_form.to_id.data:
            flash("Please choose two different classes.", "danger")
        else:
            pupils = class_pupils(promote_form.from_id.data)
            target = db.session.get(SchoolClass, promote_form.to_id.data)
            for pupil in pupils:
                pupil.class_id = target.id
            db.session.commit()
            flash(f"{len(pupils)} students were moved to {target.name}.", "success")
            return redirect(url_for("classes"))

    all_classes = db.session.execute(
        db.select(SchoolClass).order_by(SchoolClass.name)
    ).scalars().all()

    student_counts = dict(db.session.execute(
        db.select(Student.class_id, db.func.count()).group_by(Student.class_id)
    ).all())

    return render_template(
        "classes.html",
        classes=all_classes,
        student_counts=student_counts,
        form=form,
        promote_form=promote_form,
        title="Classes",
    )


@app.route("/classes/<class_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_class(class_id):
    school_class = db.get_or_404(SchoolClass, class_id)
    form = EditClassForm(obj=school_class)

    form.teacher_id.choices = [("", "-- No class teacher yet --")] + [
        (t.id, t.full_name) for t in users_with_role("teacher", school_class.teacher_id)
    ]

    if form.validate_on_submit():
        name = form.name.data.strip()

        existing = db.session.execute(
            db.select(SchoolClass).where(
                db.func.lower(SchoolClass.name) == name.lower(),
                SchoolClass.id != school_class.id,
            )
        ).scalar_one_or_none()

        if existing:
            flash("Another class already has that name.", "danger")
            return render_template("edit_class.html", form=form, school_class=school_class, title="Edit Class")

        school_class.name = name
        school_class.teacher_id = form.teacher_id.data or None
        school_class.is_active = form.is_active.data
        db.session.commit()

        flash(f"Class {school_class.name} was updated.", "success")
        return redirect(url_for("classes"))

    return render_template("edit_class.html", form=form, school_class=school_class, title="Edit Class")


@app.route("/students")
@role_required("admin")
def students():
    search = request.args.get("q", "").strip()
    selected_class = request.args.get("class_id", "")

    query = (
        db.select(Student)
        .join(User, Student.user_id == User.id)
        .order_by(User.full_name)
    )

    if selected_class:
        query = query.where(Student.class_id == selected_class)

    if search:
        like = f"%{search}%"
        query = query.where(User.full_name.ilike(like) | Student.admission_no.ilike(like))

    all_students = db.session.execute(query).scalars().all()
    all_classes = db.session.execute(
        db.select(SchoolClass).order_by(SchoolClass.name)
    ).scalars().all()

    return render_template(
        "students.html",
        students=all_students,
        classes=all_classes,
        search=search,
        selected_class=selected_class,
        title="Students",
    )


@app.route("/students/<student_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_student(student_id):
    student = db.get_or_404(Student, student_id)
    form = EditStudentForm(obj=student)

    form.class_id.choices = [("", "-- Select class --")] + [
        (c.id, c.name) for c in classes_with_current(student.class_id)
    ]
    form.parent_id.choices = [("", "-- No parent linked --")] + [
        (p.id, f"{p.full_name} - {p.phone or p.email}")
        for p in users_with_role("parent", student.parent_id)
    ]

    if form.validate_on_submit():
        student.class_id = form.class_id.data
        student.parent_id = form.parent_id.data or None
        student.dob = form.dob.data
        db.session.commit()

        flash(f"{student.user.full_name} was updated.", "success")
        return redirect(url_for("students"))

    return render_template("edit_student.html", form=form, student=student, title="Edit Student")


@app.route("/fees", methods=["GET", "POST"])
@role_required("admin")
def fees():
    form = ClassFeeForm()
    form.class_id.choices = [("", "-- Select class --")] + [
        (c.id, c.name) for c in classes_with_current()
    ]

    if request.method == "GET":
        form.academic_session.data = current_session()

    if form.validate_on_submit():
        term = f"{form.academic_session.data.strip()} {form.term_name.data}"
        amount = round(form.amount.data, 2)

        pupils = class_pupils(form.class_id.data)

        if not pupils:
            flash("That class has no active students yet.", "danger")
        else:
            for pupil in pupils:
                fee = db.session.execute(
                    db.select(Fee).where(Fee.student_id == pupil.id, Fee.term == term)
                ).scalar_one_or_none()
                if fee:
                    fee.amount_due = amount
                else:
                    db.session.add(Fee(student_id=pupil.id, term=term, amount_due=amount, amount_paid=0))
            db.session.commit()
            flash(f"Fee of {amount:,.2f} set for {len(pupils)} students for {term}.", "success")
            return redirect(url_for("fees", term=term))

    terms = [t for (t,) in db.session.execute(
        db.select(Fee.term).distinct().order_by(Fee.term.desc())
    ).all()]
    selected_term = request.args.get("term") or (terms[0] if terms else "")
    selected_class = request.args.get("class_id", "")
    owing_only = bool(request.args.get("owing"))

    rows = []
    if selected_term:
        query = (
            db.select(Fee)
            .join(Student, Fee.student_id == Student.id)
            .join(User, Student.user_id == User.id)
            .where(Fee.term == selected_term)
            .order_by(User.full_name)
        )
        if selected_class:
            query = query.where(Student.class_id == selected_class)
        rows = db.session.execute(query).scalars().all()
        if owing_only:
            rows = [f for f in rows if f.amount_due - f.amount_paid > 0]

    total_due = round(sum(f.amount_due for f in rows), 2)
    total_paid = round(sum(f.amount_paid for f in rows), 2)

    all_classes = db.session.execute(
        db.select(SchoolClass).order_by(SchoolClass.name)
    ).scalars().all()

    return render_template(
        "fees.html",
        form=form,
        rows=rows,
        terms=terms,
        classes=all_classes,
        selected_term=selected_term,
        selected_class=selected_class,
        owing_only=owing_only,
        total_due=total_due,
        total_paid=total_paid,
        title="Fees",
    )


@app.route("/fees/<student_id>", methods=["GET", "POST"])
@role_required("admin")
def student_fees(student_id):
    student = db.get_or_404(Student, student_id)

    fee_rows = db.session.execute(
        db.select(Fee).where(Fee.student_id == student.id).order_by(Fee.term.desc())
    ).scalars().all()

    form = PaymentForm()
    form.fee_id.choices = [
        (f.id, f"{f.term} (balance {f.amount_due - f.amount_paid:,.2f})")
        for f in fee_rows if f.amount_due - f.amount_paid > 0
    ]

    if form.validate_on_submit():
        fee = db.session.get(Fee, form.fee_id.data)

        if fee is None or fee.student_id != student.id:
            abort(404)

        amount = round(form.amount.data, 2)
        balance = round(fee.amount_due - fee.amount_paid, 2)

        if amount > balance:
            flash(f"That is more than the balance of {balance:,.2f}.", "danger")
        else:
            payment = Payment(
                fee_id=fee.id,
                amount=amount,
                method=form.method.data,
                paid_on=form.paid_on.data,
                receipt_no=make_code("RCP", Payment.receipt_no),
                recorded_by=g.user.id,
            )
            fee.amount_paid = round(fee.amount_paid + amount, 2)
            db.session.add(payment)
            db.session.commit()
            flash(f"Payment recorded. Receipt {payment.receipt_no}.", "success")
            return redirect(url_for("student_fees", student_id=student.id))

    return render_template(
        "student_fees.html",
        student=student,
        fee_rows=fee_rows,
        form=form,
        title="Student Fees",
    )


@app.route("/attendance", methods=["GET", "POST"])
@role_required("teacher", "admin")
def attendance():
    my_classes = visible_classes()
    if not my_classes:
        return render_template("attendance.html", my_classes=[], title="Attendance")

    selected = next(
        (c for c in my_classes if c.id == request.values.get("class_id")),
        my_classes[0],
    )

    today = date.today()
    try:
        day = date.fromisoformat(request.values.get("day", ""))
    except ValueError:
        day = today
    if day > today:
        day = today

    pupils = class_pupils(selected.id)
    ids = [s.id for s in pupils]

    records = {}
    if ids:
        found = db.session.execute(
            db.select(Attendance).where(Attendance.date == day, Attendance.student_id.in_(ids))
        ).scalars().all()
        records = {a.student_id: a for a in found}

    sheet = SheetForm()
    if request.method == "POST" and pupils and sheet.validate_on_submit():
        for s in pupils:
            status = request.form.get(f"status_{s.id}")
            if status not in ("present", "absent", "late"):
                continue
            record = records.get(s.id)
            if record:
                record.status = status
            else:
                db.session.add(Attendance(student_id=s.id, date=day, status=status))
        db.session.commit()
        flash(f"Attendance for {selected.name} on {day.strftime('%d %b %Y')} was saved.", "success")
        return redirect(url_for("attendance", class_id=selected.id, day=day.isoformat()))

    marked = {sid: a.status for sid, a in records.items()}
    summary = None
    if marked:
        values = list(marked.values())
        summary = {key: values.count(key) for key in ("present", "absent", "late")}

    return render_template(
        "attendance.html",
        my_classes=my_classes,
        selected=selected,
        pupils=pupils,
        marked=marked,
        summary=summary,
        day=day,
        today=today,
        sheet=sheet,
        title="Attendance",
    )


@app.route("/results", methods=["GET", "POST"])
@role_required("teacher", "admin")
def results():
    my_classes = visible_classes()
    if not my_classes:
        return render_template("results.html", my_classes=[], title="Results")

    selected = next(
        (c for c in my_classes if c.id == request.values.get("class_id")),
        my_classes[0],
    )

    academic_session = (clean(request.values.get("academic_session")) or current_session())[:20]
    term_name = request.values.get("term")
    if term_name not in TERM_NAMES:
        term_name = TERM_NAMES[0]
    subject = " ".join((request.values.get("subject") or "").split())
    term = f"{academic_session} {term_name}"

    if request.args.get("view") == "broadsheet":
        return broadsheet_view(selected, term, academic_session, term_name)

    pupils = class_pupils(selected.id)

    existing = {}
    if subject and pupils:
        found = db.session.execute(
            db.select(Result).where(
                Result.student_id.in_([s.id for s in pupils]),
                Result.term == term,
                db.func.lower(Result.subject) == subject.lower(),
            )
        ).scalars().all()
        existing = {r.student_id: r for r in found}

    sheet = SheetForm()
    if request.method == "POST" and subject and pupils and sheet.validate_on_submit():
        problems = []
        parsed = []
        for s in pupils:
            try:
                ca = parse_score(request.form.get(f"ca_{s.id}"), CA_MAX)
                exam = parse_score(request.form.get(f"exam_{s.id}"), EXAM_MAX)
            except ValueError:
                problems.append(s.user.full_name)
                continue
            if ca is None and exam is None:
                continue
            parsed.append((s, ca or 0, exam or 0))

        if problems:
            flash(
                "Check the scores for: " + ", ".join(problems)
                + f". CA is out of {CA_MAX} and exam is out of {EXAM_MAX}.",
                "danger",
            )
        else:
            for s, ca, exam in parsed:
                total = round(ca + exam, 1)
                record = existing.get(s.id)
                if record:
                    record.ca = ca
                    record.exam = exam
                    record.total = total
                    record.grade = grade_for(total)
                else:
                    db.session.add(Result(
                        student_id=s.id, subject=subject, term=term,
                        ca=ca, exam=exam, total=total, grade=grade_for(total),
                    ))
            db.session.commit()
            flash(f"{subject} results saved for {len(parsed)} students.", "success")
            return redirect(url_for(
                "results", class_id=selected.id, academic_session=academic_session,
                term=term_name, subject=subject,
            ))

    rows = []
    for s in pupils:
        r = existing.get(s.id)
        if request.method == "POST":
            ca = request.form.get(f"ca_{s.id}", "")
            exam = request.form.get(f"exam_{s.id}", "")
        else:
            ca = "%g" % r.ca if r else ""
            exam = "%g" % r.exam if r else ""
        rows.append({"student": s, "ca": ca, "exam": exam})

    used = [name for (name,) in db.session.execute(
        db.select(Result.subject)
        .join(Student, Result.student_id == Student.id)
        .where(Student.class_id == selected.id)
        .distinct()
    ).all()]
    subject_options = sorted(set(DEFAULT_SUBJECTS) | set(used))

    return render_template(
        "results.html",
        my_classes=my_classes,
        selected=selected,
        academic_session=academic_session,
        term_name=term_name,
        term_names=TERM_NAMES,
        subject=subject,
        subject_options=subject_options,
        rows=rows,
        ca_max=CA_MAX,
        exam_max=EXAM_MAX,
        sheet=sheet,
        title="Results",
    )


@app.route("/my")
@role_required("student", "parent", "admin")
def my():
    if g.user.role == "admin":
        picked = db.session.get(Student, request.args.get("child", ""))
        children = [picked] if picked else []
    elif g.user.role == "student":
        children = db.session.execute(
            db.select(Student).where(Student.user_id == g.user.id)
        ).scalars().all()
    else:
        children = db.session.execute(
            db.select(Student)
            .join(User, Student.user_id == User.id)
            .where(Student.parent_id == g.user.id)
            .order_by(User.full_name)
        ).scalars().all()

    child = next((c for c in children if c.id == request.args.get("child")), None)
    if child is None and children:
        child = children[0]

    tab = request.args.get("tab")
    if tab not in ("results", "attendance", "fees"):
        tab = "results"

    context = {}

    if child and tab == "results":
        terms = [t for (t,) in db.session.execute(
            db.select(Result.term)
            .where(Result.student_id == child.id)
            .distinct()
            .order_by(Result.term.desc())
        ).all()]
        term = request.args.get("term")
        if term not in terms:
            term = terms[0] if terms else ""
        rows = []
        position = None
        cohort = 0
        if term:
            rows = db.session.execute(
                db.select(Result)
                .where(Result.student_id == child.id, Result.term == term)
                .order_by(Result.subject)
            ).scalars().all()
            if child.class_id:
                totals = db.session.execute(
                    db.select(Result.student_id, db.func.sum(Result.total))
                    .join(Student, Result.student_id == Student.id)
                    .where(Student.class_id == child.class_id, Result.term == term)
                    .group_by(Result.student_id)
                ).all()
                cohort = len(totals)
                mine = next((t for sid, t in totals if sid == child.id), 0)
                position = 1 + sum(1 for sid, t in totals if t > mine)
        total = round(sum(r.total for r in rows), 1)
        average = round(total / len(rows), 1) if rows else 0
        context = {
            "terms": terms,
            "term": term,
            "rows": rows,
            "total": total,
            "average": average,
            "position": position,
            "cohort": cohort,
        }

    elif child and tab == "attendance":
        records = db.session.execute(
            db.select(Attendance)
            .where(Attendance.student_id == child.id)
            .order_by(Attendance.date.desc())
        ).scalars().all()
        counts = {key: sum(1 for a in records if a.status == key) for key in ("present", "absent", "late")}
        days = len(records)
        rate = round((counts["present"] + counts["late"]) / days * 100) if days else 0
        context = {"records": records[:60], "counts": counts, "days": days, "rate": rate}

    elif child and tab == "fees":
        fee_rows = db.session.execute(
            db.select(Fee).where(Fee.student_id == child.id).order_by(Fee.term.desc())
        ).scalars().all()
        context = {"fee_rows": fee_rows}

    return render_template(
        "my.html",
        children=children,
        child=child,
        tab=tab,
        title="Student Record" if g.user.role == "admin" else "My Records",
        **context,
    )

@app.route("/")
def home():
    return render_template("home.html")