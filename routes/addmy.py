from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from models.student import Student
from models.school import School
from models.institutional_user import InstitutionalUser

from datetime import datetime

import pandas as pd
import os
import re

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def limpiar_nombre_archivo(texto):
    if not texto:
        return "general"

    texto = texto.strip().lower()
    texto = texto.replace(" ", "_")
    texto = re.sub(r"[^a-zA-Z0-9_áéíóúñÁÉÍÓÚÑ-]", "", texto)

    return texto


def obtener_colegios():
    colegios = (
        db.session.query(TestResult.school)
        .filter(TestResult.status == "activo")
        .filter(TestResult.school.isnot(None))
        .filter(TestResult.school != "")
        .distinct()
        .order_by(TestResult.school.asc())
        .all()
    )

    return [c[0] for c in colegios]


def calcular_estadisticas(results):
    total_registros = len(results)

    areas_base = ["Científica", "Humanista", "Artística", "Técnica", "Social"]

    por_curso = {}
    por_curso_paralelo = {}
    por_area = {}
    por_ruta = {}
    por_ensenanza = {}

    cursos_basica_temprana = ["6° Básico", "7° Básico"]
    cursos_octavo = ["8° Básico"]
    cursos_media = ["1° Medio", "2° Medio", "3° Medio", "4° Medio"]

    tiene_basica_temprana = False
    tiene_octavo = False
    tiene_media = False

    for r in results:
        curso = r.course or "Sin curso"
        section = r.section or "SIN PARALELO"
        area = r.main_area or "Sin área"
        ruta = r.suggested_path or "Sin ruta"
        ensenanza = r.education_type or "No registrada"

        if section != "SIN PARALELO":
            curso_paralelo = f"{curso} {section}"
        else:
            curso_paralelo = curso

        por_curso[curso] = por_curso.get(curso, 0) + 1
        por_area[area] = por_area.get(area, 0) + 1
        por_ruta[ruta] = por_ruta.get(ruta, 0) + 1
        por_ensenanza[ensenanza] = por_ensenanza.get(ensenanza, 0) + 1

        if curso_paralelo not in por_curso_paralelo:
            por_curso_paralelo[curso_paralelo] = {
                "total": 0,
                "areas": {a: 0 for a in areas_base}
            }

        por_curso_paralelo[curso_paralelo]["total"] += 1

        if area in por_curso_paralelo[curso_paralelo]["areas"]:
            por_curso_paralelo[curso_paralelo]["areas"][area] += 1

        if curso in cursos_basica_temprana:
            tiene_basica_temprana = True

        if curso in cursos_octavo:
            tiene_octavo = True

        if curso in cursos_media:
            tiene_media = True

    porcentaje_area = {}

    if total_registros > 0:
        for area, cantidad in por_area.items():
            porcentaje_area[area] = round((cantidad / total_registros) * 100, 1)

    porcentaje_por_curso_paralelo = {}

    for curso_paralelo, datos in por_curso_paralelo.items():
        total = datos["total"]
        porcentaje_por_curso_paralelo[curso_paralelo] = {}

        for area in areas_base:
            cantidad = datos["areas"].get(area, 0)
            porcentaje = round((cantidad / total) * 100, 1) if total > 0 else 0

            porcentaje_por_curso_paralelo[curso_paralelo][area] = {
                "cantidad": cantidad,
                "porcentaje": porcentaje
            }

    area_predominante = max(por_area, key=por_area.get) if por_area else "Sin datos"
    ruta_predominante = max(por_ruta, key=por_ruta.get) if por_ruta else "Sin datos"

    recomendaciones = []

    if tiene_basica_temprana:
        recomendaciones.append(
            "Para 6° y 7° básico, se recomienda fortalecer talleres exploratorios que permitan observar intereses tempranos sin definir aún una trayectoria educativa definitiva."
        )

    if tiene_octavo:
        recomendaciones.append(
            "Para 8° básico, se recomienda reforzar el proceso de orientación para la elección de continuidad en enseñanza media, considerando opciones Científico-Humanistas, Técnico-Profesionales o complementarias según el perfil observado."
        )

    if tiene_media:
        recomendaciones.append(
            "Para enseñanza media, se recomienda fortalecer acciones de orientación vocacional, continuidad de estudios, preparación PAES, exploración de educación superior y vinculación con instituciones técnicas o profesionales."
        )

    if porcentaje_area.get("Científica", 0) >= 35:
        recomendaciones.append(
            "Se observa una presencia importante del área científica. Se recomienda implementar talleres de ciencias, tecnología, investigación escolar, medioambiente y resolución de problemas."
        )

    if porcentaje_area.get("Técnica", 0) >= 35:
        if tiene_media:
            recomendaciones.append(
                "Se observa una presencia importante del área técnica. En enseñanza media, se recomienda fortalecer orientación TP, especialidades técnicas, vinculación con CFT/IP y talleres aplicados."
            )
        elif tiene_octavo:
            recomendaciones.append(
                "Se observa una presencia importante del área técnica. En 8° básico, se recomienda orientar la exploración hacia liceos Técnico-Profesionales y talleres prácticos, sin cerrar la decisión de manera definitiva."
            )
        else:
            recomendaciones.append(
                "Se observa una presencia importante del área técnica. En 6° y 7° básico, se recomienda promover talleres prácticos, tecnología, robótica, manualidades, computación y actividades de creación."
            )

    if porcentaje_area.get("Humanista", 0) >= 30:
        recomendaciones.append(
            "Se observa una presencia importante del área humanista. Se recomienda potenciar lectura, escritura, debate, historia, comunicación y actividades de reflexión social."
        )

    if porcentaje_area.get("Social", 0) >= 30:
        recomendaciones.append(
            "Se observa una presencia importante del área social. Se recomienda reforzar liderazgo, convivencia escolar, trabajo colaborativo, participación estudiantil y apoyo comunitario."
        )

    if porcentaje_area.get("Artística", 0) >= 25:
        recomendaciones.append(
            "Se observa una presencia importante del área artística. Se recomienda implementar talleres de creatividad, música, artes visuales, diseño, expresión corporal y actividades culturales."
        )

    if not recomendaciones:
        recomendaciones.append(
            "Se recomienda seguir acumulando información para definir talleres institucionales con mayor precisión."
        )

    return {
        "total_registros": total_registros,
        "por_curso": por_curso,
        "por_curso_paralelo": por_curso_paralelo,
        "porcentaje_por_curso_paralelo": porcentaje_por_curso_paralelo,
        "por_area": por_area,
        "por_ruta": por_ruta,
        "por_ensenanza": por_ensenanza,
        "porcentaje_area": porcentaje_area,
        "area_predominante": area_predominante,
        "ruta_predominante": ruta_predominante,
        "recomendaciones": recomendaciones
    }


