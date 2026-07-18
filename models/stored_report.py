from datetime import datetime

from models import db


class StoredReport(db.Model):
    """
    Almacena una copia permanente del informe PDF generado
    para cada resultado de test.

    Cada TestResult puede tener solamente un informe guardado.
    Si el PDF se vuelve a generar, el registro existente se actualiza.
    """

    __tablename__ = "stored_reports"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    result_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "test_results.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        unique=True,
        index=True
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    mime_type = db.Column(
        db.String(100),
        nullable=False,
        default="application/pdf"
    )

    pdf_data = db.Column(
        db.LargeBinary,
        nullable=False
    )

    size_bytes = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    result = db.relationship(
        "TestResult",
        backref=db.backref(
            "stored_report",
            uselist=False,
            cascade="all, delete-orphan",
            passive_deletes=True
        )
    )

    def __repr__(self):
        return (
            f"<StoredReport "
            f"id={self.id} "
            f"result_id={self.result_id} "
            f"filename='{self.filename}'>"
        )
