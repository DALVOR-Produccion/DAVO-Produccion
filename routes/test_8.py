from services.basic_results import analyze_scores, profile, interpretation as basic_interpretation, workshops as basic_workshops, continuity, continuity_from_scores, history_text, SCORING_VERSION
import json
from services.basic_questionnaires import QUESTIONS_6, QUESTIONS_8, questions_for_course, instrument_version

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe
from services.publicidad import obtener_publicidad
from services.orientation_maps import obtener_continuidad_8


test_8_bp = Blueprint("test_8", __name__, url_prefix="/test8")


questions_8 = QUESTIONS_8


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
        TestResult.created_at <= result.created_at,
        TestResult.course.in_(cursos_basica)
    ).order_by(
        TestResult.created_at.asc()
    ).all()

    return resultados


def formatear_linea_historial(resultado):
    return history_text([resultado]).split("\n\n")[0]


def obtener_clasificacion_trayectoria(resultados):
    analyses = [profile(r) for r in resultados]
    if not analyses:
        return 'sin_datos'
    if all(a['kind'] == 'leading' for a in analyses) and len({a['main'] for a in analyses}) == 1:
        return 'estable'
    return 'exploracion_diversa' 


def obtener_historial_8(result):
    resultados = obtener_resultados_basica(result)
    anteriores = [r for r in resultados if r.id != result.id]
    previous = anteriores[-1] if anteriores else None
    cursos = {r.course for r in resultados}
    history_type = 'completo' if set(('6° Básico', '7° Básico', '8° Básico')).issubset(cursos) else ('parcial' if anteriores else 'sin_historial')
    return anteriores, bool(anteriores), previous, history_type, 'Seguimiento de Enseñanza Básica:\n\n' + history_text(resultados)



def generar_respaldo_pdf_8(result):
    previous_results, has_history, previous_result, history_type, seguimiento = obtener_historial_8(result)

    continuidad = continuity(result)

    areas_recomendadas = continuidad["areas"]
    areas_texto = ", ".join(areas_recomendadas)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 8° básico, "
        "etapa en la que el estudiante enfrenta una primera decisión relevante respecto de su continuidad "
        "en enseñanza media. A diferencia de 6° y 7° básico, donde el foco está puesto en la exploración "
        "temprana de intereses, en 8° básico el informe busca aportar antecedentes para orientar la elección "
        "entre continuidad Científico-Humanista, Técnico-Profesional u otras líneas complementarias de desarrollo."
    )

    interpretacion = basic_interpretation(result)

    orientacion = (
        f"{continuidad['texto']} "
        f"Áreas o líneas formativas sugeridas: {areas_texto}."
    )

    talleres = basic_workshops(result, obtener_talleres)

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

    if session.get("course") != "8° Básico":
        return redirect(url_for("students.new_student"))

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

        analysis = analyze_scores(scores)
        main_area = analysis["main"]
        secondary_area = analysis["secondary"]

        continuidad = continuity_from_scores(analysis)

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
            answers=json.dumps({**answers, "_scoring_version": SCORING_VERSION, "_instrument_version": instrument_version(session.get("course", "8° Básico"))}),
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

    continuidad = continuity(result)

    areas_recomendadas = continuidad["areas"]
    areas_texto = ", ".join(areas_recomendadas)

    interpretation = basic_interpretation(result)

    path_guidance = (
        f"{continuidad['texto']} "
        f"Áreas o líneas formativas sugeridas: {areas_texto}."
    )

    workshop_text = basic_workshops(result, obtener_talleres)

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

    continuidad = continuity(result)

    areas_recomendadas = continuidad["areas"]
    areas_texto = ", ".join(areas_recomendadas)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 8° básico, "
        "etapa en la que el estudiante enfrenta una primera decisión relevante respecto de su continuidad "
        "en enseñanza media. A diferencia de 6° y 7° básico, donde el foco está puesto en la exploración "
        "temprana de intereses, en 8° básico el informe busca aportar antecedentes para orientar la elección "
        "entre continuidad Científico-Humanista, Técnico-Profesional u otras líneas complementarias de desarrollo."
    )

    interpretacion = basic_interpretation(result)

    orientacion = (
        f"{continuidad['texto']} "
        f"Áreas o líneas formativas sugeridas: {areas_texto}."
    )

    talleres = basic_workshops(result, obtener_talleres)

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
