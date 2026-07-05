import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

try:
    from publicidad import obtener_publicidad
except Exception:
    obtener_publicidad = None


def limpiar_nombre_archivo(texto):
    texto = (texto or "archivo").strip().replace(" ", "_")

    caracteres_invalidos = ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '°']

    for caracter in caracteres_invalidos:
        texto = texto.replace(caracter, "")

    return texto


def agregar_bloque_publicidad(story, result, normal_style):
    """
    Bloque publicitario opcional.

    Si publicidad.py no tiene datos cargados, solo deja una línea separadora
    al final del informe. No modifica resultados, interpretación ni recomendaciones.
    """

    story.append(Spacer(1, 0.4 * cm))

    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color="#999999",
            spaceBefore=6,
            spaceAfter=6
        )
    )

    if not obtener_publicidad:
        return

    publicidad = obtener_publicidad(getattr(result, "course", None))

    if not publicidad:
        return

    story.append(Spacer(1, 0.2 * cm))

    for aviso in publicidad:
        nombre = aviso.get("nombre", "")
        descripcion = aviso.get("descripcion", "")
        contacto = aviso.get("contacto", "")
        telefono = aviso.get("telefono", "")

        if nombre:
            story.append(Paragraph(f"<b>{nombre}</b>", normal_style))

        if descripcion:
            story.append(Paragraph(descripcion, normal_style))

        datos_contacto = []

        if contacto:
            datos_contacto.append(f"Contacto: {contacto}")

        if telefono:
            datos_contacto.append(f"Teléfono: {telefono}")

        if datos_contacto:
            story.append(Paragraph(" | ".join(datos_contacto), normal_style))

        story.append(Spacer(1, 0.2 * cm))


def generar_pdf_informe(
    result,
    titulo,
    introduccion,
    interpretacion,
    recomendacion,
    carpeta_salida="informes",
    seguimiento=None,
    talleres=None,
    orientacion=None
):
    os.makedirs(carpeta_salida, exist_ok=True)

    fecha_actual = datetime.now()
    anio = fecha_actual.strftime("%Y")
    fecha = fecha_actual.strftime("%d-%m-%Y_%H-%M-%S")

    colegio = limpiar_nombre_archivo(result.school or "SIN_COLEGIO")
    curso = limpiar_nombre_archivo(result.course or "SIN_CURSO")
    nombre_alumno = limpiar_nombre_archivo(result.student_name or "Alumno")

    carpeta_final = os.path.join(
        carpeta_salida,
        anio,
        colegio,
        curso
    )

    os.makedirs(carpeta_final, exist_ok=True)

    nombre_archivo = f"{nombre_alumno}_Informe_Orientacion_{fecha}.pdf"

    ruta_pdf = os.path.join(carpeta_final, nombre_archivo)

    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        "TituloSistema",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=16,
        leading=20,
        spaceAfter=12
    )

    subtitulo_style = ParagraphStyle(
        "SubtituloSistema",
        parent=styles["Heading2"],
        fontSize=12,
        leading=14,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        "NormalSistema",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    story = []

    story.append(Paragraph("Sistema Integral de Orientación Educacional", titulo_style))
    story.append(Paragraph("Desarrollado por David Vargas Orellana", normal_style))
    story.append(Paragraph(titulo, titulo_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Datos del estudiante", subtitulo_style))
    story.append(Paragraph(f"<b>Nombre:</b> {result.student_name}", normal_style))
    story.append(Paragraph(f"<b>RUT:</b> {result.student_rut}", normal_style))
    story.append(Paragraph(f"<b>Colegio:</b> {result.school or 'No registrado'}", normal_style))
    curso_completo = result.course or "SIN CURSO"

    if getattr(result, "section", None) and result.section != "SIN PARALELO":
        curso_completo += f" {result.section}"

    story.append(
        Paragraph(
            f"<b>Curso:</b> {curso_completo}",
            normal_style
        )
    )
    story.append(Paragraph(f"<b>Tipo de test:</b> {result.test_type}", normal_style))
    story.append(Paragraph(f"<b>Fecha:</b> {fecha}", normal_style))

    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Introducción", subtitulo_style))
    story.append(Paragraph(introduccion, normal_style))

    story.append(Paragraph("Resultados", subtitulo_style))
    story.append(Paragraph(f"<b>Área principal observada:</b> {result.main_area}", normal_style))
    story.append(Paragraph(f"<b>Área secundaria observada:</b> {result.secondary_area}", normal_style))

    if getattr(result, "suggested_path", None):
        story.append(Paragraph(f"<b>Modalidad o ruta sugerida:</b> {result.suggested_path}", normal_style))

    story.append(Paragraph("Interpretación", subtitulo_style))
    story.append(Paragraph(interpretacion, normal_style))

    if seguimiento:
        story.append(Paragraph("Análisis de seguimiento", subtitulo_style))
        story.append(Paragraph(seguimiento, normal_style))

    if orientacion:
        story.append(Paragraph("Orientación para continuidad educativa", subtitulo_style))
        story.append(Paragraph(orientacion, normal_style))

    story.append(Paragraph("Recomendación", subtitulo_style))
    story.append(Paragraph(recomendacion, normal_style))

    if talleres:
        story.append(Paragraph("Sugerencia de talleres o actividades", subtitulo_style))
        story.append(Paragraph(talleres, normal_style))

    story.append(Spacer(1, 0.5 * cm))

    story.append(
        Paragraph(
            "Documento generado automáticamente por el Sistema Integral de Orientación Educacional.",
            normal_style
        )
    )

    agregar_bloque_publicidad(story, result, normal_style)

    doc.build(story)

    return ruta_pdf
