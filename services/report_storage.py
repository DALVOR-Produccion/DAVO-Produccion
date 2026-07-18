import os

from models import db
from models.stored_report import StoredReport


def guardar_informe_pdf(result_id, ruta_pdf):
    """
    Guarda o actualiza el PDF asociado a un resultado de test.
    """

    if not os.path.exists(ruta_pdf):
        raise FileNotFoundError(
            f"No existe el archivo PDF: {ruta_pdf}"
        )

    with open(ruta_pdf, "rb") as archivo:
        contenido = archivo.read()

    nombre_archivo = os.path.basename(ruta_pdf)

    informe = StoredReport.query.filter_by(
        result_id=result_id
    ).first()

    if informe is None:

        informe = StoredReport(
            result_id=result_id,
            filename=nombre_archivo,
            mime_type="application/pdf",
            pdf_data=contenido,
            size_bytes=len(contenido)
        )

        db.session.add(informe)

    else:

        informe.filename = nombre_archivo
        informe.mime_type = "application/pdf"
        informe.pdf_data = contenido
        informe.size_bytes = len(contenido)

    db.session.commit()

    return informe


def obtener_informe_pdf(result_id):
    """
    Devuelve el PDF almacenado para un resultado.
    """

    return StoredReport.query.filter_by(
        result_id=result_id
    ).first()


def existe_informe_pdf(result_id):
    """
    Indica si un resultado ya posee un PDF almacenado.
    """

    return (
        StoredReport.query.filter_by(
            result_id=result_id
        ).first()
        is not None
    )


def eliminar_informe_pdf(result_id):
    """
    Elimina el PDF asociado a un resultado.
    """

    informe = StoredReport.query.filter_by(
        result_id=result_id
    ).first()

    if informe is None:
        return False

    db.session.delete(informe)
    db.session.commit()

    return True
