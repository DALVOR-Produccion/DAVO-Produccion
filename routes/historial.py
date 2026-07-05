from collections import Counter

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file

from models.test_result import TestResult
from models import db

import os
import re
import pandas as pd
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


historial_bp = Blueprint(
    "historial",
    __name__,
    url_prefix="/historial"
)


def usuario_autorizado():
    return session.get("admin_logged") or session.get("colegio_logged")


def obtener_orden_curso_valor(curso):
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


def obtener_valor_predominante(contador, texto_empate):
    if not contador:
        return "Sin datos", []

    maximo = max(contador.values())

    areas_maximas = [
        area
        for area, cantidad in contador.items()
        if cantidad == maximo
    ]

    if len(areas_maximas) > 1:
        return (
            f"{texto_empate}: " + ", ".join(areas_maximas),
            areas_maximas
        )

    return areas_maximas[0], areas_maximas


def obtener_tendencia_por_curso(curso):
    tendencias = {
        "6° Básico": "Exploración inicial",
        "7° Básico": "Exploración y seguimiento",
        "8° Básico": "Orientación para continuidad educativa",
        "1° Medio": "Inicio de trayectoria de Enseñanza Media",
        "2° Medio": "Definición progresiva de trayectoria educativa",
        "3° Medio": "Consolidación de trayectoria educativa",
        "4° Medio": "Proyección de continuidad de estudios y desarrollo vocacional",
    }

    return tendencias.get(curso or "", "Sin información suficiente")


def obtener_analisis_historial(resultados):
    if not resultados:
        return {
            "area_predominante": "Sin datos",
            "area_secundaria_predominante": "Sin datos",
            "tendencia": "Sin información suficiente",
            "texto": "No existen evaluaciones registradas para generar análisis histórico."
        }

    resultados_ordenados = sorted(
        resultados,
        key=lambda r: (
            obtener_orden_curso_valor(r.course),
            r.created_at
        )
    )

    ultimo_curso = max(
        resultados_ordenados,
        key=lambda r: obtener_orden_curso_valor(r.course)
    )

    areas_principales = [
        r.main_area
        for r in resultados_ordenados
        if r.main_area
    ]

    areas_secundarias = [
        r.secondary_area
        for r in resultados_ordenados
        if r.secondary_area
    ]

    contador_principal = Counter(areas_principales)
    contador_secundaria = Counter(areas_secundarias)

    area_predominante, areas_principales_maximas = obtener_valor_predominante(
        contador_principal,
        "Trayectoria de intereses diversificada"
    )

    area_secundaria, areas_secundarias_maximas = obtener_valor_predominante(
        contador_secundaria,
        "Trayectoria de intereses complementarios diversificada"
    )

    tendencia = obtener_tendencia_por_curso(ultimo_curso.course)

    total = len(resultados_ordenados)
    curso_actual = ultimo_curso.course or "Sin curso"
    area_actual = ultimo_curso.main_area or "Sin área"
    secundaria_actual = ultimo_curso.secondary_area or "Sin área secundaria"

    hay_empate_principal = len(areas_principales_maximas) > 1
    hay_empate_secundaria = len(areas_secundarias_maximas) > 1

    if total == 1:
        texto = (
            f"El estudiante registra una primera evaluación en {curso_actual}, "
            f"con área principal {area_actual} y área secundaria {secundaria_actual}. "
            "Este registro debe entenderse como un antecedente inicial para futuras "
            "evaluaciones de seguimiento."
        )

    elif hay_empate_principal:
        texto = (
            f"El historial muestra una trayectoria de intereses diversificada, con presencia de las áreas "
            f"{', '.join(areas_principales_maximas)}. "
            "Esto indica que no existe una única área predominante histórica, sino un recorrido con intereses "
            "que se han expresado en distintas áreas durante el proceso de orientación."
        )

        if curso_actual in ["8° Básico", "4° Medio"]:
            texto += (
                f" Considerando que el curso actual es {curso_actual}, el resultado más reciente adquiere "
                f"especial importancia para la toma de decisiones de cierre de ciclo: área principal actual "
                f"{area_actual} y área secundaria actual {secundaria_actual}."
            )

        else:
            texto += (
                f" El resultado más reciente corresponde a {curso_actual}, con área principal {area_actual} "
                f"y área secundaria {secundaria_actual}."
            )

    else:
        cantidad_predominante = contador_principal.get(area_predominante, 0)

        if cantidad_predominante == total:
            texto = (
                f"Se observa una continuidad histórica hacia el área {area_predominante} durante "
                f"{total} evaluaciones registradas. Esto puede indicar estabilidad progresiva "
                "en los intereses observados."
            )
        else:
            texto = (
                f"Se observa una mayor presencia histórica del área {area_predominante}, aunque también "
                "existen otros intereses registrados durante el proceso. Se recomienda considerar tanto "
                "la continuidad como las áreas complementarias observadas."
            )

        if curso_actual in ["8° Básico", "4° Medio"]:
            texto += (
                f" Al encontrarse actualmente en {curso_actual}, se debe considerar especialmente el resultado "
                f"actual para apoyar la orientación de cierre de ciclo: área principal {area_actual} "
                f"y área secundaria {secundaria_actual}."
            )

    if hay_empate_secundaria:
        texto += (
            f" En el área secundaria se observa una trayectoria complementaria diversificada, con presencia de "
            f"{', '.join(areas_secundarias_maximas)}."
        )
    elif area_secundaria != "Sin datos":
        texto += (
            f" Como área secundaria predominante se observa {area_secundaria}, lo que puede aportar información "
            "complementaria para comprender mejor el perfil del estudiante."
        )

    return {
        "area_predominante": area_predominante,
        "area_secundaria_predominante": area_secundaria,
        "tendencia": tendencia,
        "texto": texto
    }


