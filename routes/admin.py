from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from io import BytesIO

from models import db
from models.test_result import TestResult
from models.student import Student
from models.school import School

from models.institutional_user import InstitutionalUser
from services.report_storage import obtener_informe_pdf
from datetime import datetime
from sqlalchemy import case

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


def obtener_orden_curso():
    return case(
        (TestResult.course == "6° Básico", 1),
        (TestResult.course == "7° Básico", 2),
        (TestResult.course == "8° Básico", 3),
        (TestResult.course == "1° Medio", 4),
        (TestResult.course == "2° Medio", 5),
        (TestResult.course == "3° Medio", 6),
        (TestResult.course == "4° Medio", 7),
        else_=99
    )


def curso_orden_valor(curso):
    orden = {
        "6° Básico": 1,
        "7° Básico": 2,
        "8° Básico": 3,
        "1° Medio": 4,
        "2° Medio": 5,
        "3° Medio": 6,
        "4° Medio": 7,
    }

    return orden.get(curso or "", 99)


def obtener_nombre_curso_paralelo(resultado):
    curso = resultado.course or "Sin curso"
    section = resultado.section or "SIN PARALELO"

    if section and section != "SIN PARALELO":
        return f"{curso} {section}"

    return curso


def obtener_nivel_curso(curso):
    if curso in ["6° Básico", "7° Básico", "8° Básico"]:
        return "basica"

    if curso in ["1° Medio", "2° Medio", "3° Medio", "4° Medio"]:
        return "media"

    return "otro"


def ordenar_diccionario_por_curso_paralelo(diccionario):
    def clave(item):
        curso_paralelo = item[0]

        curso = curso_paralelo
        section = ""

        cursos = [
            "6° Básico",
            "7° Básico",
            "8° Básico",
            "1° Medio",
            "2° Medio",
            "3° Medio",
            "4° Medio"
        ]

        for c in cursos:
            if curso_paralelo.startswith(c):
                curso = c
                section = curso_paralelo.replace(c, "").strip()
                break

        return (
            curso_orden_valor(curso),
            section or "SIN PARALELO",
            curso_paralelo
        )

    return dict(sorted(diccionario.items(), key=clave))


def obtener_secciones_disponibles(query_base):
    secciones = (
        query_base
        .with_entities(TestResult.section)
        .filter(TestResult.section.isnot(None))
        .filter(TestResult.section != "")
        .distinct()
        .all()
    )

    ordenadas = sorted(
        [s[0] for s in secciones if s[0]],
        key=lambda x: (x == "SIN PARALELO", x)
    )

    return ordenadas


def obtener_registros_vigentes_actuales(selected_school=""):
    """
    Devuelve solo alumnos vigentes para estadísticas/talleres:
    - registros activos
    - último registro activo por RUT
    - último registro del año actual
    - si se filtra por colegio, el último registro debe pertenecer a ese colegio
    """

    current_year = datetime.now().year

    registros = (
        TestResult.query
        .filter(TestResult.status == "activo")
        .order_by(
            TestResult.student_rut.asc(),
            TestResult.created_at.desc()
        )
        .all()
    )

    ultimos_por_rut = {}

    for registro in registros:
        rut = registro.student_rut

        if not rut:
            continue

        if rut not in ultimos_por_rut:
            ultimos_por_rut[rut] = registro

    vigentes = []

    for registro in ultimos_por_rut.values():
        if not registro.created_at:
            continue

        if registro.created_at.year != current_year:
            continue

        if selected_school and registro.school != selected_school:
            continue

        vigentes.append(registro)

    return vigentes


def aplicar_filtros_estadisticas(
    registros,
    selected_level="",
    selected_course="",
    selected_section="",
    selected_area=""
):
    resultados = registros

    if selected_level == "basica":
        resultados = [
            r for r in resultados
            if r.course in ["6° Básico", "7° Básico", "8° Básico"]
        ]

    if selected_level == "media":
        resultados = [
            r for r in resultados
            if r.course in ["1° Medio", "2° Medio", "3° Medio", "4° Medio"]
        ]

    if selected_course:
        resultados = [
            r for r in resultados
            if r.course == selected_course
        ]

    if selected_section:
        resultados = [
            r for r in resultados
            if r.section == selected_section
        ]

    if selected_area:
        resultados = [
            r for r in resultados
            if r.main_area == selected_area
        ]

    resultados = sorted(
        resultados,
        key=lambda r: (
            r.school or "",
            curso_orden_valor(r.course),
            r.section or "",
            r.student_name or ""
        )
    )

    return resultados


