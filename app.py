from flask import Flask, render_template, session
from sqlalchemy import text

from config import Config
from models import db
from models.user import User
from models.stored_report import StoredReport
from routes.auth import auth_bp, login_required
from routes.students import students_bp
from routes.test import test_bp
from routes.test_8 import test_8_bp
from routes.test_1m import test_1m_bp
from routes.test_2m import test_2m_bp
from routes.test_3m import test_3m_bp
from routes.test_4m import test_4m_bp
from routes.admin import admin_bp
from routes.colegio import colegio_bp
from routes.talleres import talleres_bp
from routes.historial import historial_bp


def create_default_admin():
    admin = User.query.filter_by(username="admin").first()

    if not admin:
        admin = User(
            username="admin",
            full_name="Administrador DAVO",
            role="admin",
            is_active=True,
        )
        admin.set_password("Davo@2026Segura")
        db.session.add(admin)
        db.session.commit()


def actualizar_columna_section():
    """
    Revisa el tamaño de la columna students.section.

    Si la columna tiene menos de 20 caracteres, la amplía a VARCHAR(20).
    La operación no elimina ni modifica los registros existentes.
    """

    try:
        resultado = db.session.execute(
            text(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'students'
                  AND column_name = 'section'
                """
            )
        ).scalar()

        if resultado is None:
            print(
                "AVISO: No se encontró la columna students.section. "
                "No se realizó ninguna modificación."
            )
            return

        if resultado < 20:
            db.session.execute(
                text(
                    """
                    ALTER TABLE students
                    ALTER COLUMN section TYPE VARCHAR(20)
                    """
                )
            )
            db.session.commit()

            print(
                "CORRECCIÓN REALIZADA: "
                "students.section fue ampliada a VARCHAR(20)."
            )
        else:
            print(
                "VERIFICACIÓN CORRECTA: "
                f"students.section ya permite {resultado} caracteres."
            )

    except Exception as error:
        db.session.rollback()
        print(
            "ERROR AL ACTUALIZAR students.section: "
            f"{type(error).__name__}: {error}"
        )


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(test_8_bp)
    app.register_blueprint(test_1m_bp)
    app.register_blueprint(test_2m_bp)
    app.register_blueprint(test_3m_bp)
    app.register_blueprint(test_4m_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(colegio_bp)
    app.register_blueprint(talleres_bp)
    app.register_blueprint(historial_bp)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template(
            "dashboard.html",
            full_name=session.get("full_name"),
            role=session.get("role"),
        )

    with app.app_context():
        db.create_all()

        # Corrige automáticamente la longitud de students.section.
        actualizar_columna_section()

        from services.seed_schools import cargar_colegios_iniciales

        cantidad = cargar_colegios_iniciales()

        if cantidad:
            print(f"Se cargaron {cantidad} colegios iniciales.")

        create_default_admin()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False)
