import json

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models import db
from models.test_result import TestResult
from services.pdf_generator import generar_pdf_informe
from services.publicidad import obtener_publicidad


test_4m_bp = Blueprint("test_4m", __name__, url_prefix="/test4m")


questions_4m = [
    (1, "Me interesa continuar estudios superiores", "Científica"),
    (2, "Me gustan los desafíos académicos", "Científica"),
    (3, "Me interesa estudiar carreras relacionadas con ciencias o tecnología", "Científica"),
    (4, "Me gusta investigar y analizar información", "Científica"),
    (5, "Me interesa resolver problemas complejos", "Científica"),

    (6, "Me interesa comprender la sociedad y sus problemas", "Humanista"),
    (7, "Me gusta leer, escribir o argumentar ideas", "Humanista"),
    (8, "Me interesan carreras relacionadas con comunicación, leyes o educación", "Humanista"),
    (9, "Me gusta debatir temas de actualidad", "Humanista"),
    (10, "Me interesa comprender el comportamiento humano", "Humanista"),

    (11, "Me interesa desarrollar proyectos creativos", "Artística"),
    (12, "Me gusta expresarme mediante arte, diseño, música o creación visual", "Artística"),
    (13, "Me gustaría estudiar o trabajar en áreas creativas", "Artística"),
    (14, "Me interesa crear productos, imágenes, contenidos o propuestas visuales", "Artística"),

    (15, "Me interesa aplicar conocimientos en trabajos prácticos", "Técnica"),
    (16, "Me gustaría trabajar en un área técnica o especializada", "Técnica"),
    (17, "Me interesa seguir perfeccionándome en una especialidad", "Técnica"),
    (18, "Me gustaría combinar trabajo y estudios", "Técnica"),
    (19, "Me interesa obtener herramientas concretas para insertarme laboralmente", "Técnica"),

    (20, "Me interesa ayudar o acompañar a otras personas", "Social"),
    (21, "Me gustaría estudiar carreras relacionadas con apoyo social, salud o educación", "Social"),
    (22, "Me gusta trabajar con personas", "Social"),
    (23, "Me interesa aportar al bienestar de otros", "Social"),
]



def obtener_antecedente_3m(result):
    antecedente = TestResult.query.filter(
        TestResult.student_rut == result.student_rut,
        TestResult.id != result.id,
        TestResult.status == "activo",
        TestResult.course == "3° Medio"
    ).order_by(TestResult.created_at.desc()).first()

    return antecedente


def obtener_carreras_ch(area):
    carreras = {
        "Científica": "Carreras universitarias sugeridas: Ingeniería Civil, Ingeniería Informática, Ingeniería Industrial, Medicina, Enfermería, Tecnología Médica, Química y Farmacia, Biotecnología, Kinesiología o áreas vinculadas a ciencias, salud, tecnología e investigación.",
        "Humanista": "Carreras sugeridas: Derecho, Psicología, Periodismo, Pedagogía, Administración Pública, Sociología, Ciencia Política, Trabajo Social o áreas vinculadas a comunicación, educación, gestión pública y análisis social.",
        "Social": "Carreras sugeridas: Trabajo Social, Psicología, Pedagogía, Terapia Ocupacional, Educación Parvularia, Fonoaudiología, Enfermería o áreas vinculadas a salud, educación, apoyo comunitario y acompañamiento de personas.",
        "Artística": "Carreras sugeridas: Diseño Gráfico, Diseño Industrial, Arquitectura, Comunicación Audiovisual, Música, Artes Visuales, Animación Digital, Publicidad o áreas vinculadas a diseño, creación, cultura y comunicación visual.",
        "Técnica": "Carreras sugeridas: Ingeniería en Informática, Ingeniería en Ejecución, Ingeniería Industrial, Técnico en Automatización, Técnico en Electricidad, Técnico en Mecánica, Técnico en Construcción, Técnico en Administración o áreas aplicadas vinculadas a tecnología, procesos y resolución práctica de problemas."
    }

    return carreras.get(
        area,
        "Se recomienda explorar carreras, programas de formación y áreas ocupacionales relacionadas con los intereses predominantes observados."
    )


