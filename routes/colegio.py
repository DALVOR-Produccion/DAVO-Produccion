from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from models import db
from models.test_result import TestResult
from models.institutional_user import InstitutionalUser
from sqlalchemy import case
from services.institutional_excel import crear_excel_institucional
from services.institutional_course_exports import crear_excel_curso, crear_pdf_curso
from services.institutional_statistics import (
    calcular_dashboard_institucional,
    calcular_ficha_curso,
    nivel_del_curso,
)
import re


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


def obtener_registros_dashboard(school_id, anio, incluir_archivados, nivel):
    consulta = TestResult.query.filter(TestResult.school_id == school_id)

    if anio is not None:
        inicio = datetime(anio, 1, 1)
        termino = datetime(anio + 1, 1, 1)
        consulta = consulta.filter(
            TestResult.created_at >= inicio,
            TestResult.created_at < termino,
        )

    if not incluir_archivados:
        consulta = consulta.filter(TestResult.status == "activo")

    resultados = consulta.order_by(TestResult.created_at.asc()).all()

    if nivel in {"basica", "media"}:
        resultados = [
            resultado for resultado in resultados
            if nivel_del_curso(resultado.course) == nivel
        ]

    return resultados


@colegio_bp.route("/estadisticas")
def estadisticas():
    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    school_id = session.get("colegio_school_id")
    current_year = datetime.now().year
    anios = obtener_anios_disponibles_colegio(school_id)
    seleccion_anio = request.args.get("anio", str(current_year))
    nivel = request.args.get("nivel", "todos")
    estado = request.args.get("estado", "activos")

    if nivel not in {"todos", "basica", "media"}:
        nivel = "todos"
    if estado not in {"activos", "todos"}:
        estado = "activos"

    if seleccion_anio == "historico":
        anio = None
        periodo_texto = "Histórico completo"
    else:
        try:
            anio = int(seleccion_anio)
        except ValueError:
            anio = current_year
            seleccion_anio = str(current_year)
        periodo_texto = f"Año {anio}"

    resultados = obtener_registros_dashboard(
        school_id=school_id,
        anio=anio,
        incluir_archivados=estado == "todos",
        nivel=nivel,
    )
    datos = calcular_dashboard_institucional(resultados)

    return render_template(
        "colegio/estadisticas.html",
        school_name=session.get("colegio_school_name"),
        current_year=current_year,
        anios=anios,
        seleccion_anio=seleccion_anio,
        periodo_texto=periodo_texto,
        nivel=nivel,
        estado=estado,
        datos=datos,
    )


@colegio_bp.route("/estadisticas/curso")
def estadisticas_curso():
    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    cursos_validos = {
        "6° Básico", "7° Básico", "8° Básico",
        "1° Medio", "2° Medio", "3° Medio", "4° Medio",
    }
    school_id = session.get("colegio_school_id")
    current_year = datetime.now().year
    curso = request.args.get("curso", "").strip()
    paralelo = request.args.get("paralelo", "SIN PARALELO").strip() or "SIN PARALELO"
    seleccion_anio = request.args.get("anio", str(current_year))
    nivel = request.args.get("nivel", "todos")
    estado = request.args.get("estado", "activos")

    if curso not in cursos_validos:
        flash("Seleccione un curso válido.", "warning")
        return redirect(url_for("colegio.estadisticas"))
    if nivel not in {"todos", "basica", "media"}:
        nivel = "todos"
    if estado not in {"activos", "todos"}:
        estado = "activos"

    if seleccion_anio == "historico":
        anio = None
        periodo_texto = "Histórico completo"
    else:
        try:
            anio = int(seleccion_anio)
        except ValueError:
            anio = current_year
            seleccion_anio = str(current_year)
        periodo_texto = f"Año {anio}"

    resultados = obtener_registros_dashboard(
        school_id=school_id,
        anio=anio,
        incluir_archivados=estado == "todos",
        nivel="todos",
    )
    resultados = [
        resultado for resultado in resultados
        if resultado.course == curso
        and (resultado.section or "SIN PARALELO") == paralelo
    ]

    if not resultados:
        flash("No existen resultados para el curso y los filtros seleccionados.", "warning")
        return redirect(url_for(
            "colegio.estadisticas",
            anio=seleccion_anio,
            nivel=nivel,
            estado=estado,
        ))

    datos = calcular_ficha_curso(resultados)
    curso_completo = curso if paralelo == "SIN PARALELO" else f"{curso} {paralelo}"

    return render_template(
        "colegio/estadisticas_curso.html",
        school_name=session.get("colegio_school_name"),
        curso=curso,
        paralelo=paralelo,
        curso_completo=curso_completo,
        periodo_texto=periodo_texto,
        seleccion_anio=seleccion_anio,
        nivel=nivel,
        estado=estado,
        datos=datos,
    )


