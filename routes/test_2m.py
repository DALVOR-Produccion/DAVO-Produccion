import json

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe
from services.publicidad import obtener_publicidad


test_2m_bp = Blueprint("test_2m", __name__, url_prefix="/test2m")


questions_2m = [
    (1, "Me interesa estudiar carreras relacionadas con ciencias", "Científica"),
    (2, "Me gusta analizar problemas complejos", "Científica"),
    (3, "Me interesa profundizar en biología, química o física", "Científica"),
    (4, "Me gusta investigar temas por mi cuenta", "Científica"),
    (5, "Me interesa comprender fenómenos naturales", "Científica"),
    (6, "Me gustaría seguir estudiando después del colegio", "Científica"),

    (7, "Me interesa comprender la sociedad", "Humanista"),
    (8, "Me gusta analizar temas sociales o históricos", "Humanista"),
    (9, "Me interesa debatir ideas", "Humanista"),
    (10, "Me gusta expresar mis ideas por escrito", "Humanista"),
    (11, "Me interesa comprender el comportamiento humano", "Humanista"),
    (12, "Me gustaría estudiar carreras relacionadas con personas", "Humanista"),

    (13, "Me interesa desarrollar habilidades creativas", "Artística"),
    (14, "Me gusta expresarme a través del arte", "Artística"),
    (15, "Me interesa participar en actividades artísticas", "Artística"),
    (16, "Me gusta crear ideas nuevas", "Artística"),
    (17, "Me interesa explorar distintas formas de expresión", "Artística"),

    (18, "Me interesa aprender haciendo", "Técnica"),
    (19, "Me gusta resolver problemas prácticos", "Técnica"),
    (20, "Me interesa trabajar con herramientas o tecnología", "Técnica"),
    (21, "Me gustaría aprender un oficio o especialidad técnica", "Técnica"),
    (22, "Me interesa ver resultados concretos de mi trabajo", "Técnica"),
    (23, "Me gustaría trabajar en algo práctico en el futuro", "Técnica"),

    (24, "Me interesa trabajar con personas", "Social"),
    (25, "Me gusta ayudar a otros", "Social"),
    (26, "Me interesa enseñar o explicar", "Social"),
    (27, "Me gusta participar en actividades grupales", "Social"),
    (28, "Me interesa apoyar a otras personas", "Social"),
]



def obtener_antecedente_1m(result):
    antecedente = TestResult.query.filter(
        TestResult.student_rut == result.student_rut,
        TestResult.id != result.id,
        TestResult.status == "activo",
        TestResult.course == "1° Medio"
    ).order_by(
        TestResult.created_at.desc()
    ).first()

    return antecedente


def obtener_electivos_ch(main_area, secondary_area):
    electivos = {
        "Científica": "Se sugiere priorizar electivos vinculados a Ciencias, Biología, Química, Física, Matemática, Tecnología, Investigación Escolar o áreas de profundización científica.",
        "Humanista": "Se sugiere priorizar electivos vinculados a Historia, Filosofía, Lenguaje, Literatura, Debate, Comunicación, Ciencias Sociales o formación ciudadana.",
        "Social": "Se sugiere considerar electivos o actividades vinculadas a Ciencias Sociales, Psicología, Educación, Trabajo Comunitario, Liderazgo, Participación Estudiantil o apoyo a personas.",
        "Artística": "Se sugiere complementar la formación Científico-Humanista con electivos, talleres o actividades relacionadas con Artes Visuales, Música, Teatro, Diseño, Expresión Creativa o proyectos culturales.",
        "Técnica": "Se sugiere complementar la formación Científico-Humanista con electivos o talleres aplicados, tecnología, computación, robótica, emprendimiento, innovación o proyectos prácticos."
    }

    texto = electivos.get(
        main_area,
        "Se sugiere seleccionar electivos que permitan profundizar los intereses predominantes observados."
    )

    if secondary_area and secondary_area != main_area:
        texto += (
            f" Como área complementaria, también se recomienda considerar experiencias formativas "
            f"relacionadas con el área {secondary_area}, para ampliar el desarrollo del estudiante."
        )

    return texto