@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin_orientacion" and password == "Orientacion2026*":
            session["admin_logged"] = True
            return redirect(url_for("admin.dashboard"))

        flash("Credenciales incorrectas", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/dashboard")
def dashboard():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    activos = TestResult.query.filter_by(status="activo").count()
    archivados = TestResult.query.filter_by(status="archivado").count()
    total_registros = activos + archivados

    return render_template(
        "admin/dashboard.html",
        total_registros=total_registros,
        activos=activos,
        archivados=archivados
    )


@admin_bp.route("/students")
def students():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    search = request.args.get("search", "").strip()
    course = request.args.get("course", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 50

    query = TestResult.query.filter_by(status="activo")

    if search:
        query = query.filter(
            db.or_(
                TestResult.student_name.ilike(f"%{search}%"),
                TestResult.student_rut.ilike(f"%{search}%"),
                TestResult.school.ilike(f"%{search}%")
            )
        )

    if course:
        query = query.filter(TestResult.course == course)

    pagination = query.order_by(
        TestResult.created_at.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    results = pagination.items

    seen_ruts = {}
    seen_names = {}

    for r in results:
        rut_key = (r.student_rut or "").strip().lower()
        name_key = (r.student_name or "").strip().lower()

        r.posible_duplicado = False

        if rut_key in seen_ruts:
            r.posible_duplicado = True
            seen_ruts[rut_key].posible_duplicado = True
        else:
            seen_ruts[rut_key] = r

        if name_key in seen_names:
            r.posible_duplicado = True
            seen_names[name_key].posible_duplicado = True
        else:
            seen_names[name_key] = r

    courses = [
        "6° Básico",
        "7° Básico",
        "8° Básico",
        "1° Medio",
        "2° Medio",
        "3° Medio",
        "4° Medio"
    ]

    return render_template(
        "admin/students.html",
        results=results,
        pagination=pagination,
        courses=courses,
        selected_course=course,
        search=search
    )


@admin_bp.route("/edit_student/<int:result_id>", methods=["GET", "POST"])
def edit_student(result_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    result = TestResult.query.get_or_404(result_id)

    student_record = Student.query.filter_by(
        student_rut=result.student_rut
    ).order_by(
        Student.created_at.desc()
    ).first()

    courses = [
        "6° Básico",
        "7° Básico",
        "8° Básico",
        "1° Medio",
        "2° Medio",
        "3° Medio",
        "4° Medio"
    ]

    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        student_email = request.form.get("student_email", "").strip()
        guardian_rut = request.form.get("guardian_rut", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_email = request.form.get("guardian_email", "").strip()

        student_type = request.form.get("student_type", "COLEGIO").strip()
        school_id_raw = request.form.get("school_id", "").strip()

        school_name = result.school
        school_id = result.school_id

        if not student_name:
            flash("El nombre del alumno no puede quedar vacío.", "warning")
            return render_template(
                "admin/edit_student.html",
                result=result,
                student_record=student_record,
                courses=courses
            )

        if student_type == "PARTICULAR":
            school_name = "ALUMNO PARTICULAR"
            school_id = None
        else:
            if school_id_raw:
                colegio = School.query.get(school_id_raw)

                if colegio:
                    school_name = colegio.name
                    school_id = colegio.id

        related_results = TestResult.query.filter_by(
            student_rut=result.student_rut
        ).all()

        for r in related_results:
            r.student_name = student_name
            r.school = school_name
            r.school_id = school_id
            r.student_type = student_type

        related_students = Student.query.filter_by(
            student_rut=result.student_rut
        ).all()

        for s in related_students:
            s.student_name = student_name
            s.school = school_name
            s.school_id = school_id
            s.student_type = student_type
            s.student_email = student_email
            s.guardian_rut = guardian_rut
            s.guardian_name = guardian_name
            s.guardian_email = guardian_email

        db.session.commit()

        flash("Datos administrativos actualizados correctamente.", "success")

        return redirect(url_for("admin.students"))

    return render_template(
        "admin/edit_student.html",
        result=result,
        student_record=student_record,
        courses=courses
    )


@admin_bp.route("/archive/<int:result_id>")
def archive_student(result_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    result = TestResult.query.get_or_404(result_id)
    result.status = "archivado"

    db.session.commit()

    flash("Registro archivado correctamente.", "success")

    return redirect(url_for("admin.students"))


@admin_bp.route("/archived")
def archived_students():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    results = TestResult.query.filter_by(
        status="archivado"
    ).order_by(
        TestResult.student_name.asc()
    ).all()

    return render_template(
        "admin/archived.html",
        results=results
    )


@admin_bp.route("/restore/<int:result_id>")
def restore_student(result_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    result = TestResult.query.get_or_404(result_id)
    result.status = "activo"

    db.session.commit()

    flash("Registro restaurado correctamente.", "success")

    return redirect(url_for("admin.archived_students"))


@admin_bp.route("/stats")
def stats():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    selected_school = request.args.get("school", "").strip()

    query = TestResult.query.filter_by(status="activo")

    if selected_school:
        query = query.filter(TestResult.school == selected_school)

    results = query.all()
    datos = calcular_estadisticas(results)
    colegios = obtener_colegios()

    return render_template(
        "admin/stats.html",
        total_registros=datos["total_registros"],
        por_curso=datos["por_curso"],
        por_curso_paralelo=datos["por_curso_paralelo"],
        porcentaje_por_curso_paralelo=datos["porcentaje_por_curso_paralelo"],
        por_area=datos["por_area"],
        por_ruta=datos["por_ruta"],
        por_ensenanza=datos["por_ensenanza"],
        porcentaje_area=datos["porcentaje_area"],
        area_predominante=datos["area_predominante"],
        ruta_predominante=datos["ruta_predominante"],
        recomendaciones=datos["recomendaciones"],
        colegios=colegios,
        selected_school=selected_school
    )


@admin_bp.route("/institutional_report")
def institutional_report():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    selected_school = request.args.get("school", "").strip()

    query = TestResult.query.filter_by(status="activo")

    if selected_school:
        query = query.filter(TestResult.school == selected_school)

    results = query.all()
    datos = calcular_estadisticas(results)

    os.makedirs("exports", exist_ok=True)

    if selected_school:
        nombre_pdf = limpiar_nombre_archivo(selected_school)
        pdf_path = f"exports/informe_institucional_{nombre_pdf}.pdf"
        titulo_contexto = f"Colegio: {selected_school}"
    else:
        pdf_path = "exports/informe_institucional_general.pdf"
        titulo_contexto = "Vista general de todos los colegios"

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Informe Institucional - Sistema Integral de Orientación Educacional", styles["Title"]))
    elements.append(Paragraph("Desarrollado por David Vargas Orellana", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(titulo_contexto, styles["Heading2"]))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("1. Resumen general", styles["Heading2"]))
    elements.append(Paragraph(f"Total de registros analizados: {datos['total_registros']}", styles["BodyText"]))
    elements.append(Paragraph(f"Área predominante general: {datos['area_predominante']}", styles["BodyText"]))
    elements.append(Paragraph(f"Ruta predominante: {datos['ruta_predominante']}", styles["BodyText"]))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("2. Registros por curso", styles["Heading2"]))

    tabla_curso = [["Curso", "Cantidad"]]

    for curso, cantidad in datos["por_curso"].items():
        tabla_curso.append([curso, cantidad])

    table = Table(tabla_curso, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("3. Áreas vocacionales predominantes", styles["Heading2"]))

    tabla_area = [["Área", "Cantidad", "Porcentaje"]]

    for area, cantidad in datos["por_area"].items():
        porcentaje = datos["porcentaje_area"].get(area, 0)
        tabla_area.append([area, cantidad, f"{porcentaje}%"])

    table = Table(tabla_area, hAlign="LEFT")
    table.set