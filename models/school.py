from models import db


class School(db.Model):

    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)

    rbd = db.Column(db.String(20), unique=True, index=True)

    rut = db.Column(db.String(20))

    name = db.Column(db.String(200), nullable=False, index=True)

    comuna = db.Column(db.String(100), index=True)

    region = db.Column(db.String(100))

    active = db.Column(db.Boolean, default=True)