def obtener_secciones_disponibles_desde_registros(registros, selected_course=""):
    if selected_course:
        registros = [
            r for r in registros
            if r.course == selected_course
        ]

    secciones = sorted(
        set([
            r.section
            for r in registros
            if r.section
        ]),
        key=lambda x: (x == "SIN PARALELO", x)
    )

    return secciones




def calcular_estadisticas(results):
    total_registros = len(results)

    areas_base = ["Científica", "Humanista", "Artística", "Técnica", "Social"]

    por_curso = {}
    por_curso_paralelo = {}
    por_area = {}
    por_ruta = {}
    por_ensenanza = {}
    por_nivel = {
        "basica": 0,
        "media": 0,
        "otro": 0
    }
    por_colegio = {}

    for r in results:
        curso = r.course or "Sin curso"
        area = r.main_area or "Sin área"
        ruta = r.suggested_path or "Sin ruta"
        ensenanza = r.education_type or "No registrada"
        colegio = r.school or "Sin colegio"
        nivel = obtener_nivel_curso(curso)
        curso_paralelo = obtener_nombre_curso_paralelo(r)

        por_curso[curso] = por_curso.get(curso, 0) + 1
        por_area[area] = por_area.get(area, 0) + 1
        por_ruta[ruta] = por_ruta.get(ruta, 0) + 1
        por_ensenanza[ensenanza] = por_ensenanza.get(ensenanza, 0) + 1
        por_nivel[nivel] = por_nivel.get(nivel, 0) + 1

        if colegio not in por_colegio:
            por_colegio[colegio] = {
                "total": 0,
                "areas": {a: 0 for a in areas_base}
            }

        por_colegio[colegio]["total"] += 1

        if area in por_colegio[colegio]["areas"]:
            por_colegio[colegio]["areas"][area] += 1

        if curso_paralelo not in por_curso_paralelo:
            por_curso_paralelo[curso_paralelo] = {
                "total": 0,
                "areas": {a: 0 for a in areas_base}
            }

        por_curso_paralelo[curso_paralelo]["total"] += 1

        if area in por_curso_paralelo[curso_paralelo]["areas"]:
            por_curso_paralelo[curso_paralelo]["areas"][area] += 1

    por_curso = dict(
        sorted(
            por_curso.items(),
            key=lambda item: curso_orden_valor(item[0])
        )
    )

    por_curso_paralelo = ordenar_diccionario_por_curso_paralelo(
        por_curso_paralelo
    )

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

    porcentaje_por_colegio = {}

    for colegio, datos in sorted(por_colegio.items()):
        total = datos["total"]
        porcentaje_por_colegio[colegio] = {
            "total": total,
            "areas": {}
        }

        for area in areas_base:
            cantidad = datos["areas"].get(area, 0)
            porcentaje = round((cantidad / total) * 100, 1) if total > 0 else 0

            porcentaje_por_colegio[colegio]["areas"][area] = {
                "cantidad": cantidad,
                "porcentaje": porcentaje
            }

    area_predominante = max(por_area, key=por_area.get) if por_area else "Sin datos"
    ruta_predominante = max(por_ruta, key=por_ruta.get) if por_ruta else "Sin datos"

    recomendaciones = []

    if porcentaje_area.get("Científica", 0) >= 35:
        recomendaciones.append("Se observa una presencia importante del área científica. Se recomienda implementar talleres de ciencias, tecnología, investigación escolar, medioambiente y resolución de problemas.")

    if porcentaje_area.get("Técnica", 0) >= 35:
        recomendaciones.append("Se observa una presencia importante del área técnica. Se recomienda fortalecer talleres prácticos, tecnología, robótica, computación, oficios y orientación Técnico-Profesional según el nivel educativo.")

    if porcentaje_area.get("Humanista", 0) >= 30:
        recomendaciones.append("Se observa una presencia importante del área humanista. Se recomienda potenciar lectura, escritura, debate, historia, comunicación y reflexión social.")

    if porcentaje_area.get("Social", 0) >= 30:
        recomendaciones.append("Se observa una presencia importante del área social. Se recomienda reforzar liderazgo, convivencia escolar, trabajo colaborativo, participación estudiantil y apoyo comunitario.")

    if porcentaje_area.get("Artística", 0) >= 25:
        recomendaciones.append("Se observa una presencia importante del área artística. Se recomienda implementar talleres de creatividad, música, artes visuales, diseño, expresión corporal y actividades culturales.")

    if not recomendaciones:
        recomendaciones.append("Se recomienda seguir acumulando información para definir talleres institucionales con mayor precisión.")

    return {
        "total_registros": total_registros,
        "por_curso": por_curso,
        "por_curso_paralelo": por_curso_paralelo,
        "porcentaje_por_curso_paralelo": porcentaje_por_curso_paralelo,
        "por_colegio": por_colegio,
        "porcentaje_por_colegio": porcentaje_por_colegio,
        "por_nivel": por_nivel,
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
            
            session.clear()
            
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

    orden_curso = case(
        (TestResult.course == "6° Básico", 1),
        (TestResult.course == "7° Básico", 2),
        (TestResult.course == "8° Básico", 3),
        (TestResult.course == "1° Medio", 4),
        (TestResult.course == "2° Medio", 5),
        (TestResult.course == "3° Medio", 6),
        (TestResult.course == "4° Medio", 7),
        else_=99
    )

    if search:
        # Cuando se busca por RUT o nombre, se privilegia el orden histórico
        # para que el seguimiento aparezca en secuencia cronológica.
        pagination = query.order_by(
            TestResult.student_rut.asc(),
            TestResult.created_at.asc(),
            orden_curso,
            TestResult.section.asc(),
            TestResult.student_name.asc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
    else:
        pagination = query.order_by(
            TestResult.school.asc(),
            orden_curso,
            TestResult.section.asc(),
            TestResult.student_name.asc()
        ).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

    results = pagination.items

    # Un mismo RUT en distintos años corresponde a historial DAVO,
    # no a duplicado. Solo se marca como posible duplicado cuando
    # el mismo RUT aparece más de una vez en el mismo año y mismo test.
    seen_rut_year_test = {}
    seen_name_year_course = {}

    for r in results:

        rut_key = (r.student_rut or "").strip().lower()
        name_key = (r.student_name or "").strip().lower()
        year_key = r.created_at.strftime("%Y") if r.created_at else "sin_fecha"
        test_key = (r.test_type or "").strip().lower()
        course_key = (r.course or "").strip().lower()

        r.posible_duplicado = False

        rut_duplicate_key = (
            rut_key,
            year_key,
            test_key
        )

        name_duplicate_key = (
            name_key,
            year_key,
            course_key
        )

        if rut_key and rut_duplicate_key in seen_rut_year_test:
            r.posible_duplicado = True
            seen_rut_year_test[rut_duplicate_key].posible_duplicado = True
        else:
            seen_rut_year_test[rut_duplicate_key] = r

        if name_key and name_duplicate_key in seen_name_year_course:
            r.posible_duplicado = True
            seen_name_year_course[name_duplicate_key].posible_duplicado = True
        else:
            seen_name_year_course[name_duplicate_key] = r

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



@admin_bp.route("/view_report/<int:result_id>")
def view_report(result_id):
    """
    Muestra en el navegador el informe PDF permanente asociado
    a un resultado de test.

    No modifica ni regenera informes. Si todavía no existe un
    respaldo en PostgreSQL, vuelve al listado con un aviso.
    """

    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    result = TestResult.query.get_or_404(result_id)

    informe = obtener_informe_pdf(result.id)

    if informe is None or not informe.pdf_data:
        flash(
            "Este registro todavía no tiene un informe PDF almacenado. "
            "El informe quedará disponible después de que sea generado "
            "nuevamente desde el test.",
            "warning"
        )

        return redirect(url_for(
            "admin.students",
            search=result.student_rut
        ))

    nombre_archivo = (
        informe.filename
        or f"informe_davo_{result.id}.pdf"
    )

    return send_file(
        BytesIO(informe.pdf_data),
        mimetype=informe.mime_type or "application/pdf",
        download_name=nombre_archivo,
        as_attachment=False
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


@admin_bp.route("/edit_history/<int:result_id>", methods=["GET", "POST"])
def edit_history(result_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    result = TestResult.query.get_or_404(result_id)

    courses = [
        "6° Básico",
        "7° Básico",
        "8° Básico",
        "1° Medio",
        "2° Medio",
        "3° Medio",
        "4° Medio"
    ]

    sections = [
        "A",
        "B",
        "C",
        "D",
        "SIN PARALELO"
    ]

    schools = School.query.filter_by(
        active=True
    ).order_by(
        School.name.asc()
    ).all()

    if request.method == "POST":

        course = request.form.get("course", "").strip()
        section = request.form.get("section", "").strip()
        school_id_raw = request.form.get("school_id", "").strip()
        created_at_raw = request.form.get("created_at", "").strip()

        if not course:
            flash("Debe seleccionar un curso.", "warning")
            return render_template(
                "admin/edit_history.html",
                result=result,
                courses=courses,
                sections=sections,
                schools=schools
            )

        if not created_at_raw:
            flash("Debe indicar la fecha de aplicación.", "warning")
            return render_template(
                "admin/edit_history.html",
                result=result,
                courses=courses,
                sections=sections,
                schools=schools
            )

        try:
            nueva_fecha = datetime.strptime(created_at_raw, "%Y-%m-%d")
        except ValueError:
            flash("La fecha ingresada no tiene un formato válido.", "danger")
            return render_template(
                "admin/edit_history.html",
                result=result,
                courses=courses,
                sections=sections,
                schools=schools
            )

        colegio = None

        if school_id_raw:
            colegio = School.query.get(school_id_raw)

        if not colegio:
            flash("Debe seleccionar un colegio válido.", "warning")
            return render_template(
                "admin/edit_history.html",
                result=result,
                courses=courses,
                sections=sections,
                schools=schools
            )

        result.course = course
        result.section = section or "SIN PARALELO"
        result.school_id = colegio.id
        result.school = colegio.name
        result.created_at = nueva_fecha

        db.session.commit()

        flash("Historial DAVO actualizado correctamente.", "success")

        return redirect(url_for(
            "admin.students",
            search=result.student_rut
        ))

    return render_template(
        "admin/edit_history.html",
        result=result,
        courses=courses,
        sections=sections,
        schools=schools
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
    selected_level = request.args.get("level", "").strip()
    selected_course = request.args.get("course", "").strip()
    selected_section = request.args.get("section", "").strip()
    selected_area = request.args.get("area", "").strip()

    registros_vigentes = obtener_registros_vigentes_actuales(selected_school)

    results = aplicar_filtros_estadisticas(
        registros_vigentes,
        selected_level=selected_level,
        selected_course=selected_course,
        selected_section=selected_section,
        selected_area=selected_area
    )

    datos = calcular_estadisticas(results)
    colegios = obtener_colegios()

    cursos = [
        "6° Básico",
        "7° Básico",
        "8° Básico",
        "1° Medio",
        "2° Medio",
        "3° Medio",
        "4° Medio"
    ]

    areas = [
        "Científica",
        "Humanista",
        "Artística",
        "Técnica",
        "Social"
    ]

    secciones = obtener_secciones_disponibles_desde_registros(
        registros_vigentes,
        selected_course=selected_course
    )

    return render_template(
        "admin/stats.html",
        total_registros=datos["total_registros"],
        por_curso=datos["por_curso"],
        por_area=datos["por_area"],
        por_ruta=datos["por_ruta"],
        por_ensenanza=datos["por_ensenanza"],
        por_nivel=datos["por_nivel"],
        porcentaje_area=datos["porcentaje_area"],
        area_predominante=datos["area_predominante"],
        ruta_predominante=datos["ruta_predominante"],
        recomendaciones=datos["recomendaciones"],
        colegios=colegios,
        courses=cursos,
        sections=secciones,
        areas=areas,
        selected_school=selected_school,
        selected_level=selected_level,
        selected_course=selected_course,
        selected_section=selected_section,
        selected_area=selected_area,
        por_curso_paralelo=datos["por_curso_paralelo"],
        porcentaje_por_curso_paralelo=datos["porcentaje_por_curso_paralelo"],
        por_colegio=datos["por_colegio"],
        porcentaje_por_colegio=datos["porcentaje_por_colegio"],
    )


@admin_bp.route("/institutional_report")
def institutional_report():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    selected_school = request.args.get("school", "").strip()
    selected_level = request.args.get("level", "").strip()
    selected_course = request.args.get("course", "").strip()
    selected_section = request.args.get("section", "").strip()
    selected_area = request.args.get("area", "").strip()

    registros_vigentes = obtener_registros_vigentes_actuales(selected_school)

    results = aplicar_filtros_estadisticas(
        registros_vigentes,
        selected_level=selected_level,
        selected_course=selected_course,
        selected_section=selected_section,
        selected_area=selected_area
    )

    datos = calcular_estadisticas(results)

    os.makedirs("exports", exist_ok=True)

    nombre_base = selected_school if selected_school else "general"

    if selected_level:
        nombre_base += f"_{selected_level}"

    if selected_course:
        nombre_base += f"_{selected_course}"

    if selected_section:
        nombre_base += f"_{selected_section}"

    if selected_area:
        nombre_base += f"_{selected_area}"

    nombre_pdf = limpiar_nombre_archivo(nombre_base)
    pdf_path = f"exports/informe_institucional_{nombre_pdf}.pdf"

    filtros_aplicados = []

    if selected_school:
        filtros_aplicados.append(f"Colegio: {selected_school}")
    else:
        filtros_aplicados.append("Vista: todos los colegios")

    if selected_level == "basica":
        filtros_aplicados.append("Nivel: Enseñanza Básica")

    if selected_level == "media":
        filtros_aplicados.append("Nivel: Enseñanza Media")

    if selected_course:
        filtros_aplicados.append(f"Curso: {selected_course}")

    if selected_section:
        filtros_aplicados.append(f"Paralelo: {selected_section}")

    if selected_area:
        filtros_aplicados.append(f"Área: {selected_area}")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35
    )

    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph(
            "Informe Institucional DAVO",
            styles["Title"]
        )
    )

    elements.append(
        Paragraph(
            "Sistema Integral de Orientación Educacional",
            styles["Heading2"]
        )
    )

    elements.append(
        Paragraph(
            "Desarrollado por David Vargas Orellana",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"<b>Fecha de emisión:</b> {datetime.now().strftime('%d-%m-%Y')}",
            styles["Normal"]
        )
    )

    elements.append(
        Paragraph(
            "<b>Filtros aplicados:</b> " + " | ".join(filtros_aplicados),
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 16))

    elements.append(Paragraph("1. Resumen ejecutivo", styles["Heading2"]))

    resumen_data = [
        ["Indicador", "Resultado"],
        ["Total de registros analizados", datos["total_registros"]],
        ["Registros Enseñanza Básica", datos["por_nivel"].get("basica", 0)],
        ["Registros Enseñanza Media", datos["por_nivel"].get("media", 0)],
        ["Área predominante", datos["area_predominante"]],
        ["Ruta predominante", datos["ruta_predominante"]],
    ]

    resumen_table = Table(
        resumen_data,
        hAlign="LEFT",
        colWidths=[210, 260]
    )

    resumen_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(resumen_table)
    elements.append(Spacer(1, 14))

    if not selected_school and datos.get("porcentaje_por_colegio"):

        elements.append(Paragraph("2. Comparación general por colegio", styles["Heading2"]))

        tabla_colegios = [
            [
                "Colegio",
                "Total",
                "Científica",
                "Humanista",
                "Artística",
                "Técnica",
                "Social"
            ]
        ]

        for colegio, info in datos["porcentaje_por_colegio"].items():
            tabla_colegios.append([
                colegio,
                info["total"],
                f'{info["areas"]["Científica"]["cantidad"]} ({info["areas"]["Científica"]["porcentaje"]}%)',
                f'{info["areas"]["Humanista"]["cantidad"]} ({info["areas"]["Humanista"]["porcentaje"]}%)',
                f'{info["areas"]["Artística"]["cantidad"]} ({info["areas"]["Artística"]["porcentaje"]}%)',
                f'{info["areas"]["Técnica"]["cantidad"]} ({info["areas"]["Técnica"]["porcentaje"]}%)',
                f'{info["areas"]["Social"]["cantidad"]} ({info["areas"]["Social"]["porcentaje"]}%)',
            ])

        table = Table(
            tabla_colegios,
            hAlign="LEFT",
            repeatRows=1,
            colWidths=[130, 40, 70, 70, 70, 70, 70]
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 14))

        numero_seccion_cursos = "3"

    else:

        numero_seccion_cursos = "2"

    elements.append(
        Paragraph(
            f"{numero_seccion_cursos}. Distribución por curso y paralelo",
            styles["Heading2"]
        )
    )

    tabla_curso_paralelo = [
        [
            "Curso / Paralelo",
            "Total",
            "Científica",
            "Humanista",
            "Artística",
            "Técnica",
            "Social"
        ]
    ]

    for curso_paralelo, info in datos["porcentaje_por_curso_paralelo"].items():
        tabla_curso_paralelo.append([
            curso_paralelo,
            datos["por_curso_paralelo"][curso_paralelo]["total"],
            f'{info["Científica"]["cantidad"]} ({info["Científica"]["porcentaje"]}%)',
            f'{info["Humanista"]["cantidad"]} ({info["Humanista"]["porcentaje"]}%)',
            f'{info["Artística"]["cantidad"]} ({info["Artística"]["porcentaje"]}%)',
            f'{info["Técnica"]["cantidad"]} ({info["Técnica"]["porcentaje"]}%)',
            f'{info["Social"]["cantidad"]} ({info["Social"]["porcentaje"]}%)',
        ])

    table = Table(
        tabla_curso_paralelo,
        hAlign="LEFT",
        repeatRows=1,
        colWidths=[95, 40, 75, 75, 75, 75, 75]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("4. Áreas vocacionales predominantes", styles["Heading2"]))

    tabla_area = [["Área", "Cantidad", "Porcentaje"]]

    for area, cantidad in datos["por_area"].items():
        porcentaje = datos["porcentaje_area"].get(area, 0)
        tabla_area.append([area, cantidad, f"{porcentaje}%"])

    table = Table(
        tabla_area,
        hAlign="LEFT",
        colWidths=[190, 90, 90]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("5. Rutas sugeridas", styles["Heading2"]))

    tabla_ruta = [["Ruta", "Cantidad"]]

    for ruta, cantidad in datos["por_ruta"].items():
        tabla_ruta.append([ruta, cantidad])

    table = Table(
        tabla_ruta,
        hAlign="LEFT",
        colWidths=[300, 80]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("6. Tipo de enseñanza registrada", styles["Heading2"]))

    tabla_ensenanza = [["Tipo de enseñanza", "Cantidad"]]

    for ensenanza, cantidad in datos["por_ensenanza"].items():
        tabla_ensenanza.append([ensenanza, cantidad])

    table = Table(
        tabla_ensenanza,
        hAlign="LEFT",
        colWidths=[300, 80]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("7. Recomendaciones institucionales", styles["Heading2"]))

    for recomendacion in datos["recomendaciones"]:
        elements.append(Paragraph(f"• {recomendacion}", styles["BodyText"]))
        elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 14))

    elements.append(Paragraph("8. Uso institucional sugerido", styles["Heading2"]))

    elements.append(Paragraph(
        "La información contenida en este informe puede ser utilizada para planificar talleres, "
        "comparar cursos y paralelos, observar diferencias entre enseñanza básica y media, "
        "apoyar acciones de orientación y fortalecer la toma de decisiones educativas. "
        "En 8° básico y 4° medio se recomienda complementar estos resultados con entrevistas, "
        "seguimiento individual y acciones específicas de orientación vocacional.",
        styles["BodyText"]
    ))

    doc.build(elements)

    return send_file(pdf_path, as_attachment=True)


