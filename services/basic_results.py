"""Descriptive scoring for the basic yes/no instrument; no psychometric cut-off."""
import json
from datetime import datetime

AREAS = ('Científica', 'Humanista', 'Artística', 'Técnica', 'Social')
COURSES = ('6° Básico', '7° Básico', '8° Básico')
FIELDS = ('score_cientifica', 'score_humanista', 'score_artistica', 'score_tecnica', 'score_social')
SCORING_VERSION = 'basico-empates-v1'


def analyze_scores(scores):
    scores = {area: int(scores.get(area, 0) or 0) for area in AREAS}
    maximum = max(scores.values())
    ordered = sorted(AREAS, key=lambda area: -scores[area])
    top = [area for area in AREAS if scores[area] == maximum]
    secondary = []
    if maximum == 0:
        kind, main = 'no_interest', 'Sin predominio'
        considered = []
        text = 'No se registraron respuestas afirmativas. No se identifica un área predominante; esto no significa que el estudiante carezca de intereses. Conviene conversar y ofrecer experiencias variadas.'
    elif len(top) == len(AREAS):
        kind, main = 'distributed', 'Intereses distribuidos'
        considered = list(AREAS)
        text = 'Todas las áreas obtuvieron la misma puntuación positiva. Se observan intereses distribuidos, sin un área predominante.'
    elif len(top) > 1:
        kind, main = 'tie', 'Intereses compartidos'
        considered = top
        text = 'Hay un empate en la puntuación más alta entre las áreas ' + ', '.join(top) + '. Ninguna de ellas debe presentarse como única área principal.'
    else:
        other_max = max(value for area, value in scores.items() if area not in top)
        secondary = [area for area in AREAS if area not in top and scores[area] == other_max and other_max > 0]
        if maximum - other_max == 1:
            kind, main = 'close', 'Puntuaciones cercanas'
            considered = [area for area in ordered if scores[area] > 0 and maximum - scores[area] <= 1]
            text = ('El área ' + top[0] + ' obtuvo la puntuación más alta, con solo un punto de diferencia respecto de la siguiente puntuación. Las áreas ' + ', '.join(considered) + ' muestran intereses cercanos y pueden complementarse. Esta diferencia pequeña no demuestra una preferencia firme ni define una vocación o continuidad educativa.')
            if other_max == 0:
                text = ('Solo se registró una respuesta afirmativa en el área ' + top[0] + '. La diferencia es de un punto respecto de las áreas sin respuestas afirmativas. No hay información suficiente para afirmar un predominio claro; conviene ampliar la exploración.')
        else:
            kind, main = 'leading', top[0]
            considered = top
            text = 'La puntuación más alta corresponde al área ' + top[0] + '. Es una señal de interés observado, no una decisión vocacional ni una medida de capacidad.'
    # A tie at the top has no arbitrary second place. Include tied runners-up only for a unique top.
    second = secondary[0] if len(secondary) == 1 else ('Intereses secundarios compartidos' if secondary else 'Sin área secundaria diferenciada')
    main_display = top[0] if kind == 'close' else main + (': ' + ', '.join(considered) if kind in ('tie', 'distributed') else '')
    secondary_display = second + (': ' + ', '.join(secondary) if len(secondary) > 1 else '')
    return dict(kind=kind, main=main, secondary=second, main_display=main_display,
                secondary_display=secondary_display, top=top if maximum else [],
                considered=considered, secondary_areas=secondary, scores=scores,
                interpretation=text + ' El sistema entrega información para apoyar al estudiante, su familia y los profesionales; no decide por el estudiante.')


def profile(result):
    return analyze_scores(dict(zip(AREAS, [getattr(result, field, 0) for field in FIELDS])))


def display_area(result, attribute):
    if result.course not in COURSES:
        return getattr(result, attribute, None) or 'Sin área'
    return profile(result)['main_display' if attribute == 'main_area' else 'secondary_display']


def category_area(result, attribute):
    if result.course not in COURSES:
        return getattr(result, attribute, None) or 'Sin área'
    return profile(result)['main' if attribute == 'main_area' else 'secondary']


def interpretation(result):
    return profile(result)['interpretation']


def workshops(result, lookup):
    areas = profile(result)['considered']
    if not areas:
        return 'Ofrecer experiencias variadas de exploración y conversar sobre lo que le gustaría conocer al estudiante.'
    return ' '.join(area + ': ' + lookup(area) for area in areas)