def obtener_continuidad_tp(area, tp_area):
    rutas = {
        "Industrial": (
            "Continuidad de estudios sugerida: Técnico en Electricidad, Técnico en Automatización, Técnico en Mecánica, "
            "Técnico en Construcción, Ingeniería en Electricidad, Ingeniería Mecánica, Ingeniería Industrial o programas vinculados "
            "a mantenimiento, operaciones, producción, construcción y tecnología.\n\n"
            "Áreas laborales posibles: mantenimiento industrial, electricidad, producción, operaciones, construcción, minería, "
            "logística técnica o apoyo en procesos productivos."
        ),
        "Comercial": (
            "Continuidad de estudios sugerida: Técnico en Administración, Técnico en Contabilidad, Auditoría, Ingeniería en Administración, "
            "Ingeniería Comercial, Recursos Humanos, Logística o programas vinculados a gestión y negocios.\n\n"
            "Áreas laborales posibles: administración, contabilidad, ventas, atención de clientes, recursos humanos, finanzas, "
            "logística o apoyo a la gestión de empresas."
        ),
        "Servicios": (
            "Continuidad de estudios sugerida: Turismo, Gastronomía, Hotelería, Técnico en Educación, Técnico en Enfermería, "
            "Administración de Servicios, Atención de Personas o programas vinculados a salud, educación, turismo y servicios.\n\n"
            "Áreas laborales posibles: atención de público, turismo, hotelería, servicios, educación inicial, salud, gastronomía "
            "o apoyo operativo en instituciones."
        ),
        "Otro": (
            "Continuidad de estudios sugerida: programas técnicos o profesionales relacionados con la especialidad cursada, "
            "considerando Centros de Formación Técnica, Institutos Profesionales o Universidades según los intereses del estudiante.\n\n"
            "Áreas laborales posibles: dependerán de la especialidad desarrollada, sus competencias prácticas y la oferta laboral local."
        ),
        "No sabe": (
            "Se recomienda revisar junto al estudiante la especialidad cursada, sus competencias adquiridas y las alternativas de continuidad "
            "disponibles en CFT, Institutos Profesionales o Universidades.\n\n"
            "Áreas laborales posibles: dependerán de las competencias técnicas desarrolladas durante la Enseñanza Media."
        )
    }

    texto = rutas.get((tp_area or "").strip(), rutas["Otro"])

    if area and area != "Técnica":
        texto += (
            "\n\nLos intereses observados en esta evaluación también pueden ampliar sus alternativas futuras, "
            f"especialmente en áreas relacionadas con {area}. Estos intereses deben entenderse como complemento de la formación ya adquirida."
        )

    texto += (
        "\n\nSi el estudiante desea proyectarse hacia una ruta universitaria, puede fortalecer su preparación mediante "
        "preuniversitario, programas propedéuticos, nivelación académica, bachilleratos u otras instancias de apoyo para la educación superior."
    )

    return texto


def obtener_seguimiento_4m(result):
    anterior = obtener_antecedente_3m(result)

    if not anterior:
        return (
            "No existe un antecedente activo de 3° Medio para este estudiante. "
            "Por lo tanto, esta evaluación de 4° Medio se considera como el principal antecedente disponible "
            "para apoyar la definición de alternativas de continuidad de estudios."
        )

    fecha_anterior = anterior.created_at.strftime("%Y") if anterior.created_at else "Sin año"

    if result.main_area == anterior.main_area:
        texto = (
            f"Al comparar con el antecedente de 3° Medio ({fecha_anterior}), los resultados muestran continuidad "
            f"en el área principal {result.main_area}. Esta situación aporta mayores antecedentes para la planificación "
            "de alternativas de continuidad de estudios y desarrollo futuro."
        )
    else:
        texto = (
            f"Al comparar con el antecedente de 3° Medio ({fecha_anterior}), los resultados actuales amplían los intereses "
            f"observados previamente y aportan nuevos antecedentes para la definición de alternativas de continuidad de estudios. "
            "Esta información debe entenderse como una ampliación del perfil formativo del estudiante y no como una modificación "
            "de la trayectoria ya desarrollada."
        )

    if result.secondary_area:
        texto += (
            f" El área secundaria observada es {result.secondary_area}, lo que permite considerar alternativas complementarias "
            "al momento de proyectar estudios, formación técnica, ruta mixta o inserción laboral."
        )

    return texto