def _datos_exportacion_curso():
    cursos_validos = {
        "6° Básico", "7° Básico", "8° Básico",
        "1° Medio", "2° Medio", "3° Medio", "4° Medio",
    }
    school_id = session.get("colegio_school_id")
    current_year = datetime.now().year
    curso = request.args.get("curso", "").strip()
    paralelo = request.args.get("paralelo", "SIN PARALELO").strip() or "SIN PARALELO"
    seleccion_anio = request.args.get("anio", str(current_year))
    estado = request.args.get("estado", "activos")

    if curso not in cursos_validos:
        return None
    if estado not in {"activos", "todos"}:
        estado = "activos"

    if seleccion_anio == "historico":
        anio = None
        periodo_texto = "Histórico completo"
    else:
        try:
            anio = int(seleccion_anio)
        except ValueError:
            return None
        periodo_texto = f"Año {anio}"

    resultados = obtener_registros_dashboard(
        school_id=school_id,
        anio=anio,
        incluir_archivados=estado == "todos",
        nivel="todos",
    )
    resultados = [
        resultado for resultado in resultados
        if resultado.course == curso
        and (resultado.section or "SIN PARALELO") == paralelo
    ]
    if not resultados:
        return None

    curso_completo = curso if paralelo == "SIN PARALELO" else f"{curso} {paralelo}"
    return resultados, calcular_ficha_curso(resultados), curso, paralelo, curso_completo, periodo_texto


@colegio_bp.route("/estadisticas/curso/excel")
def estadisticas_curso_excel():
    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    exportacion = _datos_exportacion_curso()
    if exportacion is None:
        flash("No existen resultados para generar el Excel del curso.", "warning")
        return redirect(url_for("colegio.estadisticas"))

    resultados, datos, curso, paralelo, curso_completo, periodo_texto = exportacion
    school_name = session.get("colegio_school_name") or "Colegio"
    archivo = crear_excel_curso(
        resultados, datos, school_name, curso_completo, periodo_texto
    )
    nombre_base = re.sub(r"[^A-Za-z0-9_-]+", "_", curso_completo).strip("_") or "Curso"
    periodo_archivo = request.args.get("anio", str(datetime.now().year))
    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"Estadisticas_{nombre_base}_{periodo_archivo}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@colegio_bp.route("/estadisticas/curso/pdf")
def estadisticas_curso_pdf():
    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    exportacion = _datos_exportacion_curso()
    if exportacion is None:
        flash("No existen resultados para generar el PDF del curso.", "warning")
        return redirect(url_for("colegio.estadisticas"))

    resultados, datos, curso, paralelo, curso_completo, periodo_texto = exportacion
    school_name = session.get("colegio_school_name") or "Colegio"
    archivo = crear_pdf_curso(datos, school_name, curso_completo, periodo_texto)
    nombre_base = re.sub(r"[^A-Za-z0-9_-]+", "_", curso_completo).strip("_") or "Curso"
    periodo_archivo = request.args.get("anio", str(datetime.now().year))
    return send_file(
        archivo,
        as_attachment=True,
        download_name=f"Ficha_{nombre_base}_{periodo_archivo}.pdf",
        mimetype="application/pdf",
    )


def obtener_anios_disponibles_colegio(school_id):
    fechas = (
        TestResult.query
        .with_entities(TestResult.created_at)
        .filter(
            TestResult.school_id == school_id,
            TestResult.created_at.isnot(None)
        )
        .all()
    )
    return sorted({fecha.year for (fecha,) in fechas}, reverse=True)


def obtener_registros_exportacion(school_id, anio=None):
    consulta = TestResult.query.filter(TestResult.school_id == school_id)

    if anio is not None:
        inicio = datetime(anio, 1, 1)
        termino = datetime(anio + 1, 1, 1)
        consulta = consulta.filter(
            TestResult.created_at >= inicio,
            TestResult.created_at < termino
        )

    return consulta.order_by(
        TestResult.created_at.asc(),
        TestResult.student_name.asc()
    ).all()


@colegio_bp.route("/exportar", methods=["GET", "POST"])
def exportar():
    if not colegio_login_required():
        return redirect(url_for("colegio.login"))

    school_id = session.get("colegio_school_id")
    school_name = session.get("colegio_school_name") or "Colegio"
    current_year = datetime.now().year
    anios = obtener_anios_disponibles_colegio(school_id)

    if current_year not in anios:
        anios.insert(0, current_year)

    if request.method == "GET":
        return render_template(
            "colegio/exportar.html",
            school_name=school_name,
            current_year=current_year,
            anios=anios
        )

    periodo = request.form.get("periodo", "actual")
    anio = None

    if periodo == "actual":
        anio = current_year
        periodo_texto = f"Año {anio}"
    elif periodo == "especifico":
        try:
            anio = int(request.form.get("anio", ""))
        except ValueError:
            flash("Seleccione un año válido.", "danger")
            return redirect(url_for("colegio.exportar"))

        if anio not in anios:
            flash("El año seleccionado no está disponible.", "danger")
            return redirect(url_for("colegio.exportar"))
        periodo_texto = f"Año {anio}"
    elif periodo == "historico":
        periodo_texto = "Histórico completo"
    else:
        flash("Seleccione un periodo válido.", "danger")
        return redirect(url_for("colegio.exportar"))

    results = obtener_registros_exportacion(school_id, anio)

    if not results:
        flash("No existen evaluaciones para el periodo seleccionado.", "warning")
        return redirect(url_for("colegio.exportar"))

    archivo = crear_excel_institucional(results, school_name, periodo_texto)
    nombre_colegio = (
        re.sub(r"[^A-Za-z0-9_-]+", "_", school_name).strip("_")
        or "Colegio"
    )
    periodo_archivo = "Historico" if anio is None else str(anio)
    nombre_archivo = f"Resultados_{nombre_colegio}_{periodo_archivo}.xlsx"

    return send_file(
        archivo,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@colegio_bp.route("/logout")
def logout():

    session.pop("colegio_logged", None)
    session.pop("colegio_user_id", None)
    session.pop("colegio_full_name", None)
    session.pop("colegio_school_id", None)
    session.pop("colegio_school_name", None)

    return redirect(url_for("home"))