@admin_bp.route("/export_excel")
def export_excel():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    selected_school = request.args.get("school", "").strip()

    query = TestResult.query.filter_by(status="activo")

    if selected_school:
        query = query.filter(TestResult.school == selected_school)

    results = query.order_by(TestResult.student_name.asc()).all()

    data = []

    for r in results:
        data.append({
            "Alumno": r.student_name,
            "RUT": r.student_rut,
            "Colegio": r.school,
            "Curso": r.course,
            "Fecha": r.created_at.strftime('%d-%m-%Y'),
            "Área Principal": r.main_area,
            "Área Secundaria": r.secondary_area,
            "Ruta Sugerida": r.suggested_path,
            "Tipo Enseñanza": r.education_type
        })

    df = pd.DataFrame(data)

    os.makedirs("exports", exist_ok=True)

    if selected_school:
        nombre_excel = limpiar_nombre_archivo(selected_school)
        file_path = f"exports/alumnos_{nombre_excel}.xlsx"
    else:
        file_path = "exports/alumnos_orientacion_educacional_general.xlsx"

    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


@admin_bp.route("/backup_database")
def backup_database():
    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    db_path = "database.db"

    return send_file(db_path, as_attachment=True)

@admin_bp.route("/institutional_users")
def institutional_users():

    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    users = InstitutionalUser.query.order_by(
        InstitutionalUser.school_name.asc(),
        InstitutionalUser.full_name.asc()
    ).all()

    return render_template(
        "admin/institutional_users.html",
        users=users
    )


