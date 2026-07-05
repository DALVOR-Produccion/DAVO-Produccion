import json

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult

from services.pdf_generator import generar_pdf_informe
from services.publicidad import obtener_publicidad


test_1m_bp = Blueprint("test_1m", __name__, url_prefix="/test1m")


questions_1m = [
    (1, "Me interesa profundizar en temas científicos", "Científica"),
    (2, "Me gusta analizar información con mayor detalle", "Científica"),
    (3, "Me interesa aprender contenidos más complejos", "Científica"),
    (4, "Me gusta investigar por mi cuenta", "Científica"),
    (5, "Me interesa comprender fenómenos naturales", "Científica"),

    (6, "Me interesa comprender la sociedad actual", "Humanista"),
    (7, "Me gusta reflexionar sobre temas sociales", "Humanista"),
    (8, "Me interesa debatir ideas", "Humanista"),
    (9, "Me gusta escribir o argumentar", "Humanista"),
    (10, "Me interesa entender el comportamiento humano", "Humanista"),

    (11, "Me interesa desarrollar habilidades creativas", "Artística"),
    (12, "Me gusta expresarme a través del arte", "Artística"),
    (13, "Me interesa participar en actividades artísticas", "Artística"),
    (14, "Me gusta crear ideas nuevas", "Artística"),
    (15, "Me interesa explorar distintas formas de expresión", "Artística"),

    (16, "Me interesa aprender haciendo", "Técnica"),
    (17, "Me gusta resolver problemas prácticos", "Técnica"),
    (18, "Me interesa trabajar con herramientas o tecnología", "Técnica"),
    (19, "Me gustaría desarrollar habilidades técnicas", "Técnica"),
    (20, "Me interesa aprender cosas aplicadas", "Técnica"),

    (21, "Me interesa trabajar con personas", "Social"),
    (22, "Me gusta ayudar a otros", "Social"),
    (23, "Me interesa enseñar o explicar", "Social"),
    (24, "Me gusta participar en actividades grupales", "Social"),
    (25, "Me interesa comprender y apoyar a otros", "Social"),
]



def obtener_antecedente_octavo(result):
    antecedente = TestResult.query.filter(
        TestResult.student_rut == result.student_rut,
        TestResult.id != result.id,
        TestResult.status == "activo",
        TestResult.course == "8° Básico"
    ).order_by(
        TestResult.created_at.desc()
    ).first()

    return antecedente


def normalizar_modalidad(texto):
    texto = (texto or "").strip().lower()

    if "cient" in texto or "human" in texto or texto == "ch":
        return "CH"

    if "técnico" in texto or "tecnico" in texto or "profesional" in texto or texto == "tp":
        return "TP"

    return "OTRO"


def obtener_analisis_transicion(result):
    antecedente_octavo = obtener_antecedente_octavo(result)

    if not antecedente_octavo:
        return (
            "Antecedentes de transición desde Enseñanza Básica:\n\n"
            "No existen antecedentes activos registrados de orientación al finalizar la Enseñanza Básica.\n\n"
            "Esta evaluación constituye el primer antecedente disponible para el seguimiento de Enseñanza Media."
        )

    modalidad_octavo = antecedente_octavo.suggested_path or "No registrada"
    modalidad_actual = result.education_type or "No registrada"

    modalidad_octavo_norm = normalizar_modalidad(modalidad_octavo)
    modalidad_actual_norm = normalizar_modalidad(modalidad_actual)

    fecha_octavo = antecedente_octavo.created_at.strftime("%Y") if antecedente_octavo.created_at else "Sin año"

    if modalidad_octavo_norm == modalidad_actual_norm and modalidad_actual_norm in ["CH", "TP"]:
        return (
            "Antecedentes de transición desde Enseñanza Básica:\n\n"
            f"En 8° Básico ({fecha_octavo}) se sugirió una trayectoria asociada a {modalidad_octavo}.\n\n"
            f"Actualmente el estudiante se encuentra cursando una modalidad {modalidad_actual}.\n\n"
            "La elección realizada resulta coherente con la orientación entregada al finalizar la Enseñanza Básica. "
            "Esta información debe entenderse como un antecedente de transición y no como una comparación directa entre ciclos."
        )

    return (
        "Antecedentes de transición desde Enseñanza Básica:\n\n"
        f"En 8° Básico ({fecha_octavo}) se sugirió una trayectoria asociada a {modalidad_octavo}.\n\n"
        f"Actualmente el estudiante se encuentra cursando una modalidad {modalidad_actual}.\n\n"
        "Esta diferencia refleja que el estudiante y su familia han considerado diversos factores "
        "al momento de definir su continuidad educativa. La Enseñanza Media corresponde a un nuevo "
        "ciclo de seguimiento, donde la información actual permitirá observar progresivamente cómo "
        "se relacionan los intereses actuales con la modalidad cursada y el proyecto educativo del estudiante."
    )


