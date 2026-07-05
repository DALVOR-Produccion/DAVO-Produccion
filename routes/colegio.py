from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models import db
from models.test_result import TestResult
from models.institutional_user import InstitutionalUser
from sqlalchemy import case


colegio_bp = Blueprint("colegio", __name__, url_prefix="/colegio")


def colegio_login_required():
    return session.get("colegio_logged") is True


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


def obtener_registros_vigentes_colegio(school_id):
    """
    Panel colegio:
    - usa solo registros activos
    - considera el último registro activo por RUT
    - exige que el último registro sea del año actual
    - exige que el último registro pertenezca al colegio conectado

    Así el panel operativo no cuenta historial de años anteriores,
    egresados ni alumnos que se hayan cambiado de colegio.
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

        if registro.school_id != school_id:
            continue

        vigentes.append(registro)

    vigentes = sorted(
        vigentes,
        key=lambda r: (
            curso_orden_valor(r.course),
            r.section or "",
            r.student_name or ""
        )
    )

    return vigentes


def obtener_resumen_cursos_desde_registros(results):
    resumen = {}

    for r in results:
        curso = r.course or "Sin curso"
        resumen[curso] = resumen.get(curso, 0) + 1

    return sorted(
        resumen.items(),
        key=lambda item: curso_orden_valor(item[0])
    )


def obtener_resumen_areas_desde_registros(results):
    resumen = {}

    for r in results:
        area = r.main_area or "Sin área"
        resumen[area] = resumen.get(area, 0) + 1

    return sorted(
        resumen.items(),
        key=lambda item: item[0]
    )


def calcular_estadisticas_colegio(results):
    areas_base = ["Científica", "Humanista", "Artística", "Técnica", "Social"]

    por_curso_paralelo = {}

    for r in results:
        curso = r.course or "Sin curso"
        section = r.section or "SIN PARALELO"
        area = r.main_area or "Sin área"

        if section != "SIN PARALELO":
            curso_paralelo = f"{curso} {section}"
        else:
            curso_paralelo = curso

        if curso_paralelo not in por_curso_paralelo:
            por_curso_paralelo[curso_paralelo] = {
                "total": 0,
                "areas": {a: 0 for a in areas_base}
            }

        por_curso_paralelo[curso_paralelo]["total"] += 1

        if area in por_curso_paralelo[curso_paralelo]["areas"]:
            por_curso_paralelo[curso_paralelo]["areas"][area] += 1

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

    por_curso_paralelo = ordenar_diccionario_por_curso_paralelo(
        por_curso_paralelo
    )

    porcentaje_por_curso_paralelo = ordenar_diccionario_por_curso_paralelo(
        porcentaje_por_curso_paralelo
    )

    return por_curso_paralelo, porcentaje_por_curso_paralelo


@colegio_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = InstitutionalUser.query.filter_by(
            username=username,
            is_active=True
        ).first()

        if user and user.check_password(password):

            session.clear()
            
            session["colegio_logged"] = True
            session["colegio_user_id"] = user.id
            session["colegio_full_name"] = user.full_name
            session["colegio_school_id"] = user.school_id
            session["colegio_school_name"] = user.school_name

            user.last_login = datetime.utcnow()
            db.session.commit()

            return redirect(url_for("colegio.dashboard"))

        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("colegio/login.html")


@colegio_bp.route("/dashboard")
def dashboard():

    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    school_id = session.get("colegio_school_id")

    results = obtener_registros_vigentes_colegio(school_id)

    total = len(results)

    cursos = obtener_resumen_cursos_desde_registros(results)

    areas = obtener_resumen_areas_desde_registros(results)

    por_curso_paralelo, porcentaje_por_curso_paralelo = calcular_estadisticas_colegio(results)

    return render_template(
        "colegio/dashboard.html",
        school_name=session.get("colegio_school_name"),
        full_name=session.get("colegio_full_name"),
        total=total,
        cursos=cursos,
        areas=areas,
        por_curso_paralelo=por_curso_paralelo,
        porcentaje_por_curso_paralelo=porcentaje_por_curso_paralelo
    )


@colegio_bp.route("/alumnos")
def alumnos():

    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    school_id = session.get("colegio_school_id")

    results = obtener_registros_vigentes_colegio(school_id)

    return render_template(
        "colegio/alumnos.html",
        results=results,
        school_name=session.get("colegio_school_name")
    )


@colegio_bp.route("/logout")
def logout():

    session.pop("colegio_logged", None)
    session.pop("colegio_user_id", None)
    session.pop("colegio_full_name", None)
    session.pop("colegio_school_id", None)
    session.pop("colegio_school_name", None)

    return redirect(url_for("home"))