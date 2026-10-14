from services.basic_results import analyze_scores, profile, interpretation as basic_interpretation, workshops as basic_workshops, continuity, continuity_from_scores, history_text, SCORING_VERSION
import json
from services.basic_questionnaires import QUESTIONS_6, QUESTIONS_8, questions_for_course, instrument_version

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe


test_bp = Blueprint("test", __name__, url_prefix="/test")


questions = QUESTIONS_6


def obtener_talleres(area):
    workshop_map = {
        "Científica": "Participar en talleres de ciencias, experimentos, tecnología, medioambiente o investigación escolar.",
        "Humanista": "Participar en talleres de lectura, escritura, historia, debates o actividades culturales.",
        "Artística": "Participar en talleres de dibujo, pintura, música, danza, teatro u otras expresiones artísticas.",
        "Técnica": "Participar en talleres prácticos, robótica, computación, manualidades o actividades de creación.",
        "Social": "Participar en actividades grupales, liderazgo, convivencia escolar o apoyo comunitario."
    }

    return workshop_map.get(
        area,
        "Se recomienda participar en actividades complementarias que permitan explorar intereses y habilidades."
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


def obtener_seguimiento(result):
    return "Seguimiento de Enseñanza Básica:\n\n" + history_text(obtener_resultados_basica(result))




def obtener_textos_pdf_basico(result):
    if result.course == "7° Básico":
        introduccion = (
            "Este informe forma parte del seguimiento progresivo de intereses del estudiante. "
            "La evaluación permite comparar los resultados actuales con antecedentes anteriores, "
            "observando si existen intereses que se mantienen, cambian o comienzan a fortalecerse. "
            "En esta etapa no se busca definir una trayectoria educativa definitiva, sino reunir "
            "antecedentes que puedan ser útiles al llegar a 8° Básico, momento en que el estudiante "
            "enfrentará una primera decisión relevante respecto de su continuidad educativa."
        )

        orientacion = (
            "Se recomienda utilizar este informe como antecedente de apoyo y seguimiento del desarrollo "
            "de intereses del estudiante. En 7° Básico resulta especialmente importante observar su "
            "motivación en actividades relacionadas con sus áreas de interés, promover su participación "
            "en talleres, proyectos, actividades extracurriculares y experiencias de aprendizaje variadas "
            "que favorezcan el descubrimiento y fortalecimiento de sus habilidades.\n\n"
            "Asimismo, se recomienda registrar posibles continuidades, cambios o nuevos intereses que "
            "puedan surgir durante este período, ya que la información acumulada en 6° y 7° Básico "
            "permitirá contar con mejores antecedentes al llegar a 8° Básico, momento en que corresponderá "
            "orientar con mayor claridad la continuidad educativa.\n\n"
            "La orientación en esta etapa debe entenderse como un proceso de exploración y acompañamiento, "
            "donde lo más importante es favorecer el conocimiento de sí mismo, el desarrollo de habilidades "
            "personales y la participación activa en diversas experiencias formativas."
        )

    else:
        introduccion = (
            "Este informe corresponde a una evaluación inicial de intereses en una etapa temprana "
            "del desarrollo escolar. Su propósito es identificar señales iniciales de interés en "
            "distintas áreas del desarrollo personal y académico. Estos resultados no deben "
            "interpretarse como una definición vocacional definitiva, sino como un punto de partida "
            "para observar, acompañar y fortalecer intereses durante los próximos años. En 6° Básico, "
            "la orientación debe entenderse como un proceso exploratorio, donde lo más importante es "
            "ofrecer experiencias variadas mediante actividades escolares, talleres, proyectos y "
            "espacios de participación."
        )

        orientacion = (
            "Se recomienda utilizar este informe como antecedente inicial de apoyo. En 6° Básico "
            "lo más importante es ofrecer experiencias variadas que permitan al estudiante explorar "
            "intereses, fortalecer habilidades y desarrollar mayor conocimiento de sí mismo.\n\n"
            "La información obtenida en esta etapa servirá como punto de partida para futuras "
            "evaluaciones de seguimiento durante la Enseñanza Básica."
        )

    return introduccion, orientacion



def generar_respaldo_pdf_basico(result):
    introduccion, orientacion = obtener_textos_pdf_basico(result)

    interpretacion = basic_interpretation(result)

    seguimiento = obtener_seguimiento(result) or None

    if result.course == "6° Básico":
        recomendacion = (
            "Se recomienda utilizar este informe como primer antecedente de apoyo y seguimiento. "
            "En esta etapa escolar lo más relevante es favorecer la exploración, la participación "
            "y el descubrimiento de intereses mediante experiencias variadas. La información "
            "obtenida permitirá observar futuras continuidades o cambios durante la Enseñanza Básica."
        )
    elif result.course == "7° Básico":
        recomendacion = (
            "Se recomienda utilizar este informe como antecedente de seguimiento, considerando "
            "los resultados actuales y las evaluaciones previas disponibles. En esta etapa aún "
            "corresponde favorecer la exploración de intereses y preparar progresivamente la "
            "orientación que se realizará en 8° Básico."
        )
    else:
        recomendacion = (
            "Se recomienda utilizar este informe como antecedente de apoyo y seguimiento. "
            "En esta etapa escolar lo más relevante es favorecer la exploración, la participación "
            "y el descubrimiento de intereses. La información acumulada en estos niveles podrá ser "
            "especialmente útil al llegar a 8° básico, cuando corresponda orientar con mayor claridad "
            "la continuidad educativa."
        )

    talleres = basic_workshops(result, obtener_talleres)

    try:
        generar_pdf_informe(
            result=result,
            titulo="Informe de Orientación Educacional",
            introduccion=introduccion,
            interpretacion=interpretacion,
            recomendacion=recomendacion,
            seguimiento=seguimiento,
            talleres=talleres,
            orientacion=orientacion
        )
    except Exception as error:
        print(f"No se pudo generar respaldo PDF automático: {error}")


@test_bp.route("/start", methods=["GET", "POST"])
def start_test():

    course = session.get("course", "6° Básico")
    if course not in ("6° Básico", "7° Básico"):
        return redirect(url_for("students.new_student"))
    questions = questions_for_course(course)

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

        for q_id, _, area in questions:

            answer = request.form.get(f"q_{q_id}")

            if answer not in ["si", "no"]:
                unanswered_questions.append(q_id)
            else:
                if answer == "si":
                    scores[area] += 1

            answers[q_id] = answer

        if unanswered_questions:
            flash("Debe responder todas las preguntas antes de finalizar el test.", "danger")
            return render_template("test.html", questions=questions)

        analysis = analyze_scores(scores)
        main_area = analysis["main"]
        secondary_area = analysis["secondary"]

        result = TestResult(
            student_rut=session.get("student_rut"),
            student_name=session.get("student_name"),
            school=session.get("school"),
            school_id=session.get("school_id"),
            student_type=session.get("student_type"),
            course=session.get("course"),
            section=session.get("section"),
            test_type="Test Básico",
            answers=json.dumps({**answers, "_scoring_version": SCORING_VERSION, "_instrument_version": instrument_version(session.get("course", "6° Básico"))}),
            score_cientifica=scores["Científica"],
            score_humanista=scores["Humanista"],
            score_artistica=scores["Artística"],
            score_tecnica=scores["Técnica"],
            score_social=scores["Social"],
            main_area=main_area,
            secondary_area=secondary_area,
            suggested_path=None,
            status="activo"
        )

        db.session.add(result)
        db.session.commit()

        generar_respaldo_pdf_basico(result)

        return redirect(url_for("test.view_report", result_id=result.id))

    return render_template("test.html", questions=questions)


@test_bp.route("/report/<int:result_id>")
def view_report(result_id):

    result = TestResult.query.get_or_404(result_id)

    # Historial válido para pantalla:
    # 6° Básico no debe mostrar evaluación anterior.
    # 7° Básico solo debe considerar 6° Básico activo del mismo RUT.
    previous_results = []

    if result.course == "7° Básico":
        previous_results = TestResult.query.filter(
            TestResult.student_rut == result.student_rut,
            TestResult.id != result.id,
            TestResult.status == "activo",
        TestResult.created_at <= result.created_at,
            TestResult.course == "6° Básico"
        ).order_by(
            TestResult.created_at.asc()
        ).all()

    has_history = len(previous_results) > 0
    previous_result = previous_results[-1] if has_history else None

    if result.course == "6° Básico":
        report_type = "inicial"
    elif result.course == "7° Básico":
        report_type = "seguimiento" 
    else:
        report_type = "inicial"

    interpretation = basic_interpretation(result)

    follow_up_text = obtener_seguimiento(result)

    workshop_text = basic_workshops(result, obtener_talleres)

    if result.course == "6° Básico":
        recommendation_text = (
            "Se recomienda continuar acompañando al estudiante mediante experiencias "
            "variadas de exploración, participación y descubrimiento de intereses. "
            "Este primer registro permitirá observar futuras continuidades o cambios "
            "durante la Enseñanza Básica."
        )
    elif result.course == "7° Básico":
        recommendation_text = (
            "Se recomienda utilizar este informe como antecedente de seguimiento, "
            "considerando tanto los resultados actuales como las evaluaciones previas "
            "disponibles. En esta etapa aún corresponde favorecer la exploración de "
            "intereses y preparar progresivamente la orientación que se realizará en 8° Básico."
        )
    else:
        recommendation_text = (
            "Se recomienda continuar acompañando el desarrollo del estudiante, "
            "favoreciendo espacios de exploración, participación y descubrimiento "
            "de intereses mediante actividades escolares y talleres relacionados "
            "con las áreas detectadas."
        )

    return render_template(
        "report.html",
        result=result,
        interpretation=interpretation,
        report_type=report_type,
        has_history=has_history,
        follow_up_text=follow_up_text,
        previous_result=previous_result,
        recommendation_text=recommendation_text,
        workshop_text=workshop_text
    )


@test_bp.route("/report/<int:result_id>/pdf")
def download_report_pdf(result_id):

    result = TestResult.query.get_or_404(result_id)

    introduccion, orientacion = obtener_textos_pdf_basico(result)

    interpretacion = basic_interpretation(result)

    seguimiento = obtener_seguimiento(result) or None

    if result.course == "6° Básico":
        recomendacion = (
            "Se recomienda utilizar este informe como primer antecedente de apoyo y seguimiento. "
            "En esta etapa escolar lo más relevante es favorecer la exploración, la participación "
            "y el descubrimiento de intereses mediante experiencias variadas. La información "
            "obtenida permitirá observar futuras continuidades o cambios durante la Enseñanza Básica."
        )
    elif result.course == "7° Básico":
        recomendacion = (
            "Se recomienda utilizar este informe como antecedente de seguimiento, considerando "
            "los resultados actuales y las evaluaciones previas disponibles. En esta etapa aún "
            "corresponde favorecer la exploración de intereses y preparar progresivamente la "
            "orientación que se realizará en 8° Básico."
        )
    else:
        recomendacion = (
            "Se recomienda utilizar este informe como antecedente de apoyo y seguimiento. "
            "En esta etapa escolar lo más relevante es favorecer la exploración, la participación "
            "y el descubrimiento de intereses. La información acumulada en estos niveles podrá ser "
            "especialmente útil al llegar a 8° básico, cuando corresponda orientar con mayor claridad "
            "la continuidad educativa."
        )

    talleres = basic_workshops(result, obtener_talleres)

    ruta_pdf = generar_pdf_informe(
        result=result,
        titulo="Informe de Orientación Educacional",
        introduccion=introduccion,
        interpretacion=interpretacion,
        recomendacion=recomendacion,
        seguimiento=seguimiento,
        talleres=talleres,
        orientacion=orientacion
    )

    return send_file(ruta_pdf, as_attachment=True)
