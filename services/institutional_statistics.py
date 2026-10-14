from services.basic_results import category_area
from collections import Counter, defaultdict
from datetime import datetime


AREAS = ["Científica", "Humanista", "Artística", "Técnica", "Social"]


def normalizar_area(area):
    equivalencias = {
        "Técnico-Práctica": "Técnica",
        "Técnico-Práctico": "Técnica",
        "Técnica": "Técnica",
    }
    return equivalencias.get(area, area or "Sin área")


def nivel_del_curso(curso):
    if curso in {"6° Básico", "7° Básico", "8° Básico"}:
        return "basica"
    if curso in {"1° Medio", "2° Medio", "3° Medio", "4° Medio"}:
        return "media"
    return "otro"


def ultimo_resultado_por_estudiante(resultados):
    """Obtiene la fotografía más reciente de cada estudiante en el periodo."""
    ultimos = {}
    for resultado in sorted(
        resultados,
        key=lambda r: (r.created_at or datetime.min, r.id or 0),
        reverse=True,
    ):
        if resultado.student_rut and resultado.student_rut not in ultimos:
            ultimos[resultado.student_rut] = resultado
    return list(ultimos.values())


def distribucion_areas(resultados, atributo):
    contador = Counter(
        normalizar_area(category_area(resultado, atributo))
        for resultado in resultados
    )
    total = len(resultados)
    distribucion = []

    # Both series use the same labels, so tables cannot pair unrelated categories.
    labels = {normalizar_area(category_area(result, attr))
              for result in resultados for attr in ('main_area', 'secondary_area')}
    for area in AREAS + sorted(labels - set(AREAS)):
        cantidad = contador.get(area, 0)
        porcentaje = round((cantidad / total) * 100, 1) if total else 0
        distribucion.append({
            "area": area,
            "cantidad": cantidad,
            "porcentaje": porcentaje,
        })

    return distribucion


def area_predominante(distribucion):
    if not distribucion or not any(item["cantidad"] for item in distribucion):
        return "Sin datos"
    mayor = max(item["cantidad"] for item in distribucion)
    areas = [item["area"] for item in distribucion if item["cantidad"] == mayor]
    return ", ".join(areas)


def resumen_por_curso(resultados):
    filas = defaultdict(lambda: {
        "ruts": set(),
        "principales": Counter(),
        "secundarias": Counter(),
    })

    for resultado in resultados:
        curso = resultado.course or "Sin curso"
        paralelo = resultado.section or "SIN PARALELO"
        etiqueta = curso if paralelo == "SIN PARALELO" else f"{curso} {paralelo}"
        fila = filas[(curso, paralelo, etiqueta)]
        if resultado.student_rut:
            fila["ruts"].add(resultado.student_rut)
        fila["principales"][normalizar_area(category_area(resultado, "main_area"))] += 1
        fila["secundarias"][normalizar_area(category_area(resultado, "secondary_area"))] += 1

    orden = {
        "6° Básico": 1,
        "7° Básico": 2,
        "8° Básico": 3,
        "1° Medio": 4,
        "2° Medio": 5,
        "3° Medio": 6,
        "4° Medio": 7,
    }
    resultado = []

    for (curso, paralelo, etiqueta), datos in sorted(
        filas.items(),
        key=lambda item: (orden.get(item[0][0], 99), item[0][1]),
    ):
        resultado.append({
            "curso": curso,
            "paralelo": paralelo,
            "etiqueta": etiqueta,
            "total": len(datos["ruts"]),
            "sin_principal_unica": sum(v for k,v in datos["principales"].items() if k not in AREAS),
            "principales": {area: datos["principales"].get(area, 0) for area in AREAS + sorted((set(datos["principales"]) | set(datos["secundarias"])) - set(AREAS))},
            "secundarias": {area: datos["secundarias"].get(area, 0) for area in AREAS + sorted((set(datos["principales"]) | set(datos["secundarias"])) - set(AREAS))},
        })

    return resultado


