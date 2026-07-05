import json

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe
from services.publicidad import obtener_publicidad


test_3m_bp = Blueprint("test_3m", __name__, url_prefix="/test3m")


questions_3m = [
    (1, "Me interesa estudiar carreras relacionadas con ciencias", "Científica"),
    (2, "Me gusta analizar problemas complejos", "Científica"),
    (3, "Me interesa investigar en profundidad", "Científica"),
    (4, "Me gustaría continuar estudios superiores", "Científica"),
    (5, "Me interesa comprender fenómenos naturales", "Científica"),

    (6, "Me interesa comprender la sociedad", "Humanista"),
    (7, "Me gusta debatir ideas", "Humanista"),
    (8, "Me interesa analizar temas sociales", "Humanista"),
    (9, "Me gusta escribir y argumentar", "Humanista"),
    (10, "Me interesa trabajar con personas", "Humanista"),

    (11, "Me interesa desarrollar habilidades creativas", "Artística"),
    (12, "Me gusta expresarme a través del arte", "Artística"),
    (13, "Me interesa crear ideas nuevas", "Artística"),
    (14, "Me gustaría trabajar en algo creativo", "Artística"),

    (15, "Me interesa trabajar en actividades prácticas", "Técnica"),
    (16, "Me gusta resolver problemas concretos", "Técnica"),
    (17, "Me interesa aprender haciendo", "Técnica"),
    (18, "Me gustaría trabajar en un área técnica", "Técnica"),
    (19, "Me interesa ver resultados reales de mi trabajo", "Técnica"),

    (20, "Me interesa ayudar a otros", "Social"),
    (21, "Me gusta trabajar en equipo", "Social"),
    (22, "Me interesa enseñar o guiar a otras personas", "Social"),
    (23, "Me interesa apoyar a quienes lo necesitan", "Social"),
]



def obtener_antecedente_2m(result):
    antecedente = TestResult.query.filter(
        TestResult.student_rut == result.student_rut,
        TestResult.id != result.id,
        TestResult.status == "activo",
        TestResult.course == "2° Medio"
    ).order_by(
        TestResult.created_at.desc()
    ).first()

    return antecedente


def obtener_seguimiento_3m(result):
    anterior = obtener_antecedente_2m(result)

    if not anterior:
        return (
            "No existe un antecedente activo de 2° Medio para este estudiante. "
            "Por lo tanto, esta evaluación de 3° Medio se considera como un registro de seguimiento "
            "centrado en la trayectoria educativa actualmente cursada."
        )

    fecha_anterior = anterior.created_at.strftime("%Y") if anterior.created_at else "Sin año"

    if result.main_area == anterior.main_area:
        texto = (
            f"Al comparar con el antecedente de 2° Medio ({fecha_anterior}), los resultados muestran "
            f"continuidad en el área principal {result.main_area}. "
            "Esta situación favorece la consolidación progresiva de la trayectoria educativa actualmente cursada "
            "y permite fortalecer la preparación para las decisiones futuras de continuidad de estudios."
        )
    else:
        texto = (
            f"Al comparar con el antecedente de 2° Medio ({fecha_anterior}), los resultados muestran "
            f"la incorporación de intereses complementarios asociados al área {result.main_area}. "
            "Esta situación forma parte del desarrollo personal propio de esta etapa y puede ser abordada "
            "mediante actividades, proyectos, talleres o experiencias complementarias, manteniendo la trayectoria "
            "educativa actualmente cursada."
        )

    if result.secondary_area:
        texto += (
            f" El área secundaria observada es {result.secondary_area}, lo que permite ampliar la comprensión "
            "del perfil formativo del estudiante."
        )

    return texto


