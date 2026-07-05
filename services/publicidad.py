PUBLICIDAD_8_BASICO = []

PUBLICIDAD_MEDIA = []

PUBLICIDAD_4_MEDIO = []


def obtener_publicidad(curso):
    if curso == "8° Básico":
        return PUBLICIDAD_8_BASICO

    if curso in ["1° Medio", "2° Medio", "3° Medio"]:
        return PUBLICIDAD_MEDIA

    if curso == "4° Medio":
        return PUBLICIDAD_4_MEDIO

    return []
