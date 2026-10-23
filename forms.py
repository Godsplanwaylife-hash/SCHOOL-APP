import re
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     SelectField, DateField, TextAreaField, FloatField,IntegerField)
from wtforms.validators import (DataRequired, ValidationError, Email,
                                EqualTo, Length, Optional, NumberRange)


def validate_password_strength(form, field):
    password = field.data

    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[0-9]', password):
        raise ValidationError('Password must contain at least one digit.')
    if not re.search(r'[@#$%^&*!?_\-]', password):
        raise ValidationError('Password must contain at least one special character (@#$%^&*!?_-).')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(min=8), validate_password_strength])
    confirm = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')


class BaseUserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    gender = SelectField('Gender', choices=[
        ('', '-- Select gender --'),
        ('Male', 'Male'),
        ('Female', 'Female'),
    ], validators=[DataRequired(message='Please select a gender.')])
    password = PasswordField('Temporary Password', validators=[
        DataRequired(), Length(min=8), validate_password_strength])
    confirm = PasswordField('Confirm Temporary Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Add User')


class AddStudentForm(BaseUserForm):
    class_id = SelectField('Class', choices=[], validators=[
        DataRequired(message='Please select a class.')])
    dob = DateField('Date of Birth', validators=[
        DataRequired(message='Date of birth is required.')])
    parent_id = SelectField('Parent', choices=[], validators=[Optional()])


class AddTeacherForm(BaseUserForm):
    qualification = StringField('Qualification', validators=[
        DataRequired(message='Qualification is required.'), Length(max=150)])
    date_employed = DateField('Date Employed', validators=[Optional()])


class AddParentForm(BaseUserForm):
    occupation = StringField('Occupation', validators=[Optional(), Length(max=100)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=255)])


class AddAdminForm(BaseUserForm):
    pass


class EditUserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    role = SelectField('Role', choices=[
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
        ('student', 'Student'),
        ('admin', 'Admin'),
    ], validators=[DataRequired()])
    is_active = BooleanField('Account is active')
    new_password = PasswordField('New Password (leave empty to keep the current one)', validators=[
        Optional(), Length(min=8), validate_password_strength])
    submit = SubmitField('Save Changes')


class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=30)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Profile')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(min=8), validate_password_strength])
    confirm = PasswordField('Confirm New Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Change Password')


class ClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(max=50)])
    teacher_id = SelectField('Class Teacher', choices=[], validators=[Optional()])
    submit = SubmitField('Save Class')


class EditClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired(), Length(max=50)])
    teacher_id = SelectField('Class Teacher', choices=[], validators=[Optional()])
    is_active = BooleanField('Class is active')
    submit = SubmitField('Save Class')


class EditStudentForm(FlaskForm):
    class_id = SelectField('Class', choices=[], validators=[DataRequired()])
    parent_id = SelectField('Parent', choices=[], validators=[Optional()])
    dob = DateField('Date of Birth', validators=[DataRequired()])
    submit = SubmitField('Save Student')


class ClassFeeForm(FlaskForm):
    class_id = SelectField('Class', choices=[], validators=[
        DataRequired(message='Please select a class.')])
    academic_session = StringField('Session', validators=[DataRequired(), Length(max=20)])
    term_name = SelectField('Term', choices=[
        ('First Term', 'First Term'),
        ('Second Term', 'Second Term'),
        ('Third Term', 'Third Term'),
    ], validators=[DataRequired()])
    amount = FloatField('Fee per student', validators=[
        DataRequired(message='Enter the amount.'), NumberRange(min=1)])
    submit = SubmitField('Set Fee')


class PaymentForm(FlaskForm):
    fee_id = SelectField('Term', choices=[], validators=[DataRequired()])
    amount = FloatField('Amount paid', validators=[
        DataRequired(message='Enter the amount.'), NumberRange(min=1)])
    method = SelectField('Method', choices=[
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('POS', 'POS'),
    ], validators=[DataRequired()])
    paid_on = DateField('Date', default=date.today, validators=[DataRequired()])
    submit = SubmitField('Record Payment')


class SheetForm(FlaskForm):
    submit = SubmitField('Save')


class PromoteForm(FlaskForm):
    from_id = SelectField('Move students from', choices=[], validators=[
        DataRequired(message='Choose the current class.')])
    to_id = SelectField('Move them to', choices=[], validators=[
        DataRequired(message='Choose the new class.')])
    submit = SubmitField('Move Students')


class PupilDetailsForm(FlaskForm):
    common_sickness = TextAreaField('Common sickness (optional)', validators=[
        Optional(), Length(max=1000)])
    previous_school = TextAreaField('Previous school attended (name and details)', validators=[
        DataRequired(message='Please enter the previous school, or write None.'),
        Length(max=1000)])
    previous_class = StringField('Class in the former school', validators=[
        DataRequired(message='Please enter the class, or write None.'),
        Length(max=100)])
    reason_for_leaving = TextAreaField('Reason for changing school', validators=[
        DataRequired(message='Please enter a reason, or write None.'),
        Length(max=1000)])
    contact_address = TextAreaField('Contact address of the pupil', validators=[
        DataRequired(message='Please enter the contact address.'),
        Length(max=1000)])
    year_of_entry = IntegerField('Year of entry into the school', validators=[
        DataRequired(message='Enter the year, for example 2026.'),
        NumberRange(min=1990, max=date.today().year + 1)])
    submit = SubmitField('Save Details')