@admin_bp.route("/institutional_users/new", methods=["GET", "POST"])
def new_institutional_user():

    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    if request.method == "POST":

        rut = request.form.get("rut", "").strip()
        full_name = request.form.get("full_name", "").strip()
        cargo = request.form.get("cargo", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        school_id_raw = request.form.get("school_id", "").strip()

        max_students = request.form.get("max_students", 500)

        if not school_id_raw:
            flash("Debe seleccionar un colegio.", "warning")
            return redirect(url_for("admin.new_institutional_user"))

        existing_user = InstitutionalUser.query.filter(
            db.or_(
                InstitutionalUser.username == username,
                InstitutionalUser.rut == rut
            )
        ).first()

        if existing_user:
            flash("Ya existe un usuario con ese RUT o nombre de usuario.", "danger")
            return redirect(url_for("admin.new_institutional_user"))

        colegio = School.query.get(school_id_raw)

        if not colegio:
            flash("Colegio no encontrado.", "danger")
            return redirect(url_for("admin.new_institutional_user"))

        user = InstitutionalUser(
            rut=rut,
            full_name=full_name,
            cargo=cargo,
            email=email,
            phone=phone,
            username=username,
            school_id=colegio.id,
            school_name=colegio.name,
            max_students=max_students,
            created_at=datetime.utcnow()
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Usuario institucional creado correctamente.", "success")

        return redirect(url_for("admin.institutional_users"))

    return render_template(
        "admin/new_institutional_user.html"
    )


@admin_bp.route("/institutional_users/toggle/<int:user_id>")
def toggle_institutional_user(user_id):

    if not session.get("admin_logged"):
        return redirect(url_for("admin.admin_login"))

    user = InstitutionalUser.query.get_or_404(user_id)

    user.is_active = not user.is_active

    db.session.commit()

    flash("Estado del usuario actualizado.", "success")

    return redirect(url_for("admin.institutional_users"))


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged", None)

    return redirect(url_for("home"))
