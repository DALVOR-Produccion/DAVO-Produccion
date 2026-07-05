def obtener_continuidad_8(main_area, secondary_area):

    mapas = {
        "Técnica": {
            "modalidad": "Técnico Profesional",
            "areas": [
                "Área Industrial",
                "Área Tecnología",
                "Electricidad",
                "Mecánica",
                "Construcción",
                "Programación o Computación"
            ],
            "texto": (
                "El estudiante muestra interés por actividades prácticas, uso de herramientas, "
                "tecnología, construcción o resolución concreta de problemas. Se recomienda "
                "explorar liceos Técnico-Profesionales con especialidades del área industrial "
                "o tecnológica."
            )
        },

        "Científica": {
            "modalidad": "Científico-Humanista",
            "areas": [
                "Ciencias",
                "Matemática",
                "Tecnología",
                "Salud",
                "Investigación escolar"
            ],
            "texto": (
                "El estudiante muestra interés por comprender fenómenos, investigar, analizar "
                "información y resolver problemas. Se recomienda una continuidad Científico-Humanista "
                "con fortalecimiento en ciencias y matemática."
            )
        },

        "Humanista": {
            "modalidad": "Científico-Humanista",
            "areas": [
                "Humanidades",
                "Lenguaje y comunicación",
                "Historia",
                "Ciencias sociales",
                "Educación cívica"
            ],
            "texto": (
                "El estudiante muestra interés por la lectura, escritura, historia, sociedad "
                "y comunicación. Se recomienda una continuidad Científico-Humanista con énfasis "
                "en áreas humanistas y sociales."
            )
        },

        "Artística": {
            "modalidad": "Artística o complementaria",
            "areas": [
                "Artes visuales",
                "Música",
                "Diseño",
                "Teatro",
                "Comunicación audiovisual"
            ],
            "texto": (
                "El estudiante muestra interés por la expresión creativa y artística. Se recomienda "
                "explorar establecimientos o talleres que permitan fortalecer estas habilidades, "
                "junto con una trayectoria educativa que no limite su continuidad futura."
            )
        },

        "Social": {
            "modalidad": "Científico-Humanista o Técnico Profesional según oferta",
            "areas": [
                "Área social",
                "Educación",
                "Salud",
                "Atención de personas",
                "Servicios"
            ],
            "texto": (
                "El estudiante muestra interés por ayudar, escuchar, participar y trabajar con otras personas. "
                "Se recomienda explorar trayectorias que fortalezcan habilidades sociales, liderazgo, "
                "comunicación y servicio."
            )
        }
    }

    principal = mapas.get(main_area)

    if not principal:
        return {
            "modalidad": "Mixto / en observación",
            "areas": ["Exploración general"],
            "texto": (
                "Los resultados muestran intereses diversos. Se recomienda continuar observando "
                "sus preferencias y reforzar espacios de exploración antes de tomar una decisión definitiva."
            )
        }

    return principal
