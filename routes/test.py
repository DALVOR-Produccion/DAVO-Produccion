import json

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe


test_bp = Blueprint("test", __name__, url_prefix="/test")


questions = [
    (1, "Me gusta ayudar a otras personas", "Social"),
    (2, "Me gusta saber cómo funcionan las cosas", "Científica"),
    (3, "Me gusta dibujar o pintar", "Artística"),
    (4, "Me gusta armar o reparar objetos", "Técnica"),
    (5, "Me gusta leer cuentos o historias", "Humanista"),
    (6, "Me interesa hacer experimentos", "Científica"),
    (7, "Me gusta la música, bailar o cantar", "Artística"),
    (8, "Me gusta trabajar en grupo", "Social"),
    (9, "Me interesa aprender sobre historia", "Humanista"),
    (10, "Me interesa usar herramientas", "Técnica"),
    (11, "Me gusta aprender sobre el cuerpo humano o la naturaleza", "Científica"),
    (12, "Me gusta crear cosas nuevas", "Artística"),
    (13, "Me gusta escuchar a otros", "Social"),
    (14, "Me gusta escribir o contar ideas", "Humanista"),
    (15, "Me gusta aprender haciendo cosas prácticas", "Técnica"),
    (16, "Me gusta resolver problemas", "Científica"),
    (17, "Me interesa participar en actividades artísticas", "Artística"),
    (18, "Me interesa enseñar o explicar cosas", "Social"),
    (19, "Me interesa conocer otras culturas", "Humanista"),
    (20, "Me interesa la tecnología o los computadores", "Técnica"),
]


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


def obtener_seguimiento(result):
    resultados_basica = obtener_resultados_basica(result)

    if result.course == "6° Básico":
        return (
            "Seguimiento de Enseñanza Básica:\n\n"
            "Esta evaluación constituye una primera aproximación a los intereses "
            "y preferencias del estudiante.\n\n"
            "Los resultados obtenidos servirán como antecedente para futuras "
            "evaluaciones de seguimiento durante la Enseñanza Básica."
        )

    if result.course == "7° Básico":

        previos = [
            r for r in resultados_basica
            if r.id != result.id and r.course == "6° Básico"
        ]

        if not previos:
            return (
                "Seguimiento de Enseñanza Básica:\n\n"
                "No existen evaluaciones previas registradas para este estudiante "
                "en Enseñanza Básica.\n\n"
                "Las conclusiones de este informe se basan exclusivamente en los "
                "resultados obtenidos en la presente evaluación."
            )

        anterior = previos[-1]

        lineas = [
            formatear_linea_historial(anterior),
            formatear_linea_historial(result)
        ]

        if anterior.main_area == result.main_area:
            analisis = (
                f"Los resultados muestran una tendencia consistente hacia el área "
                f"{result.main_area} entre las evaluaciones registradas. "
                "La estabilidad observada permite identificar intereses que comienzan "
                "a consolidarse durante esta etapa escolar."
            )
        else:
            analisis = (
                f"Los resultados muestran una evolución de intereses desde el área "
                f"{anterior.main_area} hacia el área {result.main_area}. "
                "Esta situación es habitual durante el proceso de desarrollo vocacional "
                "y refleja una etapa de exploración y descubrimiento de intereses."
            )

        return (
            "Seguimiento de Enseñanza Básica:\n\n"
            + "\n".join(lineas)
            + "\n\n"
            + analisis
        )

    previous_results = TestResult.query.filter(
        TestResult.student_rut == result.student_rut,
        TestResult.id != result.id
    ).order_by(TestResult.created_at.asc()).all()

    if not previous_results:
        return ""

    previous_result = previous_results[-1]

    if result.main_area == previous_result.main_area:
        return (
            f"Al comparar con la evaluación anterior, se observa continuidad "
            f"en el área {result.main_area}, lo que refleja estabilidad "
            f"en los intereses observados."
        )

    return (
        f"Se observa una evolución desde el área {previous_result.main_area} "
        f"hacia el área {result.main_area}, lo que puede corresponder "
        f"a un proceso natural de exploración de intereses."
    )




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

    interpretacion = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una inclinación secundaria hacia el área {result.secondary_area}. Estos resultados "
        f"permiten observar intereses predominantes en esta etapa escolar y apoyar su desarrollo "
        f"progresivo. No constituyen una decisión definitiva sobre su trayectoria educativa futura."
    )

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

    talleres = obtener_talleres(result.main_area)

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

        sorted_areas = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        main_area = sorted_areas[0][0]
        secondary_area = sorted_areas[1][0]

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

    interpretation = (
        f"El estudiante presenta una tendencia principal hacia el área "
        f"{result.main_area} y una inclinación secundaria hacia el área "
        f"{result.secondary_area}. Estos resultados permiten observar "
        f"intereses predominantes en esta etapa escolar y apoyar su "
        f"desarrollo progresivo."
    )

    follow_up_text = obtener_seguimiento(result)

    workshop_text = obtener_talleres(result.main_area)

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

    interpretacion = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una inclinación secundaria hacia el área {result.secondary_area}. Estos resultados "
        f"permiten observar intereses predominantes en esta etapa escolar y apoyar su desarrollo "
        f"progresivo. No constituyen una decisión definitiva sobre su trayectoria educativa futura."
    )

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

    talleres = obtener_talleres(result.main_area)

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
