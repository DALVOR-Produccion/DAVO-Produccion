from datetime import datetime
from models import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_rut = db.Column(db.String(20), nullable=False, index=True)
    student_name = db.Column(db.String(150), nullable=False)
    school = db.Column(db.String(150), nullable=False)
    school_id = db.Column(db.Integer, nullable=True)
    student_type = db.Column(db.String(20), default="COLEGIO")
    course = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(20), nullable=True)
    student_email = db.Column(db.String(120), nullable=True)

    guardian_rut = db.Column(db.String(20), nullable=False)
    guardian_name = db.Column(db.String(150), nullable=False)
    guardian_email = db.Column(db.String(120), nullable=True)

    test_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
