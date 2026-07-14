import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

database_url = os.getenv("DATABASE_URL")

class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "davo_clave_secreta_inicial_2026"
    )

    SQLALCHEMY_DATABASE_URI = (
        database_url
        if database_url
        else f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