def obtener_claridad_4m(result):
    if result.motivation == "Tengo claridad de lo que quiero estudiar":
        return (
            "El estudiante presenta una definición relativamente clara respecto de su continuidad de estudios y dispone "
            "de antecedentes que pueden facilitar la toma de decisiones futuras."
        )

    if result.motivation == "Tengo algunas dudas":
        return (
            "El estudiante dispone de intereses identificados, pero aún se encuentra evaluando distintas alternativas. "
            "Se recomienda continuar explorando opciones de formación y campos ocupacionales antes de tomar una decisión final."
        )

    return (
        "El estudiante se encuentra en proceso de definición de sus alternativas futuras y puede beneficiarse de nuevas "
        "instancias de orientación, conversación familiar, revisión de oferta educativa y exploración de campos ocupacionales."
    )


def obtener_proyeccion_4m(result):
    if result.education_type == "Científico-Humanista":
        return (
            "Proyección para trayectoria Científico-Humanista:\n\n"
            + obtener_carreras_ch(result.main_area)
            + "\n\nSe recomienda revisar requisitos de admisión, ponderaciones, oferta de universidades, institutos profesionales "
            "y alternativas de financiamiento. Si proyecta ingreso universitario, puede ser conveniente fortalecer su preparación "
            "académica mediante preuniversitario, ensayos, nivelación o apoyo escolar específico."
        )

    if result.education_type == "Técnico Profesional":
        return (
            "Proyección para trayectoria Técnico Profesional:\n\n"
            "El estudiante finaliza una trayectoria Técnico Profesional que le entrega competencias, conocimientos y una certificación "
            "válida para su desarrollo futuro. Los intereses observados en esta evaluación pueden ampliar sus alternativas de continuidad "
            "de estudios y complementar la formación ya adquirida.\n\n"
            + obtener_continuidad_tp(result.main_area, result.tp_area)
        )

    return (
        "Se recomienda revisar alternativas de continuidad de estudios, formación técnica, educación superior, ruta mixta o inserción laboral, "
        "considerando los intereses, habilidades, trayectoria educativa y oportunidades disponibles."
    )


def obtener_componentes_informe_4m(result):
    interpretation = (
        f"El estudiante presenta una tendencia principal hacia el área {result.main_area} "
        f"y una tendencia secundaria hacia el área {result.secondary_area}. "
        "En 4° Medio estos resultados deben interpretarse como antecedentes para proyectar alternativas de continuidad "
        "de estudios, formación técnica, educación superior, ruta mixta o inserción laboral."
    )

    career_examples = obtener_carreras_ch(result.main_area)
    clarity_text = obtener_claridad_4m(result)
    follow_up_text = obtener_seguimiento_4m(result)
    projection_text = obtener_proyeccion_4m(result)

    final_recommendation = (
        "Este informe representa el cierre del proceso de orientación desarrollado durante la Enseñanza Media. "
        "La decisión final respecto de la continuidad de estudios corresponde al estudiante y su familia. "
        "La información presentada tiene por objetivo apoyar la toma de decisiones informadas, considerando "
        "los intereses, habilidades, trayectoria educativa y oportunidades disponibles."
    )

    return interpretation, career_examples, clarity_text, follow_up_text, projection_text, final_recommendation


def generar_respaldo_pdf_4m(result):
    (
        interpretation,
        career_examples,
        clarity_text,
        seguimiento,
        projection_text,
        final_recommendation
    ) = obtener_componentes_informe_4m(result)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 4° Medio, etapa de cierre "
        "de la Enseñanza Media y de proyección hacia estudios superiores, formación técnica, ruta mixta o inserción laboral. "
        "Su propósito es entregar antecedentes claros y concretos para apoyar la toma de decisiones futuras."
    )

    orientacion = (
        "Claridad vocacional:\n\n"
        + clarity_text
        + "\n\n"
        + "Alternativas de continuidad:\n\n"
        + projection_text
    )

    try:
        generar_pdf_informe(
            result=result,
            titulo="Informe de Orientación Educacional - 4° Medio",
            introduccion=introduccion,
            interpretacion=interpretation,
            recomendacion=final_recommendation,
            seguimiento=seguimiento,
            orientacion=orientacion
        )
    except Exception as error:
        print(f"No se pudo generar respaldo PDF automático 4° Medio: {error}")




