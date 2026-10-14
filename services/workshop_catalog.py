"""Banco privado: la vista pública recibe exclusivamente campos de vista previa."""
import json
from functools import lru_cache
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
from services.basic_results import AREAS, COURSES, profile


def today_chile():
    return datetime.now(ZoneInfo('America/Santiago')).date()


@lru_cache(maxsize=1)
def bank():
    return json.loads((Path(__file__).resolve().parent.parent / 'data' / 'workshops.json').read_text(encoding='utf-8'))


def workshop(identifier):
    return next((w for w in bank()['workshops'] if w['id'] == identifier), None)


def previews(course='', areas=()):
    fields = ('id', 'course', 'grade', 'area', 'name', 'description', 'objective', 'sessions', 'minutes', 'resources')
    return [{key: w[key] for key in fields} for w in bank()['workshops']
            if (not course or w['course'] == course) and (not areas or w['area'] in areas)]


def group_recommendations(results):
    """Cada alumno cuenta una vez en su máximo; empates se muestran por separado."""
    first, shared, complementary = Counter(), Counter(), Counter()
    without = 0
    for result in results:
        if result.course not in COURSES:
            continue
        analysis = profile(result)
        if len(analysis['top']) == 1:
            first.update(analysis['top'])
            complementary.update(a for a in analysis['considered'] if a not in analysis['top'])
        elif analysis['top']:
            shared.update(analysis['top'])
        else:
            without += 1
    rows = [dict(area=a, first=first[a], shared=shared[a], complementary=complementary[a]) for a in AREAS]
    rows.sort(key=lambda row: (-row['first'], -row['shared'], -row['complementary'], AREAS.index(row['area'])))
    return dict(rows=rows, total=len(results), without=without)