def obtener_alumnos_actuales_por_rut(query_base):
    registros = query_base.order_by(
        TestResult.student_rut.asc(),
        TestResult.created_at.desc()
    ).all()

    alumnos = {}

    for r in registros:
        rut = r.student_rut

        if not rut:
            continue

        if rut not in alumnos:
            alumnos[rut] = r

    return list(alumnos.values())


@historial_bp.route("/")
def index():
    if not usuario_autorizado():
        return redirect(url_for("home"))

    search = request.args.get("search", "").strip()

    query = TestResult.query.filter_by(status="activo")

    if session.get("colegio_logged"):
        school_id = session.get("colegio_school_id")
        query = query.filter(TestResult.school_id == school_id)

    if search:
        query = query.filter(
            db.or_(
                TestResult.student_rut.ilike(f"%{search}%"),
                TestResult.student_name.ilike(f"%{search}%")
            )
        )

    alumnos = obtener_alumnos_actuales_por_rut(query)

    alumnos = sorted(
        alumnos,
        key=lambda r: (
            r.school or "",
            obtener_orden_curso_valor(r.course),
            r.section or "",
            r.student_name or ""
        )
    )

    return render_template(
        "historial/index.html",
        alumnos=alumnos,
        search=search
    )



def limpiar_nombre_archivo(texto):
    if not texto:
        return "historial"
    texto = texto.strip().lower().replace(" ", "_")
    texto = re.sub(r"[^a-zA-Z0-9_áéíóúñÁÉÍÓÚÑ-]", "", texto)
    return texto


def obtener_resultados_historial_autorizado(rut):
    resultados = TestResult.query.filter(
        TestResult.student_rut == rut,
        TestResult.status == "activo"
    ).order_by(
        TestResult.created_at.asc()
    ).all()

    if not resultados:
        return None, None

    ultimo = resultados[-1]

    if session.get("colegio_logged"):
        school_id = session.get("colegio_school_id")
        if ultimo.school_id != school_id:
            return None, None

    return resultados, ultimo


