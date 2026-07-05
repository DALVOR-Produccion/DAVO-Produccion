import json

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe
from services.publicidad import obtener_publicidad
from services.orientation_maps import obtener_continuidad_8


test_8_bp = Blueprint("test_8", __name__, url_prefix="/test8")


questions_8 = [
    (1, "Me interesa la ciencia o los experimentos", "Científica"),
    (2, "Me gusta investigar temas nuevos", "Científica"),
    (3, "Me interesa aprender sobre el cuerpo humano o la naturaleza", "Científica"),
    (4, "Me gusta resolver problemas complejos", "Científica"),
    (5, "Me interesa entender cómo funciona la tecnología", "Científica"),

    (6, "Me gusta leer libros o artículos", "Humanista"),
    (7, "Me interesa la historia o la actualidad", "Humanista"),
    (8, "Me gusta escribir mis ideas", "Humanista"),
    (9, "Me interesa debatir temas", "Humanista"),
    (10, "Me gusta comprender cómo funciona la sociedad", "Humanista"),

    (11, "Me gusta dibujar, pintar o crear", "Artística"),
    (12, "Me interesa la música o el arte", "Artística"),
    (13, "Me gusta expresarme de forma creativa", "Artística"),
    (14, "Me interesa participar en actividades artísticas", "Artística"),
    (15, "Me gusta imaginar cosas nuevas", "Artística"),

    (16, "Me gusta trabajar con herramientas", "Técnica"),
    (17, "Me interesa aprender un oficio", "Técnica"),
    (18, "Me gusta armar o construir cosas", "Técnica"),
    (19, "Prefiero aprender haciendo", "Técnica"),
    (20, "Me interesa cómo funcionan las máquinas o sistemas", "Técnica"),

    (21, "Me gusta ayudar a otras personas", "Social"),
    (22, "Me interesa trabajar con otras personas", "Social"),
    (23, "Me gusta trabajar en equipo", "Social"),
    (24, "Me interesa enseñar o explicar", "Social"),
    (25, "Me gusta escuchar y apoyar a los demás", "Social"),
]


def obtener_talleres(area):

    workshop_map = {
        "Científica": "Participar en talleres de ciencias, laboratorio, tecnología o investigación escolar.",
        "Humanista": "Participar en talleres de lectura, historia, escritura, debates o comunicación.",
        "Artística": "Participar en talleres de música, dibujo, teatro, danza o actividades creativas.",
        "Técnica": "Participar en talleres prácticos, computación, robótica, electricidad, mecánica o tecnología.",
        "Social": "Participar en actividades de liderazgo, convivencia escolar, apoyo comunitario o trabajo colaborativo."
    }

    return workshop_map.get(
        area,
        "Se recomienda participar en talleres y actividades complementarias."
    )


def obtener_resultados_basica(result):
    cursos_basica = ["6° Básico", "7° Básico", "8° Básico"]

    resultados = TestResult.query.filter(
        TestResult.student_rut == result.student_rut,
        TestResult.status == "activo",
        TestResult.course.in_(cursos_basica)
    ).order_by(
        TestResult.created_at.asc()
    ).all()

    return resultados


def formatear_linea_historial(resultado):
    fecha = resultado.created_at.strftime("%Y") if resultado.created_at else "Sin año"
    curso = resultado.course or "Sin curso"
    area = resultado.main_area or "Sin área"

    return f"{fecha} - {curso}: área principal {area}."


def obtener_clasificacion_trayectoria(resultados):
    areas = [
        r.main_area for r in resultados
        if r.main_area
    ]

    if not areas:
        return "sin_datos"

    areas_unicas = set(areas)

    if len(areas_unicas) == 1:
        return "estable"

    area_actual = areas[-1]
    apariciones_actual = areas.count(area_actual)

    if apariciones_actual >= 2:
        return "predominante_con_variaciones"

    return "exploracion_diversa"