def obtener_relacion_trayectoria_3m(result):
    if result.education_type == "Científico-Humanista":
        return (
            "El estudiante se encuentra cursando una trayectoria Científico-Humanista. "
            "Los intereses observados pueden desarrollarse dentro de esta formación mediante electivos, "
            "proyectos, actividades complementarias y preparación progresiva para estudios posteriores."
        )

    if result.education_type == "Técnico Profesional":
        return (
            "El estudiante se encuentra cursando una trayectoria Técnico Profesional. "
            "Los intereses observados pueden complementar la formación actualmente cursada mediante proyectos, "
            "experiencias prácticas, talleres, apoyos específicos o futuras alternativas de continuidad de estudios, "
            "manteniendo como prioridad la finalización de la Enseñanza Media."
        )

    return (
        "La información obtenida debe utilizarse para acompañar al estudiante en la consolidación de su trayectoria "
        "educativa actual y en la preparación progresiva de sus decisiones futuras."
    )


def obtener_motivacion_3m(result):
    if result.motivation == "Me siento motivado con lo que estoy estudiando":
        return (
            "El estudiante manifiesta una disposición positiva hacia la trayectoria que está desarrollando, "
            "lo que favorece la continuidad y el fortalecimiento de su proceso formativo."
        )

    if result.motivation == "Tengo algunas dudas":
        return (
            "El estudiante expresa algunas inquietudes respecto de su trayectoria actual, situación que puede formar "
            "parte del proceso normal de desarrollo vocacional. Se recomienda acompañar este proceso mediante espacios "
            "de conversación, orientación y apoyo desde el establecimiento y la familia."
        )

    if result.motivation == "No me siento motivado":
        return (
            "El estudiante manifiesta una menor conexión con la trayectoria que está desarrollando actualmente. "
            "Se recomienda fortalecer el acompañamiento desde el establecimiento y la familia, apoyando al estudiante "
            "en la consolidación de su trayectoria educativa actual y en la preparación progresiva de sus decisiones "
            "futuras de continuidad de estudios."
        )

    return "No se dispone de información suficiente respecto del nivel de motivación del estudiante."


def obtener_componentes_informe_3m(result):
    interpretation = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        "En 3° Medio estos resultados deben interpretarse como información de seguimiento y fortalecimiento "
        "de la trayectoria educativa actualmente cursada, no como una indicación de cambio de modalidad o especialidad."
    )

    relation_text = obtener_relacion_trayectoria_3m(result)
    motivation_text = obtener_motivacion_3m(result)
    follow_up_text = obtener_seguimiento_3m(result)

    recommendation_text = (
        "La prioridad durante esta etapa es finalizar exitosamente la Enseñanza Media, fortaleciendo la trayectoria "
        "educativa actualmente cursada y preparando progresivamente las decisiones de continuidad de estudios que "
        "se abordarán con mayor profundidad en 4° Medio."
    )

    return interpretation, relation_text, motivation_text, follow_up_text, recommendation_text


def generar_respaldo_pdf_3m(result):
    interpretation, relation_text, motivation_text, seguimiento, recommendation_text = obtener_componentes_informe_3m(result)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 3° Medio. "
        "En esta etapa el estudiante ya se encuentra cursando una trayectoria definida, ya sea mediante electivos "
        "en modalidad Científico-Humanista o una especialidad en modalidad Técnico Profesional. "
        "Por ello, el objetivo principal del informe es acompañar, fortalecer y consolidar su trayectoria actual, "
        "preparando progresivamente el cierre de la Enseñanza Media."
    )

    orientacion = (
        "Relación con la trayectoria actual:\n\n"
        + relation_text
        + "\n\n"
        + "Motivación declarada:\n\n"
        + motivation_text
    )

    try:
        generar_pdf_informe(
            result=result,
            titulo="Informe de Orientación Educacional - 3° Medio",
            introduccion=introduccion,
            interpretacion=interpretation,
            recomendacion=recommendation_text,
            seguimiento=seguimiento,
            orientacion=orientacion
        )
    except Exception as error:
        print(f"No se pudo generar respaldo PDF automático 3° Medio: {error}")


