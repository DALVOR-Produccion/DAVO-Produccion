"""Control institucional por colegio, curso y paralelo; tablas nuevas solamente."""
from datetime import datetime
from models import db


class WorkshopAccess(db.Model):
    __tablename__ = 'workshop_access'
    school_id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    valid_until = db.Column(db.Date, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, nullable=True)


class WorkshopSlot(db.Model):
    __tablename__ = 'workshop_slots'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, nullable=False, index=True)
    course = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(20), nullable=False)
    current_enrollment_id = db.Column(db.Integer, nullable=True)
    revision = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint('school_id', 'course', 'section', name='uq_workshop_group'),)
    __mapper_args__ = {'version_id_col': revision}


class WorkshopEnrollment(db.Model):
    __tablename__ = 'workshop_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('workshop_slots.id'), nullable=False, index=True)
    workshop_id = db.Column(db.String(60), nullable=False)
    bank_version = db.Column(db.String(60), nullable=False)
    started_on = db.Column(db.Date, nullable=False)
    available_on = db.Column(db.Date, nullable=False)
    sessions = db.Column(db.Integer, nullable=False)
    sessions_done = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default='activo')
    feedback = db.Column(db.Text, nullable=True)
    replacement_reason = db.Column(db.Text, nullable=True)
    replacement_decision = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
