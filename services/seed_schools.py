import csv
import os

from models import db
from models.school import School


def cargar_colegios_iniciales():
    """
    Carga el catálogo inicial solo cuando la tabla schools está vacía.
    Devuelve la cantidad de colegios insertados.
    """
    if School.query.count() > 0:
        return 0

    ruta_csv = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "colegios_iniciales.csv",
    )

    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(
            f"No se encontró el archivo inicial de colegios: {ruta_csv}"
        )

    colegios = []

    with open(ruta_csv, "r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)

        for fila in lector:
            nombre = (fila.get("name") or "").strip()

            if not nombre:
                continue

            activo = str(fila.get("active", "1")).strip().lower() in {
                "1", "true", "si", "sí", "yes"
            }

            colegios.append(
                School(
                    rbd=(fila.get("rbd") or "").strip() or None,
                    rut=(fila.get("rut") or "").strip() or None,
                    name=nombre,
                    comuna=(fila.get("comuna") or "").strip() or None,
                    region=(fila.get("region") or "").strip() or None,
                    active=activo,
                )
            )

    try:
        db.session.bulk_save_objects(colegios)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return len(colegios)