@test_3m_bp.route("/start", methods=["GET", "POST"])
def start_test_3m():

    education_types = [
        "Científico-Humanista",
        "Técnico Profesional"
    ]

    tp_areas = [
        "Industrial",
        "Comercial",
        "Servicios",
        "Otro",
        "No sabe"
    ]

    electives = [
        "Ciencias",
        "Humanidades",
        "Matemática",
        "Artes",
        "Lengua y Literatura",
        "Educación Física",
        "Mixto",
        "No sabe"
    ]

    motivation_levels = [
        "Me siento motivado con lo que estoy estudiando",
        "Tengo algunas dudas",
        "No me siento motivado"
    ]

    if request.method == "POST":

        education_type = request.form.get("education_type", "").strip()
        tp_area = request.form.get("tp_area", "").strip()
        specialty = request.form.get("specialty", "").strip()
        elective = request.form.get("elective", "").strip()
        motivation = request.form.get("motivation", "").strip()

        if not education_type or not motivation:
            flash("Debe completar los datos de contexto.", "danger")
            return render_template(
                "test_3m.html",
                questions=questions_3m,
                education_types=education_types,
                tp_areas=tp_areas,
                electives=electives,
                motivation_levels=motivation_levels
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

        for q_id, _, area in questions_3m:
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
                "test_3m.html",
                questions=questions_3m,
                education_types=education_types,
                tp_areas=tp_areas,
                electives=electives,
                motivation_levels=motivation_levels
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
            tp_area=tp_area if education_type == "Técnico Profesional" else elective,
            answers=json.dumps(answers),
            score_cientifica=scores["Científica"],
            score_humanista=scores["Humanista"],
            score_artistica=scores["Artística"],
            score_tecnica=scores["Técnica"],
            score_social=scores["Social"],
            main_area=main_area,
            secondary_area=secondary_area,
            suggested_path=suggested_path,
            motivation=motivation
        )

        db.session.add(result)
        db.session.commit()

        generar_respaldo_pdf_3m(result)

        return redirect(url_for("test_3m.view_report_3m", result_id=result.id))

    return render_template(
        "test_3m.html",
        questions=questions_3m,
        education_types=education_types,
        tp_areas=tp_areas,
        electives=electives,
        motivation_levels=motivation_levels
    )


@test_3m_bp.route("/report/<int:result_id>")
def view_report_3m(result_id):

    result = TestResult.query.get_or_404(result_id)

    previous_result = obtener_antecedente_2m(result)
    has_history = previous_result is not None

    (
        interpretation,
        coherence_text,
        motivation_text,
        change_text,
        recommendation_text
    ) = obtener_componentes_informe_3m(result)

    publicidad = obtener_publicidad(result.course)

    return render_template(
        "report_3m.html",
        result=result,
        interpretation=interpretation,
        coherence_text=coherence_text,
        motivation_text=motivation_text,
        change_text=change_text,
        recommendation_text=recommendation_text,
        has_history=has_history,
        previous_result=previous_result,
        publicidad=publicidad
    )


@test_3m_bp.route("/report/<int:result_id>/pdf")
def download_report_3m_pdf(result_id):

    result = TestResult.query.get_or_404(result_id)

    (
        interpretation,
        relation_text,
        motivation_text,
        seguimiento,
        recommendation_text
    ) = obtener_componentes_informe_3m(result)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 3° Medio. "
        "En esta etapa el estudiante ya se encuentra cursando una trayectoria definida, ya sea mediante electivos "
        "en modalidad Científico-Humanista o una especialidad en modalidad Técnico Profesional. "
        "Por ello, el objetivo principal del informe es acompañar, fortalecer y consolidar su trayectoria actual, "
        "preparando progresivamente el cierre de la Enseñanza Media."
    )

    orientacion = (
        "Relación con la trayectoria actual:\n\n"
        + relation_text
        + "\n\n"
        + "Motivación declarada:\n\n"
        + motivation_text
    )

    ruta_pdf = generar_pdf_informe(
        result=result,
        titulo="Informe de Orientación Educacional - 3° Medio",
        introduccion=introduccion,
        interpretacion=interpretation,
        recomendacion=recommendation_text,
        seguimiento=seguimiento,
        orientacion=orientacion
    )

    return send_file(ruta_pdf, as_attachment=True)