def obtener_orientacion_tp(main_area, secondary_area, tp_area):
    base = {
        "Técnica": "Los resultados muestran una afinidad importante con aprendizajes prácticos, resolución de problemas concretos, uso de herramientas, tecnología o desarrollo de habilidades aplicadas. Se recomienda fortalecer la trayectoria Técnico Profesional, considerando especialidades vinculadas al área declarada por el establecimiento y a los intereses actuales del estudiante.",
        "Científica": "Los resultados muestran intereses asociados al análisis, la investigación y la comprensión de fenómenos naturales o tecnológicos. En una trayectoria Técnico Profesional, estos intereses pueden complementarse con especialidades vinculadas a tecnología, electricidad, electrónica, mecánica, informática, procesos productivos, laboratorio o áreas técnicas con base científica.",
        "Humanista": "Los resultados muestran intereses asociados a la comunicación, comprensión social, análisis de información y expresión de ideas. En una trayectoria Técnico Profesional, estos intereses pueden complementarse con especialidades del área comercial, administración, servicios, atención de personas, turismo, comunicación o gestión.",
        "Social": "Los resultados muestran intereses asociados al trabajo con personas, apoyo, colaboración y participación grupal. En una trayectoria Técnico Profesional, estos intereses pueden vincularse con especialidades de servicios, administración, atención de público, educación inicial, salud, turismo o áreas que impliquen relación directa con personas.",
        "Artística": "Los resultados muestran intereses asociados a la creatividad y expresión personal. En una trayectoria Técnico Profesional, estos intereses pueden complementarse con especialidades o talleres vinculados a diseño, gráfica, comunicación visual, gastronomía, turismo, producción, proyectos creativos o actividades culturales."
    }

    texto = base.get(
        main_area,
        "Se recomienda fortalecer la trayectoria Técnico Profesional, observando la relación entre los intereses actuales del estudiante y el área declarada por el establecimiento."
    )

    if tp_area:
        texto += f" Área Técnico Profesional declarada: {tp_area}."

    if secondary_area and secondary_area != main_area:
        texto += (
            f" Como área complementaria, se recomienda considerar experiencias relacionadas con {secondary_area}, "
            "sin desincentivar la continuidad escolar ni la trayectoria ya iniciada."
        )

    return texto


def obtener_seguimiento_media_2m(result):
    anterior = obtener_antecedente_1m(result)

    if not anterior:
        return (
            "No existe un antecedente activo de 1° Medio para este estudiante. "
            "Por lo tanto, esta evaluación de 2° Medio se considera como el primer registro disponible "
            "para el seguimiento de Enseñanza Media."
        )

    fecha_anterior = anterior.created_at.strftime("%Y") if anterior.created_at else "Sin año"

    if result.main_area == anterior.main_area:
        texto = (
            f"Al comparar con el antecedente de 1° Medio ({fecha_anterior}), se observa continuidad "
            f"en el área principal {result.main_area}. Esta estabilidad permite fortalecer progresivamente "
            "las oportunidades de profundización y acompañamiento dentro de la modalidad cursada."
        )
    else:
        texto = (
            f"Al comparar con el antecedente de 1° Medio ({fecha_anterior}), se observa una ampliación "
            f"de intereses desde el área {anterior.main_area} hacia el área {result.main_area}. "
            "Esta situación forma parte del proceso normal de exploración durante la Enseñanza Media "
            "y debe entenderse como una oportunidad para complementar la trayectoria formativa actual."
        )

    if result.secondary_area == anterior.secondary_area:
        texto += (
            f" El área secundaria se mantiene en {result.secondary_area}, lo que aporta un elemento adicional "
            "de continuidad al perfil observado."
        )
    else:
        texto += (
            f" El área secundaria actual es {result.secondary_area}, lo que permite ampliar la mirada sobre "
            "los intereses complementarios del estudiante."
        )

    return texto


def obtener_componentes_informe_2m(result):
    seguimiento = obtener_seguimiento_media_2m(result)

    interpretation = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        "Estos resultados permiten orientar la elección de electivos, áreas de profundización "
        "o trayectoria Técnico Profesional, según la modalidad que cursa actualmente."
    )

    if result.education_type == "Científico-Humanista":
        coherence_text = (
            "El estudiante se encuentra en modalidad Científico-Humanista. "
            "La orientación de este nivel debe apoyar principalmente la elección de electivos, "
            "áreas de profundización y experiencias formativas coherentes con sus intereses actuales."
        )
        decision_text = obtener_electivos_ch(result.main_area, result.secondary_area)
        recommendation_text = (
            "Se recomienda revisar junto al estudiante, su familia y el establecimiento las opciones de electivos "
            "disponibles para 3° Medio, priorizando aquellas que se relacionen con sus áreas de interés predominantes. "
            "Esta orientación debe entenderse como un apoyo para la toma de decisiones, no como una imposición."
        )

    elif result.education_type == "Técnico Profesional":
        coherence_text = (
            "El estudiante se encuentra en modalidad Técnico Profesional. "
            "La orientación de este nivel debe apoyar la vinculación entre sus intereses actuales, "
            "el área Técnico Profesional declarada y las especialidades o trayectorias formativas disponibles."
        )
        decision_text = obtener_orientacion_tp(result.main_area, result.secondary_area, result.tp_area)
        recommendation_text = (
            "Se recomienda fortalecer la continuidad escolar del estudiante dentro de su trayectoria Técnico Profesional, "
            "identificando especialidades, apoyos y experiencias prácticas que se relacionen con sus intereses actuales. "
            "Si aparecen nuevos intereses, estos deben abordarse como complemento de su formación y no como motivo para desincentivar su permanencia."
        )

    else:
        coherence_text = (
            "El estudiante declara no estar seguro de su modalidad actual o de su orientación educativa. "
            "La información obtenida debe utilizarse para reforzar el acompañamiento, la exploración y la toma de decisiones informada."
        )
        decision_text = (
            "Se recomienda revisar con el estudiante sus intereses actuales, las alternativas disponibles en el establecimiento "
            "y las opciones de apoyo vocacional, evitando decisiones apresuradas."
        )
        recommendation_text = (
            "Se recomienda mantener un proceso de acompañamiento cercano durante 2° Medio, favoreciendo la exploración, "
            "la conversación con la familia y la orientación del establecimiento."
        )

    return interpretation, coherence_text, decision_text, seguimiento, recommendation_text