def obtener_historial_8(result):

    resultados_basica = obtener_resultados_basica(result)

    historial_previo = [
        r for r in resultados_basica
        if r.id != result.id
    ]

    history_count = len(historial_previo)
    has_history = history_count > 0
    previous_result = historial_previo[-1] if has_history else None

    cursos_registrados = set([
        r.course for r in resultados_basica
        if r.course
    ])

    if {"6° Básico", "7° Básico", "8° Básico"}.issubset(cursos_registrados):
        history_type = "completo"
    elif has_history:
        history_type = "parcial"
    else:
        history_type = "sin_historial"

    lineas = [
        formatear_linea_historial(r)
        for r in resultados_basica
    ]

    encabezado = "Seguimiento de Enseñanza Básica:\n\n"

    if not has_history:
        follow_up_text = (
            encabezado
            + "No existen evaluaciones previas registradas para este estudiante "
            "en Enseñanza Básica.\n\n"
            "Las conclusiones y recomendaciones de este informe se basan principalmente "
            "en los resultados obtenidos en la presente evaluación de 8° Básico."
        )

    else:
        clasificacion = obtener_clasificacion_trayectoria(resultados_basica)

        if clasificacion == "estable":
            analisis = (
                f"Los resultados registrados durante la Enseñanza Básica muestran "
                f"una tendencia consistente hacia el área {result.main_area}. "
                "Esta estabilidad permite identificar intereses que se han mantenido "
                "durante el proceso de seguimiento."
            )

        elif clasificacion == "predominante_con_variaciones":
            analisis = (
                f"Los resultados muestran una trayectoria con variaciones, pero con "
                f"presencia reiterada del área {result.main_area}. "
                "Esto permite considerar la evaluación actual como una referencia "
                "importante para orientar la continuidad educativa."
            )

        else:
            areas_observadas = []
            for r in resultados_basica:
                if r.main_area and r.main_area not in areas_observadas:
                    areas_observadas.append(r.main_area)

            analisis = (
                "Los resultados muestran una exploración de intereses en distintas "
                f"áreas durante la Enseñanza Básica: {', '.join(areas_observadas)}. "
                "Esta diversidad es esperable en el proceso de desarrollo vocacional. "
                f"Para la decisión actual, la evaluación de 8° Básico muestra una mayor "
                f"afinidad hacia el área {result.main_area}, por lo que la recomendación "
                "de continuidad educativa debe considerar especialmente el resultado actual, "
                "sin desconocer los intereses observados anteriormente."
            )

        cierre = (
            "\n\nLa recomendación entregada en el presente informe constituye una "
            "orientación educativa basada en los resultados disponibles. La decisión "
            "final sobre la continuidad de estudios corresponde al estudiante y su familia, "
            "considerando además sus intereses personales, rendimiento académico, proyecto "
            "de vida y alternativas educativas disponibles."
        )

        follow_up_text = (
            encabezado
            + "\n".join(lineas)
            + "\n\n"
            + analisis
            + cierre
        )

    return historial_previo, has_history, previous_result, history_type, follow_up_text



def generar_respaldo_pdf_8(result):
    previous_results, has_history, previous_result, history_type, seguimiento = obtener_historial_8(result)

    continuidad = obtener_continuidad_8(
        result.main_area,
        result.secondary_area
    )

    areas_recomendadas = continuidad["areas"]
    areas_texto = ", ".join(areas_recomendadas)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 8° básico, "
        "etapa en la que el estudiante enfrenta una primera decisión relevante respecto de su continuidad "
        "en enseñanza media. A diferencia de 6° y 7° básico, donde el foco está puesto en la exploración "
        "temprana de intereses, en 8° básico el informe busca aportar antecedentes para orientar la elección "
        "entre continuidad Científico-Humanista, Técnico-Profesional u otras líneas complementarias de desarrollo."
    )

    interpretacion = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        f"La modalidad sugerida es {continuidad['modalidad']}."
    )

    orientacion = (
        f"{continuidad['texto']} "
        f"Áreas o líneas formativas sugeridas: {areas_texto}."
    )

    talleres = obtener_talleres(result.main_area)

    recomendacion = (
        "Se recomienda complementar esta orientación con conversación familiar, apoyo del establecimiento "
        "educacional, revisión de alternativas de enseñanza media y participación en talleres relacionados "
        "con el área detectada. La recomendación entregada en este informe constituye un apoyo para la "
        "toma de decisiones; la elección final corresponde al estudiante y su familia, considerando sus "
        "intereses personales, rendimiento académico, proyecto de vida y alternativas educativas disponibles."
    )

    try:
        generar_pdf_informe(
            result=result,
            titulo="Informe de Orientación Educacional - 8° Básico",
            introduccion=introduccion,
            interpretacion=interpretacion,
            recomendacion=recomendacion,
            seguimiento=seguimiento,
            talleres=talleres,
            orientacion=orientacion
        )
    except Exception as error:
        print(f"No se pudo generar respaldo PDF automático 8° Básico: {error}")


