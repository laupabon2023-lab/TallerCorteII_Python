"""Conexión a la base de datos y sesión por petición."""
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import get_settings


class Base(DeclarativeBase):
    pass


def crear_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def _activar_claves_foraneas(dbapi_conn, _registro):
    """SQLite trae las claves foráneas APAGADAS: se encienden en cada conexión."""
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = crear_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """Una sesión nueva por petición; se cierra siempre, pase lo que pase."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