def continuity(result):
    return continuity_from_scores(profile(result))


def continuity_from_scores(analysis):
    from services.orientation_maps import obtener_continuidad_8
    if analysis['kind'] == 'leading':
        return obtener_continuidad_8(analysis['main'], analysis['secondary'])
    areas = []
    for area in analysis['considered']:
        for line in obtener_continuidad_8(area, None)['areas']:
            if line not in areas:
                areas.append(line)
    return dict(modalidad='Explorar alternativas, sin modalidad única',
                areas=areas or ['Exploración general'],
                texto='Estos resultados no permiten sugerir una única modalidad de enseñanza media. Explorar alternativas junto al estudiante, su familia y el establecimiento, considerando sus experiencias y la oferta disponible.')


def history_text(results):
    results = sorted(results, key=lambda r: (r.created_at or datetime.min, r.id or 0))
    if not results:
        return 'No existen evaluaciones registradas.'
    lines = []
    analyses = []
    for result in results:
        analysis = profile(result)
        analyses.append(analysis)
        date = result.created_at.strftime('%d-%m-%Y') if result.created_at else 'Sin fecha'
        lines.append(f"{date} - {result.course}: {analysis['main_display']}.")
    is_eighth = results[-1].course == '8° Básico'
    if len(results) == 1 and is_eighth:
        message = ('No existen evaluaciones previas registradas que permitan comparar la evolución de sus intereses. '
                   'El resultado actual aporta antecedentes para orientar su continuidad en enseñanza media.')
    elif len(results) == 1:
        message = 'Es un registro inicial; aún no permite evaluar continuidad o cambios.'
    elif all(a['kind'] == 'leading' for a in analyses) and len({a['main'] for a in analyses}) == 1:
        message = 'La misma área obtuvo la puntuación más alta en las evaluaciones registradas. Es una continuidad descriptiva, no una confirmación de una vocación definitiva.'
    else:
        message = 'Se observan cambios, intereses compartidos o puntuaciones cercanas entre las evaluaciones. No corresponde forzar una única trayectoria. Los intereses pueden cambiar durante estos años; conviene conversar sobre las experiencias del estudiante.'
    if len(analyses) > 1:
        shared = set(analyses[0]['considered'])
        for analysis in analyses[1:]:
            shared.intersection_update(analysis['considered'])
        if shared and not all(a['kind'] == 'leading' for a in analyses):
            names = ', '.join(area for area in AREAS if area in shared)
            message = (f'Continuidad observada: {names} aparece entre las áreas de mayor puntuación o cercanas al máximo en las {len(analyses)} evaluaciones registradas. '
                       'Las áreas que acompañan este interés pueden mantenerse o cambiar. Esta continuidad no determina una vocación definitiva. ' + message)
    if is_eighth:
        available = {r.course for r in results}
        if len(results) > 1:
            present = ', '.join(c for c in COURSES if c in available)
            if all(c in available for c in COURSES):
                context = 'Historial completo de enseñanza básica: existen evaluaciones de 6°, 7° y 8° básico. '
            else:
                missing = ', '.join(c for c in COURSES if c not in available)
                context = (f'Historial parcial: existen evaluaciones de {present}. '
                           f'No hay registros de {missing}; la comparación utiliza únicamente los antecedentes disponibles. ')
            message = context + message
        message += (' Se recomienda complementar la orientación de continuidad en enseñanza media con sus experiencias, '
                    'preferencias, antecedentes escolares y las alternativas educativas disponibles, junto al estudiante, '
                    'su familia y el orientador.')
    else:
        message += ' Los cuestionarios se adaptan a cada curso. El seguimiento permite observar intereses que se mantienen o cambian y apoyar su exploración durante la enseñanza básica.'
    return '\n'.join(lines) + '\n\n' + message


def score_rows(result):
    """Raw points ordered by score; maximum is known for versioned basic banks."""
    maximum = 4 if result.course in COURSES[:2] else (5 if result.course == COURSES[2] else None)
    try:
        version = json.loads(result.answers or '{}').get('_instrument_version')
    except (ValueError, AttributeError):
        version = None
    if result.course in COURSES and version is None:
        maximum = None
    scores = {area: int(getattr(result, field, 0) or 0) for area,field in zip(AREAS,FIELDS)}
    return [dict(area=area, points=scores[area], maximum=maximum)
            for area in sorted(AREAS, key=lambda a: -scores[a])]
