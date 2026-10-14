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
    db.String(20),
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

    @property
    def observed_main_area(self):
        from services.basic_results import display_area
        return display_area(self, 'main_area')

    @property
    def observed_secondary_area(self):
        from services.basic_results import display_area
        return display_area(self, 'secondary_area')

    @property
    def observed_path(self):
        from services.basic_results import COURSES, continuity
        return continuity(self)['modalidad'] if self.course == '8° Básico' else self.suggested_path

    @property
    def score_rows(self):
        from services.basic_results import score_rows
        return score_rows(self)