def obtener_contexto_modalidad(result):
    if result.education_type == "Científico-Humanista":
        if result.suggested_path == "Científico-Humanista":
            return "La modalidad actual Científico-Humanista es coherente con los intereses predominantes observados en esta evaluación."

        if result.suggested_path == "Técnico Profesional":
            return (
                "El estudiante se encuentra en una modalidad Científico-Humanista, pero sus respuestas muestran una inclinación hacia áreas técnico-prácticas. "
                "Se recomienda observar esta situación y reforzar espacios de aprendizaje aplicado."
            )

        return (
            "El estudiante se encuentra en una modalidad Científico-Humanista, pero presenta intereses que podrían complementarse con talleres, actividades extracurriculares o espacios de exploración vocacional."
        )

    if result.education_type == "Técnico Profesional":
        if result.suggested_path == "Técnico Profesional":
            return (
                f"La modalidad actual Técnico Profesional es coherente con los intereses actuales del estudiante. "
                f"El área declarada del establecimiento es: {result.tp_area}."
            )

        if result.suggested_path == "Científico-Humanista":
            return (
                "El estudiante se encuentra en una modalidad Técnico Profesional, pero sus respuestas muestran una inclinación hacia áreas más académicas o de formación general. "
                "Se recomienda acompañar este proceso sin desincentivar la continuidad escolar, fortaleciendo los apoyos y espacios complementarios que permitan integrar sus intereses actuales."
            )

        return (
            "El estudiante se encuentra en una modalidad Técnico Profesional, pero presenta intereses complementarios que podrían requerir espacios de desarrollo artístico, social o exploratorio."
        )

    return (
        "El estudiante declara no estar seguro de su modalidad actual o de su orientación educativa. "
        "Se recomienda mantener seguimiento y apoyar la exploración de intereses durante el año escolar."
    )


def generar_respaldo_pdf_1m(result):
    introduccion = (
        "Este informe corresponde a una evaluación de ajuste vocacional aplicada en 1° medio. "
        "Su objetivo es observar los intereses actuales del estudiante al inicio de la Enseñanza Media, "
        "considerando que este nivel marca el comienzo de un nuevo ciclo educativo."
    )

    interpretacion = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        "Estos resultados permiten iniciar el seguimiento de Enseñanza Media y no constituyen una definición definitiva."
    )

    orientacion = (
        obtener_analisis_transicion(result)
        + "\n\n"
        + "Análisis de modalidad actual:\n\n"
        + obtener_contexto_modalidad(result)
    )

    recomendacion = (
        "Se recomienda continuar explorando sus intereses durante 1° medio y participar en actividades académicas, "
        "prácticas, artísticas o sociales que permitan fortalecer su trayectoria educativa. "
        "Esta evaluación debe ser utilizada como primer antecedente del seguimiento de Enseñanza Media."
    )

    try:
        generar_pdf_informe(
            result=result,
            titulo="Informe de Orientación Educacional - 1° Medio",
            introduccion=introduccion,
            interpretacion=interpretacion,
            recomendacion=recomendacion,
            orientacion=orientacion
        )
    except Exception as error:
        print(f"No se pudo generar respaldo PDF automático 1° Medio: {error}")


