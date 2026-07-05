import os
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, send_file

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from sqlalchemy import case

from models import db
from models.test_result import TestResult


talleres_bp = Blueprint(
    "talleres",
    __name__,
    url_prefix="/talleres"
)


def acceso_permitido():

    if session.get("admin_logged"):
        return True

    if session.get("colegio_logged"):
        return True

    return False


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


def obtener_secciones_disponibles(query_base):

    secciones = (
        query_base
        .with_entities(TestResult.section)
        .filter(TestResult.section.isnot(None))
        .filter(TestResult.section != "")
        .distinct()
        .all()
    )

    return sorted(
        [s[0] for s in secciones if s[0]],
        key=lambda x: (x == "SIN PARALELO", x)
    )


def curso_orden_valor_talleres(curso):
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


def obtener_registros_vigentes_talleres(selected_school=""):
    """
    Para talleres se consideran solo alumnos vigentes:
    - registros activos
    - último registro activo por RUT
    - último registro del año actual
    - si se indica colegio, el último registro debe pertenecer a ese colegio
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


def filtrar_registros_talleres(
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
            curso_orden_valor_talleres(r.course),
            r.section or "",
            r.student_name or ""
        )
    )

    return resultados


def obtener_secciones_desde_registros_talleres(registros, selected_course=""):
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


def determinar_nivel_por_curso(course, level):

    if level:
        return level

    if course in ["6° Básico", "7° Básico", "8° Básico"]:
        return "basica"

    if course in ["1° Medio", "2° Medio", "3° Medio", "4° Medio"]:
        return "media"

    return ""


def obtener_info_taller(area, level, course, total_estudiantes):

    nivel = determinar_nivel_por_curso(course, level)

    if not area:
        return {
            "mostrar": False,
            "nombre": "Seleccione un área para generar una propuesta de taller.",
            "etapa": "",
            "objetivo": "",
            "enfoque": "",
            "actividades": [],
            "recomendacion": ""
        }

    etapa = "Nivel general"

    if nivel == "basica":
        etapa = "Enseñanza Básica"

    if nivel == "media":
        etapa = "Enseñanza Media"

    if course:
        etapa = course

    info_base = {
        "Científica": {
            "nombre": "Taller de Exploración Científica",
            "objetivo": "Fortalecer la curiosidad, el pensamiento lógico, la observación y la resolución de problemas mediante experiencias científicas aplicadas.",
            "actividades": [
                "experimentos guiados",
                "proyectos de investigación escolar",
                "desafíos de pensamiento lógico",
                "observación del entorno y registro de hallazgos"
            ]
        },
        "Humanista": {
            "nombre": "Taller de Comunicación, Debate y Pensamiento Crítico",
            "objetivo": "Desarrollar habilidades de expresión oral y escrita, argumentación, comprensión social y reflexión crítica.",
            "actividades": [
                "debates guiados",
                "lectura y análisis de casos",
                "escritura de opiniones",
                "presentaciones orales"
            ]
        },
        "Artística": {
            "nombre": "Taller de Expresión Artística y Creatividad",
            "objetivo": "Promover la creatividad, la expresión personal, la sensibilidad estética y la exploración de lenguajes artísticos.",
            "actividades": [
                "creación visual",
                "expresión corporal o musical",
                "diseño de proyectos artísticos",
                "muestras o exposiciones escolares"
            ]
        },
        "Técnica": {
            "nombre": "Taller de Exploración Técnica y Tecnología Aplicada",
            "objetivo": "Favorecer habilidades prácticas, pensamiento aplicado, resolución técnica de problemas y exploración de áreas técnico-profesionales.",
            "actividades": [
                "proyectos prácticos",
                "uso básico de herramientas o tecnología",
                "robótica o computación inicial",
                "simulación de especialidades técnico-profesionales"
            ]
        },
        "Social": {
            "nombre": "Taller de Liderazgo, Convivencia y Participación",
            "objetivo": "Fortalecer habilidades sociales, liderazgo positivo, trabajo colaborativo, participación estudiantil y compromiso comunitario.",
            "actividades": [
                "dinámicas colaborativas",
                "proyectos de servicio escolar",
                "mediación y resolución de conflictos",
                "liderazgo y participación estudiantil"
            ]
        }
    }

    info = info_base.get(area, info_base["Social"]).copy()

    if nivel == "basica":
        info["enfoque"] = (
            "En básica, el taller debe orientarse a la exploración gradual de intereses, "
            "sin cerrar decisiones vocacionales definitivas. La prioridad es observar habilidades, "
            "motivar la participación y entregar experiencias variadas."
        )

    elif nivel == "media":
        info["enfoque"] = (
            "En enseñanza media, el taller debe orientarse a la consolidación de intereses, "
            "la toma de decisiones informada y la vinculación con trayectorias educativas, técnicas, "
            "profesionales o laborales."
        )

    else:
        info["enfoque"] = (
            "Se recomienda definir primero si el grupo corresponde a enseñanza básica o media, "
            "para evitar mezclar estudiantes con necesidades vocacionales distintas."
        )

    if course == "8° Básico":
        info["nombre"] = f"{info['nombre']} para Decisión de Continuidad Educativa"
        info["recomendacion"] = (
            "8° básico es una etapa clave porque el estudiante comienza a proyectar su continuidad "
            "en enseñanza media. Se recomienda complementar el taller con entrevista de orientación, "
            "información sobre alternativas Científico-Humanistas y Técnico-Profesionales, y una reunión "
            "informativa con apoderados."
        )

    elif course == "4° Medio":
        info["nombre"] = f"{info['nombre']} para Decisión Postsecundaria"
        info["recomendacion"] = (
            "4° medio es una etapa crítica de decisión postsecundaria. Se recomienda complementar el taller "
            "con orientación sobre educación superior, CFT, IP, universidades, empleabilidad, becas, PAES, "
            "proyecto de vida y alternativas laborales o técnico-profesionales."
        )

    elif course in ["6° Básico", "7° Básico"]:
        info["recomendacion"] = (
            "En 6° y 7° básico se recomienda trabajar desde la exploración, la motivación y el descubrimiento "
            "de intereses, evitando conclusiones definitivas sobre el futuro educativo del estudiante."
        )

    elif course in ["1° Medio", "2° Medio", "3° Medio"]:
        info["recomendacion"] = (
            "En 1° a 3° medio se recomienda usar el taller para consolidar intereses, observar consistencia "
            "vocacional y preparar decisiones futuras de especialidad, continuidad de estudios o proyecto personal."
        )

    else:
        info["recomendacion"] = (
            "Si el grupo contiene distintos cursos, se recomienda separar las nóminas por nivel y curso antes de "
            "ejecutar el taller, especialmente evitando mezclar básica con media."
        )

    info["mostrar"] = True
    info["area"] = area
    info["etapa"] = etapa
    info["total_estudiantes"] = total_estudiantes

    return info


def aplicar_filtros_talleres():

    selected_school = request.args.get("school", "").strip()
    selected_level = request.args.get("level", "").strip()
    selected_course = request.args.get("course", "").strip()
    selected_section = request.args.get("section", "").strip()
    selected_area = request.args.get("area", "").strip()

    school_name_filter = ""

    if session.get("colegio_logged"):
        school_name_filter = session.get("colegio_school_name", "")

    if session.get("admin_logged") and not session.get("colegio_logged") and selected_school:
        school_name_filter = selected_school

    registros_vigentes = obtener_registros_vigentes_talleres(school_name_filter)

    results = filtrar_registros_talleres(
        registros_vigentes,
        selected_level=selected_level,
        selected_course=selected_course,
        selected_section=selected_section,
        selected_area=selected_area
    )

    filtros = {
        "school": selected_school,
        "level": selected_level,
        "course": selected_course,
        "section": selected_section,
        "area": selected_area,
        "registros_vigentes": registros_vigentes
    }

    return results, filtros


@talleres_bp.route("/")
def index():

    if not acceso_permitido():
        return redirect(url_for("home"))

    results, filtros = aplicar_filtros_talleres()

    areas = [
        "Científica",
        "Humanista",
        "Artística",
        "Técnica",
        "Social"
    ]

    courses = [
        "6° Básico",
        "7° Básico",
        "8° Básico",
        "1° Medio",
        "2° Medio",
        "3° Medio",
        "4° Medio"
    ]

    colegios = []

    if session.get("admin_logged") and not session.get("colegio_logged"):
        colegios = obtener_colegios()

    sections = obtener_secciones_desde_registros_talleres(
        filtros["registros_vigentes"],
        selected_course=filtros["course"]
    )

    taller_info = obtener_info_taller(
        filtros["area"],
        filtros["level"],
        filtros["course"],
        len(results)
    )

    return render_template(
        "talleres/index.html",
        results=results,
        areas=areas,
        courses=courses,
        colegios=colegios,
        sections=sections,
        taller_info=taller_info,
        selected_school=filtros["school"],
        selected_level=filtros["level"],
        selected_course=filtros["course"],
        selected_section=filtros["section"],
        selected_area=filtros["area"]
    )


@talleres_bp.route("/pdf")
def descargar_pdf():

    if not acceso_permitido():
        return redirect(url_for("home"))

    results, filtros = aplicar_filtros_talleres()

    taller_info = obtener_info_taller(
        filtros["area"],
        filtros["level"],
        filtros["course"],
        len(results)
    )

    os.makedirs("exports/talleres", exist_ok=True)

    fecha = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    nombre_partes = ["nomina_taller"]

    if session.get("colegio_logged"):
        nombre_partes.append(session.get("colegio_school_name", "colegio"))
    elif session.get("admin_logged") and filtros["school"]:
        nombre_partes.append(filtros["school"])
    else:
        nombre_partes.append("todos_los_colegios")

    for clave in ["level", "course", "section", "area"]:
        if filtros[clave]:
            nombre_partes.append(filtros[clave])

    nombre_archivo = "_".join(nombre_partes)
    nombre_archivo = (
        nombre_archivo
        .replace(" ", "_")
        .replace("°", "")
        .replace("/", "_")
    )

    pdf_path = f"exports/talleres/{nombre_archivo}_{fecha}.pdf"

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

    titulo = "Nómina sugerida para talleres"

    if filtros["area"]:
        titulo += f" - Área {filtros['area']}"

    elements.append(Paragraph(titulo, styles["Title"]))
    elements.append(Spacer(1, 10))

    if session.get("colegio_logged"):
        colegio = session.get("colegio_school_name", "Colegio")
        elements.append(Paragraph(f"<b>Establecimiento:</b> {colegio}", styles["Normal"]))
    elif filtros["school"]:
        elements.append(Paragraph(f"<b>Establecimiento:</b> {filtros['school']}", styles["Normal"]))
    else:
        elements.append(Paragraph("<b>Vista:</b> Administrador general - todos los colegios", styles["Normal"]))

    filtros_aplicados = []

    if filtros["level"] == "basica":
        filtros_aplicados.append("Nivel: Enseñanza Básica")

    if filtros["level"] == "media":
        filtros_aplicados.append("Nivel: Enseñanza Media")

    if filtros["course"]:
        filtros_aplicados.append(f"Curso: {filtros['course']}")

    if filtros["section"]:
        filtros_aplicados.append(f"Paralelo: {filtros['section']}")

    if filtros["area"]:
        filtros_aplicados.append(f"Área: {filtros['area']}")

    if filtros_aplicados:
        elements.append(Paragraph("<b>Filtros aplicados:</b> " + " | ".join(filtros_aplicados), styles["Normal"]))

    elements.append(Paragraph(f"<b>Fecha de emisión:</b> {datetime.now().strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    if taller_info["mostrar"]:
        elements.append(Paragraph("1. Propuesta pedagógica del taller", styles["Heading2"]))
        elements.append(Paragraph(f"<b>Nombre sugerido:</b> {taller_info['nombre']}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Área:</b> {taller_info['area']}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Etapa educativa:</b> {taller_info['etapa']}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Participantes sugeridos:</b> {taller_info['total_estudiantes']}", styles["Normal"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Objetivo:</b> {taller_info['objetivo']}", styles["Normal"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Enfoque pedagógico:</b> {taller_info['enfoque']}", styles["Normal"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("<b>Actividades sugeridas:</b>", styles["Normal"]))

        for actividad in taller_info["actividades"]:
            elements.append(Paragraph(f"• {actividad}", styles["Normal"]))

        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Recomendación:</b> {taller_info['recomendacion']}", styles["Normal"]))
        elements.append(Spacer(1, 12))

    else:
        elements.append(Paragraph(
            "Seleccione un área específica para generar una propuesta pedagógica de taller.",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("2. Nómina de estudiantes sugeridos", styles["Heading2"]))

    data = [
        [
            "Alumno",
            "RUT",
            "Colegio",
            "Curso",
            "Área principal",
            "Área secundaria",
            "Fecha"
        ]
    ]

    for r in results:

        curso = r.course or ""

        if r.section and r.section != "SIN PARALELO":
            curso = f"{curso} {r.section}"

        data.append([
            r.student_name or "",
            r.student_rut or "",
            r.school or "",
            curso,
            r.main_area or "",
            r.secondary_area or "",
            r.created_at.strftime("%d-%m-%Y") if r.created_at else ""
        ])

    if len(data) == 1:
        elements.append(Paragraph("No existen estudiantes para la selección realizada.", styles["Normal"]))
    else:
        table = Table(
            data,
            repeatRows=1,
            colWidths=[90, 65, 100, 55, 65, 65, 55]
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)

    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        "Esta nómina es una sugerencia generada a partir del área principal detectada en el test. "
        "Debe ser revisada por el equipo de orientación antes de definir la participación final de los estudiantes.",
        styles["Normal"]
    ))

    doc.build(elements)

    return send_file(pdf_path, as_attachment=True)