def generar_respaldo_pdf_2m(result):
    interpretation, coherence_text, decision_text, seguimiento, recommendation_text = obtener_componentes_informe_2m(result)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 2° Medio. "
        "En este nivel se inicia el primer seguimiento real dentro de la Enseñanza Media, tomando como referencia "
        "los antecedentes disponibles de 1° Medio cuando existen. Su propósito es apoyar la elección de electivos "
        "en modalidad Científico-Humanista o la definición y fortalecimiento de una trayectoria Técnico Profesional."
    )

    orientacion = (
        coherence_text
        + "\n\n"
        + "Orientación sugerida:\n\n"
        + decision_text
    )

    try:
        generar_pdf_informe(
            result=result,
            titulo="Informe de Orientación Educacional - 2° Medio",
            introduccion=introduccion,
            interpretacion=interpretation,
            recomendacion=recommendation_text,
            seguimiento=seguimiento,
            orientacion=orientacion
        )
    except Exception as error:
        print(f"No se pudo generar respaldo PDF automático 2° Medio: {error}")


@test_2m_bp.route("/start", methods=["GET", "POST"])
def start_test_2m():

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

    clarity_levels = [
        "Tengo claro lo que quiero estudiar",
        "Tengo una idea, pero no estoy completamente seguro",
        "No tengo claro qué quiero estudiar"
    ]

    if request.method == "POST":

        education_type = request.form.get("education_type", "").strip()
        tp_area = request.form.get("tp_area", "").strip()
        clarity = request.form.get("clarity", "").strip()

        if not education_type or not clarity:
            flash("Debe completar los datos de contexto.", "danger")
            return render_template(
                "test_2m.html",
                questions=questions_2m,
                education_types=education_types,
                tp_areas=tp_areas,
                clarity_levels=clarity_levels
            )

        if education_type == "Técnico Profesional" and not tp_area:
            flash("Debe seleccionar el área técnico profesional.", "danger")
            return render_template(
                "test_2m.html",
                questions=questions_2m,
                education_types=education_types,
                tp_areas=tp_areas,
                clarity_levels=clarity_levels
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

        for q_id, _, area in questions_2m:
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
                "test_2m.html",
                questions=questions_2m,
                education_types=education_types,
                tp_areas=tp_areas,
                clarity_levels=clarity_levels
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

        generar_respaldo_pdf_2m(result)

        return redirect(url_for("test_2m.view_report_2m", result_id=result.id))

    return render_template(
        "test_2m.html",
        questions=questions_2m,
        education_types=education_types,
        tp_areas=tp_areas,
        clarity_levels=clarity_levels
    )


@test_2m_bp.route("/report/<int:result_id>")
def view_report_2m(result_id):

    result = TestResult.query.get_or_404(result_id)

    previous_result = obtener_antecedente_1m(result)
    has_history = previous_result is not None

    (
        interpretation,
        coherence_text,
        decision_text,
        follow_up_text,
        recommendation_text
    ) = obtener_componentes_informe_2m(result)

    publicidad = obtener_publicidad(result.course)

    return render_template(
        "report_2m.html",
        result=result,
        interpretation=interpretation,
        coherence_text=coherence_text,
        decision_text=decision_text,
        follow_up_text=follow_up_text,
        has_history=has_history,
        previous_result=previous_result,
        recommendation_text=recommendation_text,
        publicidad=publicidad
    )


@test_2m_bp.route("/report/<int:result_id>/pdf")
def download_report_2m_pdf(result_id):

    result = TestResult.query.get_or_404(result_id)

    (
        interpretation,
        coherence_text,
        decision_text,
        seguimiento,
        recommendation_text
    ) = obtener_componentes_informe_2m(result)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 2° Medio. "
        "En este nivel se inicia el primer seguimiento real dentro de la Enseñanza Media, tomando como referencia "
        "los antecedentes disponibles de 1° Medio cuando existen. Su propósito es apoyar la elección de electivos "
        "en modalidad Científico-Humanista o la definición y fortalecimiento de una trayectoria Técnico Profesional."
    )

    orientacion = (
        coherence_text
        + "\n\n"
        + "Orientación sugerida:\n\n"
        + decision_text
    )

    ruta_pdf = generar_pdf_informe(
        result=result,
        titulo="Informe de Orientación Educacional - 2° Medio",
        introduccion=introduccion,
        interpretacion=interpretation,
        recomendacion=recommendation_text,
        seguimiento=seguimiento,
        orientacion=orientacion
    )

    return send_file(ruta_pdf, as_attachment=True)