def calcular_dashboard_institucional(resultados):
    fotografia = ultimo_resultado_por_estudiante(resultados)
    basica = [r for r in fotografia if nivel_del_curso(r.course) == "basica"]
    media = [r for r in fotografia if nivel_del_curso(r.course) == "media"]
    principales = distribucion_areas(fotografia, "main_area")
    secundarias = distribucion_areas(fotografia, "secondary_area")

    return {
        "total_evaluaciones": len(resultados),
        "total_estudiantes": len(fotografia),
        "total_basica": len(basica),
        "total_media": len(media),
        "tiene_basica": bool(basica),
        "tiene_media": bool(media),
        "principales": principales,
        "secundarias": secundarias,
        "principal_predominante": area_predominante(principales),
        "secundaria_predominante": area_predominante(secundarias),
        "por_curso": resumen_por_curso(fotografia),
        "basica_principales": distribucion_areas(basica, "main_area"),
        "media_principales": distribucion_areas(media, "main_area"),
    }


def _acciones_para_areas(areas):
    acciones = {
        "Científica": (
            "Fortalecer experiencias de investigación, experimentación, ciencias, "
            "tecnología y resolución de problemas."
        ),
        "Humanista": (
            "Promover lectura, escritura, debate, análisis de actualidad, historia "
            "y comprensión de fenómenos sociales."
        ),
        "Artística": (
            "Ofrecer espacios de creación visual, música, expresión corporal, diseño "
            "y participación en actividades culturales."
        ),
        "Técnica": (
            "Incorporar talleres prácticos, tecnología, robótica, herramientas, "
            "oficios y exploración de alternativas Técnico-Profesionales."
        ),
        "Social": (
            "Desarrollar actividades de colaboración, liderazgo, servicio, tutoría, "
            "comunicación y trabajo con la comunidad."
        ),
    }
    return [acciones.get(area, 'Ofrecer experiencias variadas sin asignar al estudiante a una única área; revisar sus intereses compartidos o cercanos.') for area in areas]


def calcular_ficha_curso(resultados):
    fotografia = ultimo_resultado_por_estudiante(resultados)
    principales = distribucion_areas(fotografia, "main_area")
    secundarias = distribucion_areas(fotografia, "secondary_area")
    principal = area_predominante(principales)
    secundaria = area_predominante(secundarias)

    principales_maximas = []
    if fotografia:
        mayor = max(item["cantidad"] for item in principales)
        principales_maximas = [
            item["area"] for item in principales
            if item["cantidad"] == mayor and mayor > 0
        ]

    if not fotografia:
        interpretacion = "No existen resultados suficientes para interpretar este curso."
    elif any(area not in AREAS for area in principales_maximas):
        interpretacion = ('Entre las categorías más frecuentes hay resultados sin área principal única: '
                          + principal + '. Esto no es una nueva área vocacional. Ofrecer exploración variada y revisar cada perfil.')
    elif len(principales_maximas) > 1:
        interpretacion = (
            "El curso presenta un perfil de intereses diversificado, sin una única "
            f"área claramente predominante. Las áreas con mayor presencia son {principal}. "
            "Esto sugiere ofrecer oportunidades variadas de exploración y evitar una "
            "interpretación única del grupo."
        )
    else:
        interpretacion = (
            f"En el curso se observa una mayor presencia relativa del área {principal}, "
            f"acompañada por el área secundaria {secundaria}. Este resultado describe "
            "tendencias grupales y debe utilizarse para planificar oportunidades de "
            "exploración, sin asignar una orientación definitiva a sus estudiantes."
        )

    return {
        "total_evaluaciones": len(resultados),
        "total_estudiantes": len(fotografia),
        "principales": principales,
        "secundarias": secundarias,
        "principal_predominante": principal,
        "secundaria_predominante": secundaria,
        "interpretacion": interpretacion,
        "acciones": _acciones_para_areas(principales_maximas),
    }