def generar_pdf_historial(rut):
    resultados, ultimo = obtener_resultados_historial_autorizado(rut)

    if not resultados:
        return None

    analisis = obtener_analisis_historial(resultados)

    colegios_historial = []
    colegios_vistos = set()

    for r in resultados:
        colegio = r.school or "Sin colegio"
        if colegio not in colegios_vistos:
            colegios_historial.append(colegio)
            colegios_vistos.add(colegio)

    os.makedirs("exports/historial", exist_ok=True)

    nombre_alumno = limpiar_nombre_archivo(ultimo.student_name or "alumno")
    rut_archivo = limpiar_nombre_archivo(ultimo.student_rut or "rut")
    fecha = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    pdf_path = f"exports/historial/{nombre_alumno}_{rut_archivo}_historial_DAVO_{fecha}.pdf"

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

    elements.append(Paragraph("Ficha Histórica DAVO", styles["Title"]))
    elements.append(Paragraph("Sistema Integral de Orientación Educacional", styles["Heading2"]))
    elements.append(Paragraph("Desarrollado por David Vargas Orellana", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("1. Datos actuales del estudiante", styles["Heading2"]))

    curso_actual = ultimo.course or "Sin curso"

    if ultimo.section and ultimo.section != "SIN PARALELO":
        curso_actual += f" {ultimo.section}"

    datos_actuales = [
        ["Alumno", ultimo.student_name or ""],
        ["RUT", ultimo.student_rut or ""],
        ["Colegio actual", ultimo.school or ""],
        ["Curso actual", curso_actual],
        ["Fecha de emisión", datetime.now().strftime("%d-%m-%Y")]
    ]

    tabla_datos = Table(datos_actuales, colWidths=[130, 360], hAlign="LEFT")
    tabla_datos.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(tabla_datos)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("2. Resumen histórico DAVO", styles["Heading2"]))

    resumen = [
        [
            "Evaluaciones registradas",
            Paragraph(str(len(resultados)), styles["BodyText"])
        ],
        [
            "Área predominante histórica",
            Paragraph(analisis["area_predominante"], styles["BodyText"])
        ],
        [
            "Área secundaria predominante",
            Paragraph(analisis["area_secundaria_predominante"], styles["BodyText"])
        ],
        [
            "Tendencia DAVO",
            Paragraph(analisis["tendencia"], styles["BodyText"])
        ],
    ]

    tabla_resumen = Table(resumen, colWidths=[170, 320], hAlign="LEFT")
    tabla_resumen.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(tabla_resumen)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(analisis["texto"], styles["BodyText"]))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("3. Historial de establecimientos", styles["Heading2"]))

    for colegio in colegios_historial:
        elements.append(Paragraph(f"• {colegio}", styles["BodyText"]))

    elements.append(Spacer(1, 14))

    elements.append(Paragraph("4. Línea de tiempo DAVO", styles["Heading2"]))

    data = [["Año", "Fecha", "Curso", "Colegio", "Área principal", "Área secundaria", "Ruta sugerida"]]

    for r in resultados:
        curso = r.course or ""

        if r.section and r.section != "SIN PARALELO":
            curso += f" {r.section}"

        data.append([
            r.created_at.strftime("%Y") if r.created_at else "",
            r.created_at.strftime("%d-%m-%Y") if r.created_at else "",
            curso,
            r.school or "",
            r.main_area or "",
            r.secondary_area or "",
            r.suggested_path or "En observación"
        ])

    tabla = Table(data, repeatRows=1, colWidths=[35, 60, 60, 115, 80, 80, 95])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(tabla)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("5. Uso orientador sugerido", styles["Heading2"]))
    elements.append(Paragraph(
        "Esta ficha histórica debe utilizarse como antecedente de apoyo al proceso de orientación. "
        "No reemplaza la entrevista individual, la conversación con la familia ni el análisis pedagógico "
        "del establecimiento. Su propósito es visualizar la evolución de intereses del estudiante a través "
        "del tiempo y apoyar decisiones educativas de manera informada.",
        styles["BodyText"]
    ))

    doc.build(elements)
    return pdf_path




@historial_bp.route("/detalle/<path:rut>")
def detalle(rut):
    if not usuario_autorizado():
        return redirect(url_for("home"))

    resultados = TestResult.query.filter(
        TestResult.student_rut == rut,
        TestResult.status == "activo"
    ).order_by(
        TestResult.created_at.asc()
    ).all()

    if not resultados:
        flash("No se encontró historial para el RUT indicado.", "warning")
        return redirect(url_for("historial.index"))

    ultimo = resultados[-1]

    if session.get("colegio_logged"):
        school_id = session.get("colegio_school_id")

        if ultimo.school_id != school_id:
            flash("No tiene autorización para ver el historial de este estudiante.", "danger")
            return redirect(url_for("historial.index"))

    analisis = obtener_analisis_historial(resultados)

    colegios_historial = []
    colegios_vistos = set()

    for r in resultados:
        colegio = r.school or "Sin colegio"

        if colegio not in colegios_vistos:
            colegios_historial.append(colegio)
            colegios_vistos.add(colegio)

    return render_template(
        "historial/detalle.html",
        resultados=resultados,
        ultimo=ultimo,
        analisis=analisis,
        colegios_historial=colegios_historial
    )



@historial_bp.route("/detalle/<path:rut>/pdf")
def descargar_pdf_historial(rut):
    if not usuario_autorizado():
        return redirect(url_for("home"))

    pdf_path = generar_pdf_historial(rut)

    if not pdf_path:
        flash("No se pudo generar el PDF del historial o no tiene autorización para verlo.", "danger")
        return redirect(url_for("historial.index"))

    return send_file(pdf_path, as_attachment=True)


