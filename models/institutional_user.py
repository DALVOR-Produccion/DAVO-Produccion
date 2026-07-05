from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from models import db


class InstitutionalUser(db.Model):

    __tablename__ = "institutional_users"

    id = db.Column(db.Integer, primary_key=True)

    # DATOS PERSONALES

    rut = db.Column(db.String(20), unique=True, nullable=False)

    full_name = db.Column(db.String(150), nullable=False)

    cargo = db.Column(db.String(100), nullable=True)

    email = db.Column(db.String(120), nullable=True)

    phone = db.Column(db.String(50), nullable=True)

    # DATOS DEL COLEGIO

    school_id = db.Column(db.Integer, nullable=False)

    school_name = db.Column(db.String(200), nullable=False)

    # ACCESO

    username = db.Column(db.String(80), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(50), default="colegio")

    # CONTROL Y SEGURIDAD

    is_active = db.Column(db.Boolean, default=True)

    must_change_password = db.Column(db.Boolean, default=True)

    max_students = db.Column(db.Integer, default=500)

    last_login = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # MÉTODOS

    def set_password(self, password):

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):

        return check_password_hash(self.password_hash, password)