@test_8_bp.route("/start", methods=["GET", "POST"])
def start_test_8():

    if request.method == "POST":

        answers = {}

        scores = {
            "Científica": 0,
            "Humanista": 0,
            "Artística": 0,
            "Técnica": 0,
            "Social": 0
        }

        unanswered_questions = []

        for q_id, _, area in questions_8:

            answer = request.form.get(f"q_{q_id}")

            if answer not in ["si", "no"]:
                unanswered_questions.append(q_id)

            else:
                if answer == "si":
                    scores[area] += 1

            answers[q_id] = answer

        if unanswered_questions:
            flash("Debe responder todas las preguntas antes de finalizar el test.", "danger")
            return render_template("test_8.html", questions=questions_8)

        sorted_areas = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        main_area = sorted_areas[0][0]
        secondary_area = sorted_areas[1][0]

        continuidad = obtener_continuidad_8(main_area, secondary_area)

        suggested_path = continuidad["modalidad"]

        result = TestResult(
            student_rut=session.get("student_rut"),
            student_name=session.get("student_name"),
            school=session.get("school"),
            school_id=session.get("school_id"),
            student_type=session.get("student_type"),
            course=session.get("course"),
            section=session.get("section"),
            test_type="Test Básico",
            answers=json.dumps(answers),
            score_cientifica=scores["Científica"],
            score_humanista=scores["Humanista"],
            score_artistica=scores["Artística"],
            score_tecnica=scores["Técnica"],
            score_social=scores["Social"],
            main_area=main_area,
            secondary_area=secondary_area,
            suggested_path=suggested_path
        )

        db.session.add(result)
        db.session.commit()

        generar_respaldo_pdf_8(result)

        return redirect(url_for("test_8.view_report_8", result_id=result.id))

    return render_template("test_8.html", questions=questions_8)


@test_8_bp.route("/report/<int:result_id>")
def view_report_8(result_id):

    result = TestResult.query.get_or_404(result_id)

    previous_results, has_history, previous_result, history_type, follow_up_text = obtener_historial_8(result)

    report_type = "seguimiento_final_8" if has_history else "inicial_8"

    continuidad = obtener_continuidad_8(
        result.main_area,
        result.secondary_area
    )

    areas_recomendadas = continuidad["areas"]
    areas_texto = ", ".join(areas_recomendadas)

    interpretation = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una inclinación secundaria hacia el área {result.secondary_area}. "
        f"Considerando sus respuestas, la modalidad sugerida para la continuidad "
        f"de estudios en enseñanza media es: {continuidad['modalidad']}."
    )

    path_guidance = (
        f"{continuidad['texto']} "
        f"Áreas o líneas formativas sugeridas: {areas_texto}."
    )

    workshop_text = obtener_talleres(result.main_area)

    publicidad = obtener_publicidad(result.course)

    return render_template(
        "report_8.html",
        result=result,
        interpretation=interpretation,
        report_type=report_type,
        has_history=has_history,
        previous_result=previous_result,
        follow_up_text=follow_up_text,
        publicidad=publicidad,
        path_guidance=path_guidance,
        workshop_text=workshop_text,
        history_type=history_type,
        areas_recomendadas=areas_recomendadas
    )


@test_8_bp.route("/report/<int:result_id>/pdf")
def download_report_8_pdf(result_id):

    result = TestResult.query.get_or_404(result_id)

    previous_results, has_history, previous_result, history_type, seguimiento = obtener_historial_8(result)

    continuidad = obtener_continuidad_8(
        result.main_area,
        result.secondary_area
    )

    areas_recomendadas = continuidad["areas"]
    areas_texto = ", ".join(areas_recomendadas)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 8° básico, "
        "etapa en la que el estudiante enfrenta una primera decisión relevante respecto de su continuidad "
        "en enseñanza media. A diferencia de 6° y 7° básico, donde el foco está puesto en la exploración "
        "temprana de intereses, en 8° básico el informe busca aportar antecedentes para orientar la elección "
        "entre continuidad Científico-Humanista, Técnico-Profesional u otras líneas complementarias de desarrollo."
    )

    interpretacion = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        f"La modalidad sugerida es {continuidad['modalidad']}."
    )

    orientacion = (
        f"{continuidad['texto']} "
        f"Áreas o líneas formativas sugeridas: {areas_texto}."
    )

    talleres = obtener_talleres(result.main_area)

    recomendacion = (
        "Se recomienda complementar esta orientación con conversación familiar, apoyo del establecimiento "
        "educacional, revisión de alternativas de enseñanza media y participación en talleres relacionados "
        "con el área detectada. La recomendación entregada en este informe constituye un apoyo para la "
        "toma de decisiones; la elección final corresponde al estudiante y su familia, considerando sus "
        "intereses personales, rendimiento académico, proyecto de vida y alternativas educativas disponibles."
    )

    ruta_pdf = generar_pdf_informe(
        result=result,
        titulo="Informe de Orientación Educacional - 8° Básico",
        introduccion=introduccion,
        interpretacion=interpretacion,
        recomendacion=recomendacion,
        seguimiento=seguimiento,
        talleres=talleres,
        orientacion=orientacion
    )

    return send_file(
        ruta_pdf,
        as_attachment=True
    )
