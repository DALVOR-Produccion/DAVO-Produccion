from datetime import datetime
from models import db


class TestResult(db.Model):

    __tablename__ = "test_results"

    id = db.Column(db.Integer, primary_key=True)

    student_rut = db.Column(
        db.String(20),
        nullable=False
    )

    student_name = db.Column(
        db.String(150),
        nullable=False
    )

    school = db.Column(
        db.String(150)
    )

    school_id = db.Column(
        db.Integer,
        nullable=True
    )

    student_type = db.Column(
        db.String(20),
        default="COLEGIO"
    )

    course = db.Column(
        db.String(50),
        nullable=False
    )

    section = db.Column(
    db.String(5),
    nullable=True
    )

    test_type = db.Column(
        db.String(50),
        nullable=False
    )

    education_type = db.Column(
        db.String(50)
    )

    tp_area = db.Column(
        db.String(50)
    )

    answers = db.Column(
        db.Text
    )

    score_cientifica = db.Column(
        db.Integer,
        default=0
    )

    score_humanista = db.Column(
        db.Integer,
        default=0
    )

    score_artistica = db.Column(
        db.Integer,
        default=0
    )

    score_tecnica = db.Column(
        db.Integer,
        default=0
    )

    score_social = db.Column(
        db.Integer,
        default=0
    )

    main_area = db.Column(
        db.String(50)
    )

    secondary_area = db.Column(
        db.String(50)
    )

    suggested_path = db.Column(
        db.String(100)
    )

    motivation = db.Column(
        db.String(150)
    )

    # 🔥 NUEVO CAMPO
    # activo / archivado
    status = db.Column(
        db.String(20),
        default="activo"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
