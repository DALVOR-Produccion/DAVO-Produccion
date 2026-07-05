from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

from models import db
from models.student import Student
from models.test_result import TestResult
from models.school import School
from services.rut_utils import is_valid_rut, normalize_rut


students_bp = Blueprint("students", __name__, url_prefix="/students")


@students_bp.route("/buscar_colegios")
def buscar_colegios():

    texto = request.args.get("q", "").strip().upper()

    if len(texto) < 2:
        return jsonify([])

    colegios = (
        School.query
        .filter(School.active == True)
        .filter(
            db.or_(
                School.name.ilike(f"%{texto}%"),
                School.comuna.ilike(f"%{texto}%"),
                School.rbd.ilike(f"%{texto}%")
            )
        )
        .order_by(School.name.asc())
        .limit(10)
        .all()
    )

    resultados = []

    for colegio in colegios:
        resultados.append({
            "id": colegio.id,
            "rbd": colegio.rbd,
            "name": colegio.name,
            "comuna": colegio.comuna,
            "rut": colegio.rut,
            "label": f"{colegio.name} - {colegio.comuna} - RBD {colegio.rbd}"
        })

    return jsonify(resultados)


@students_bp.route("/new", methods=["GET", "POST"])
def new_student():

    courses = [
        "6° Básico",
        "7° Básico",
        "8° Básico",
        "1° Medio",
        "2° Medio",
        "3° Medio",
        "4° Medio",
    ]

    test_types = [
        "Test Básico",
        "Test Avanzado",
    ]

    if request.method == "POST":

        student_rut_raw = request.form.get("student_rut", "").strip()
        student_name = request.form.get("student_name", "").strip()
        course = request.form.get("course", "").strip()
        section = request.form.get("section", "SIN PARALELO").strip().upper()
        student_email = request.form.get("student_email", "").strip()

        student_type_form = request.form.get("student_type", "colegio").strip()
        school_id_raw = request.form.get("school_id", "").strip()

        guardian_rut_raw = request.form.get("guardian_rut", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_email = request.form.get("guardian_email", "").strip()

        test_type = request.form.get("test_type", "").strip()

        school = ""
        school_id = None
        student_type = "COLEGIO"

        valid_sections = ["SIN PARALELO"] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        if section not in valid_sections:
            section = "SIN PARALELO"

        if not student_rut_raw or not student_name or not course or not test_type:
            flash("Debe completar todos los campos obligatorios.", "warning")
            return render_template("student_form.html", courses=courses, test_types=test_types)

        if not is_valid_rut(student_rut_raw):
            flash("El RUT del alumno no es válido. Ejemplo: 11.111.111-1", "danger")
            return render_template("student_form.html", courses=courses, test_types=test_types)

        student_rut = normalize_rut(student_rut_raw)

        if student_type_form == "particular":

            student_type = "PARTICULAR"
            school = "ALUMNO PARTICULAR"
            school_id = None

            if not guardian_rut_raw or not guardian_name:
                flash("Debe completar los datos del apoderado.", "warning")
                return render_template("student_form.html", courses=courses, test_types=test_types)

            if not is_valid_rut(guardian_rut_raw):
                flash("El RUT del apoderado no es válido. Ejemplo: 11.111.111-1", "danger")
                return render_template("student_form.html", courses=courses, test_types=test_types)

            guardian_rut = normalize_rut(guardian_rut_raw)

        else:

            student_type = "COLEGIO"

            if not school_id_raw:
                flash("Debe seleccionar un colegio desde la lista de sugerencias o marcar alumno particular.", "warning")
                return render_template("student_form.html", courses=courses, test_types=test_types)

            colegio = School.query.get(school_id_raw)

            if not colegio:
                flash("El colegio seleccionado no fue encontrado. Intente nuevamente.", "danger")
                return render_template("student_form.html", courses=courses, test_types=test_types)

            school_id = colegio.id
            school = colegio.name

            guardian_rut = colegio.rut or "SIN RUT"
            guardian_name = colegio.name
            guardian_email = ""

        if test_type == "Test Avanzado":
            flash("El Test Avanzado se encuentra en construcción. Próximamente estará disponible.", "warning")
            return render_template("student_form.html", courses=courses, test_types=test_types)

        current_year = datetime.now().year

        if test_type == "Test Básico" and session.get("role") != "admin":
            existing_free_test = TestResult.query.filter(
                TestResult.student_rut == student_rut,
                TestResult.test_type == "Test Básico",
                TestResult.status == "activo",
                db.extract("year", TestResult.created_at) == current_year
            ).first()

            if existing_free_test:
                flash(
                    f"El alumno con RUT {student_rut} ya realizó el Test Básico durante el año {current_year}. No puede repetirlo este año.",
                    "danger"
                )
                return render_template("student_form.html", courses=courses, test_types=test_types)

        student = Student(
            student_rut=student_rut,
            student_name=student_name,
            school=school,
            school_id=school_id,
            student_type=student_type,
            course=course,
            section=section,
            student_email=student_email,
            guardian_rut=guardian_rut,
            guardian_name=guardian_name,
            guardian_email=guardian_email,
            test_type=test_type,
        )

        db.session.add(student)
        db.session.commit()

        session["student_rut"] = student_rut
        session["student_name"] = student_name
        session["school"] = school
        session["school_id"] = school_id
        session["student_type"] = student_type
        session["course"] = course
        session["section"] = section

        flash("Datos registrados. Iniciando Test Básico...", "success")

        if course in ["6° Básico", "7° Básico"]:
            return redirect(url_for("test.start_test"))

        if course == "8° Básico":
            return redirect(url_for("test_8.start_test_8"))

        if course == "1° Medio":
            return redirect(url_for("test_1m.start_test_1m"))

        if course == "2° Medio":
            return redirect(url_for("test_2m.start_test_2m"))

        if course == "3° Medio":
            return redirect(url_for("test_3m.start_test_3m"))

        if course == "4° Medio":
            return redirect(url_for("test_4m.start_test_4m"))

        return redirect(url_for("home"))

    return render_template("student_form.html", courses=courses, test_types=test_types)