@historial_bp.route("/exportar_excel")
def exportar_excel_historial():
    if not usuario_autorizado():
        return redirect(url_for("home"))

    query = TestResult.query.filter_by(status="activo")

    # Colegio: exporta solo alumnos cuyo último registro activo pertenece a su colegio.
    # Super administrador: exporta todos.
    if session.get("colegio_logged"):
        school_id = session.get("colegio_school_id")

        # Primero se busca el último registro activo de TODOS los alumnos.
        # Luego se filtra solo a los alumnos cuyo último registro pertenece
        # al colegio que inició sesión.
        todos_los_registros = TestResult.query.filter_by(
            status="activo"
        ).order_by(
            TestResult.student_rut.asc(),
            TestResult.created_at.desc()
        ).all()

        ultimos_por_rut = {}

        for registro in todos_los_registros:
            rut = registro.student_rut

            if not rut:
                continue

            if rut not in ultimos_por_rut:
                ultimos_por_rut[rut] = registro

        ruts_permitidos = [
            rut for rut, ultimo in ultimos_por_rut.items()
            if ultimo.school_id == school_id
        ]

        if not ruts_permitidos:
            flash("No existen estudiantes actuales para exportar.", "warning")
            return redirect(url_for("historial.index"))

        resultados = TestResult.query.filter(
            TestResult.status == "activo",
            TestResult.student_rut.in_(ruts_permitidos)
        ).order_by(
            TestResult.student_name.asc(),
            TestResult.created_at.asc()
        ).all()

    else:
        resultados = query.order_by(
            TestResult.student_name.asc(),
            TestResult.created_at.asc()
        ).all()

    if not resultados:
        flash("No existen registros históricos para exportar.", "warning")
        return redirect(url_for("historial.index"))

    # Hoja 1: historial completo
    historial_data = []

    for r in resultados:
        curso = r.course or ""

        if r.section and r.section != "SIN PARALELO":
            curso += f" {r.section}"

        historial_data.append({
            "RUT": r.student_rut,
            "Alumno": r.student_name,
            "Fecha": r.created_at.strftime("%d-%m-%Y") if r.created_at else "",
            "Año": r.created_at.strftime("%Y") if r.created_at else "",
            "Curso": curso,
            "Colegio donde realizó el test": r.school,
            "Área principal": r.main_area,
            "Área secundaria": r.secondary_area,
            "Ruta sugerida": r.suggested_path or "En observación",
            "Tipo de enseñanza": r.education_type or "",
        })

    # Hoja 2: resumen por alumno
    ruts = sorted(set([r.student_rut for r in resultados if r.student_rut]))
    resumen_data = []

    for rut in ruts:
        historial_alumno = [
            r for r in resultados
            if r.student_rut == rut
        ]

        historial_alumno = sorted(
            historial_alumno,
            key=lambda x: x.created_at
        )

        if not historial_alumno:
            continue

        ultimo = historial_alumno[-1]
        analisis = obtener_analisis_historial(historial_alumno)

        curso_actual = ultimo.course or ""

        if ultimo.section and ultimo.section != "SIN PARALELO":
            curso_actual += f" {ultimo.section}"

        colegios = []
        colegios_vistos = set()

        for item in historial_alumno:
            colegio = item.school or "Sin colegio"

            if colegio not in colegios_vistos:
                colegios.append(colegio)
                colegios_vistos.add(colegio)

        resumen_data.append({
            "RUT": ultimo.student_rut,
            "Alumno": ultimo.student_name,
            "Colegio actual": ultimo.school,
            "Curso actual": curso_actual,
            "Evaluaciones registradas": len(historial_alumno),
            "Área predominante histórica": analisis["area_predominante"],
            "Área secundaria predominante": analisis["area_secundaria_predominante"],
            "Tendencia DAVO": analisis["tendencia"],
            "Colegios en historial": " | ".join(colegios),
        })

    os.makedirs("exports/historial", exist_ok=True)

    if session.get("colegio_logged"):
        nombre_base = session.get("colegio_school_name") or "colegio"
    else:
        nombre_base = "general"

    nombre_base = limpiar_nombre_archivo(nombre_base)
    fecha = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    excel_path = f"exports/historial/historial_DAVO_{nombre_base}_{fecha}.xlsx"

    df_historial = pd.DataFrame(historial_data)
    df_resumen = pd.DataFrame(resumen_data)

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_historial.to_excel(writer, sheet_name="Historial completo", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen por alumno", index=False)

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]

            for column_cells in worksheet.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter

                for cell in column_cells:
                    value = cell.value

                    if value:
                        max_length = max(max_length, len(str(value)))

                worksheet.column_dimensions[column_letter].width = min(max_length + 2, 45)

    return send_file(excel_path, as_attachment=True)