@test_4m_bp.route("/start", methods=["GET", "POST"])
def start_test_4m():

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

    clarity_levels = [
        "Tengo claridad de lo que quiero estudiar",
        "Tengo algunas dudas",
        "No tengo claridad"
    ]

    if request.method == "POST":

        education_type = request.form.get("education_type", "").strip()
        tp_area = request.form.get("tp_area", "").strip()
        specialty = request.form.get("specialty", "").strip()
        elective = request.form.get("elective", "").strip()
        clarity = request.form.get("clarity", "").strip()

        if not education_type or not clarity:
            flash("Debe completar los datos de contexto.", "danger")
            return render_template(
                "test_4m.html",
                questions=questions_4m,
                education_types=education_types,
                tp_areas=tp_areas,
                electives=electives,
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

        for q_id, _, area in questions_4m:
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
                "test_4m.html",
                questions=questions_4m,
                education_types=education_types,
                tp_areas=tp_areas,
                electives=electives,
                clarity_levels=clarity_levels
            )

        sorted_areas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        main_area = sorted_areas[0][0]
        secondary_area = sorted_areas[1][0]

        if main_area == "Científica":
            suggested_path = "Universidad"
        elif main_area == "Humanista":
            suggested_path = "Universidad / Instituto Profesional"
        elif main_area == "Técnica":
            suggested_path = "CFT / Instituto Profesional / Ruta mixta"
        elif main_area == "Social":
            suggested_path = "Universidad / Instituto Profesional"
        elif main_area == "Artística":
            suggested_path = "Instituto Profesional / Formación especializada"
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
            motivation=clarity
        )

        db.session.add(result)
        db.session.commit()

        generar_respaldo_pdf_4m(result)

        return redirect(url_for("test_4m.view_report_4m", result_id=result.id))

    return render_template(
        "test_4m.html",
        questions=questions_4m,
        education_types=education_types,
        tp_areas=tp_areas,
        electives=electives,
        clarity_levels=clarity_levels
    )


@test_4m_bp.route("/report/<int:result_id>")
def view_report_4m(result_id):

    result = TestResult.query.get_or_404(result_id)

    previous_result = obtener_antecedente_3m(result)
    has_history = previous_result is not None

    (
        interpretation,
        career_examples,
        clarity_text,
        follow_up_text,
        projection_text,
        final_recommendation
    ) = obtener_componentes_informe_4m(result)

    publicidad = obtener_publicidad(result.course)

    return render_template(
        "report_4m.html",
        result=result,
        interpretation=interpretation,
        career_examples=career_examples,
        clarity_text=clarity_text,
        follow_up_text=follow_up_text,
        projection_text=projection_text,
        has_history=has_history,
        previous_result=previous_result,
        final_recommendation=final_recommendation,
        publicidad=publicidad
    )


@test_4m_bp.route("/report/<int:result_id>/pdf")
def download_report_4m_pdf(result_id):

    result = TestResult.query.get_or_404(result_id)

    (
        interpretation,
        career_examples,
        clarity_text,
        seguimiento,
        projection_text,
        final_recommendation
    ) = obtener_componentes_informe_4m(result)

    introduccion = (
        "Este informe corresponde a una evaluación de orientación educacional aplicada en 4° Medio, etapa de cierre "
        "de la Enseñanza Media y de proyección hacia estudios superiores, formación técnica, ruta mixta o inserción laboral. "
        "Su propósito es entregar antecedentes claros y concretos para apoyar la toma de decisiones futuras."
    )

    orientacion = (
        "Claridad vocacional:\n\n"
        + clarity_text
        + "\n\n"
        + "Alternativas de continuidad:\n\n"
        + projection_text
    )

    ruta_pdf = generar_pdf_informe(
        result=result,
        titulo="Informe de Orientación Educacional - 4° Medio",
        introduccion=introduccion,
        interpretacion=interpretation,
        recomendacion=final_recommendation,
        seguimiento=seguimiento,
        orientacion=orientacion
    )

    return send_file(ruta_pdf, as_attachment=True)
