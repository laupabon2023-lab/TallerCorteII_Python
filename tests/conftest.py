"""Fixtures compartidas por los tests propios (no por test_contrato.py, que trae las suyas).

Cada test recibe un cliente cuya sesión apunta a una base SQLite NUEVA en tmp_path:
la base de la aplicación nunca se toca y dos corridas seguidas dan lo mismo.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

import database  # noqa: E402
import modelos  # noqa: E402,F401
from main import app  # noqa: E402


@pytest.fixture
def cliente(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}",
                           connect_args={"check_same_thread": False})
    database.Base.metadata.create_all(engine)       # solo en la base temporal del test
    Sesion = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    previo = app.dependency_overrides.get(database.get_db)
    app.dependency_overrides[database.get_db] = _get_db
    with TestClient(app) as c:
        yield c
    if previo is None:
        app.dependency_overrides.pop(database.get_db, None)
    else:
        app.dependency_overrides[database.get_db] = previo
    engine.dispose()