@test_1m_bp.route("/start", methods=["GET", "POST"])
def start_test_1m():

    education_types = [
        "Científico-Humanista",
        "Técnico Profesional",
        "No está seguro"
    ]

    tp_areas = [
        "Industrial",
        "Comercial",
        "Servicios",
        "Otro",
        "No sabe"
    ]

    if request.method == "POST":

        education_type = request.form.get("education_type", "").strip()
        tp_area = request.form.get("tp_area", "").strip()

        if not education_type:
            flash("Debe seleccionar el tipo de enseñanza actual.", "danger")
            return render_template(
                "test_1m.html",
                questions=questions_1m,
                education_types=education_types,
                tp_areas=tp_areas
            )

        if education_type == "Técnico Profesional" and not tp_area:
            flash("Debe seleccionar el área técnico profesional.", "danger")
            return render_template(
                "test_1m.html",
                questions=questions_1m,
                education_types=education_types,
                tp_areas=tp_areas
            )

        answers = {}
        scores = {
            "Científica": 0,
            "Humanista": 0,
            "Artística": 0,
            "Técnica": 0,
            "Social": 0
        }

        unanswered_questions = []

        for q_id, _, area in questions_1m:
            answer = request.form.get(f"q_{q_id}")

            if answer not in ["si", "no"]:
                unanswered_questions.append(q_id)
            else:
                if answer == "si":
                    scores[area] += 1

            answers[q_id] = answer

        if unanswered_questions:
            flash("Debe responder todas las preguntas antes de finalizar el test.", "danger")
            return render_template(
                "test_1m.html",
                questions=questions_1m,
                education_types=education_types,
                tp_areas=tp_areas
            )

        sorted_areas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        main_area = sorted_areas[0][0]
        secondary_area = sorted_areas[1][0]

        if main_area == "Técnica":
            suggested_path = "Técnico Profesional"
        elif main_area in ["Científica", "Humanista"]:
            suggested_path = "Científico-Humanista"
        elif main_area == "Artística":
            suggested_path = "Artístico / Complementario"
        else:
            if secondary_area == "Técnica":
                suggested_path = "Técnico Profesional"
            elif secondary_area in ["Científica", "Humanista"]:
                suggested_path = "Científico-Humanista"
            elif secondary_area == "Artística":
                suggested_path = "Artístico / Complementario"
            else:
                suggested_path = "Mixto / en observación"

        result = TestResult(
            student_rut=session.get("student_rut"),
            student_name=session.get("student_name"),
            school=session.get("school"),
            school_id=session.get("school_id"),
            student_type=session.get("student_type"),
            course=session.get("course"),
            section=session.get("section"),
            test_type="Test Básico",
            education_type=education_type,
            tp_area=tp_area if education_type == "Técnico Profesional" else None,
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

        generar_respaldo_pdf_1m(result)

        return redirect(url_for("test_1m.view_report_1m", result_id=result.id))

    return render_template(
        "test_1m.html",
        questions=questions_1m,
        education_types=education_types,
        tp_areas=tp_areas
    )


@test_1m_bp.route("/report/<int:result_id>")
def view_report_1m(result_id):

    result = TestResult.query.get_or_404(result_id)

    # 1° Medio inicia un nuevo ciclo de seguimiento.
    # No se compara directamente con Enseñanza Básica.
    previous_results = []
    has_history = False
    previous_result = None

    transition_analysis = obtener_analisis_transicion(result)

    interpretation = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una inclinación secundaria hacia el área {result.secondary_area}. "
        "Estos resultados permiten identificar los intereses predominantes observados "
        "al inicio de la Enseñanza Media y constituyen el primer antecedente para "
        "el seguimiento de este ciclo educativo. "
        "La información obtenida no representa una definición vocacional definitiva, "
        "sino una referencia para orientar futuras evaluaciones y procesos de acompañamiento."
    )

    context_analysis = (
        transition_analysis
        + "\n\n"
        + "Análisis de modalidad actual:\n\n"
        + obtener_contexto_modalidad(result)
    )

    follow_up_text = (
        "Esta evaluación constituye el primer registro del estudiante dentro del proceso "
        "de seguimiento de Enseñanza Media. Las comparaciones de continuidad, ajuste o "
        "cambio de intereses se realizarán progresivamente desde 2° Medio, cuando exista "
        "un antecedente propio de este ciclo educativo."
    )

    # 🔥 PUBLICIDAD / INSTITUCIONES COLABORADORAS
    publicidad = obtener_publicidad(result.course)
    return render_template(
        "report_1m.html",
        result=result,
        interpretation=interpretation,
        context_analysis=context_analysis,
        has_history=has_history,
        previous_result=previous_result,        
        follow_up_text=follow_up_text,
        publicidad=publicidad
    )

@test_1m_bp.route("/report/<int:result_id>/pdf")
def download_report_1m_pdf(result_id):

    result = TestResult.query.get_or_404(result_id)

    introduccion = (
        "Este informe corresponde a una evaluación de ajuste vocacional aplicada en 1° medio. "
        "Su objetivo es observar los intereses actuales del estudiante al inicio de la Enseñanza Media, "
        "considerando que este nivel marca el comienzo de un nuevo ciclo educativo."
    )

    interpretacion = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        "Estos resultados permiten iniciar el seguimiento de Enseñanza Media y no constituyen una definición definitiva."
    )

    orientacion = (
        obtener_analisis_transicion(result)
        + "\n\n"
        + "Análisis de modalidad actual:\n\n"
        + obtener_contexto_modalidad(result)
    )

    recomendacion = (
        "Se recomienda continuar explorando sus intereses durante 1° medio y participar en actividades académicas, "
        "prácticas, artísticas o sociales que permitan fortalecer su trayectoria educativa. "
        "Esta evaluación debe ser utilizada como primer antecedente del seguimiento de Enseñanza Media."
    )

    ruta_pdf = generar_pdf_informe(
        result=result,
        titulo="Informe de Orientación Educacional - 1° Medio",
        introduccion=introduccion,
        interpretacion=interpretacion,
        recomendacion=recomendacion,
        orientacion=orientacion
    )

    return send_file(ruta_pdf, as_attachment=True)
