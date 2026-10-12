"""
Complemento de la Parte C: cuenta las consultas de las estrategias que NO quedaron
en el código, para justificar la decisión con números propios.

    python comparar_estrategias.py

Igual que contar_consultas.py: base TEMPORAL (DATABASE_URL antes de importar la app),
siembra por la API 10 y luego 2000 pólizas con 3 siniestros, y cuenta cada sentencia SQL.
Cada alternativa sustituye por un momento la función de servicios.py y se restaura.
No modifica ningún archivo del servicio.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

raiz = Path(__file__).parent.resolve()
os.chdir(raiz)
sys.path.insert(0, str(raiz))
db = Path(tempfile.mkdtemp(prefix="comparar-")) / "comparar.db"
os.environ["DATABASE_URL"] = f"sqlite:///{db}"
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, capture_output=True)

from sqlalchemy import event, select  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import joinedload, selectinload  # noqa: E402

contador = {"n": 0}


@event.listens_for(Engine, "before_cursor_execute")
def _contar(*_):
    contador["n"] += 1


from fastapi.testclient import TestClient  # noqa: E402

import servicios  # noqa: E402
from main import app  # noqa: E402
from modelos import Poliza, Siniestro  # noqa: E402
from sembrar_datos import sembrar  # noqa: E402


def resumen_en_python(db):
    polizas = db.scalars(select(Poliza).options(selectinload(Poliza.siniestros)).order_by(Poliza.id))
    return [SimpleNamespace(numero=p.numero, n_siniestros=len(p.siniestros),
                            monto_total=round(sum(s.monto for s in p.siniestros), 2)) for p in polizas]


ALTERNATIVAS = [
    ("/polizas", "lazy", "listar_polizas", "/polizas",
     lambda db: list(db.scalars(select(Poliza).order_by(Poliza.id)))),
    ("/polizas", "joinedload", "listar_polizas", "/polizas",
     lambda db: list(db.scalars(select(Poliza).options(joinedload(Poliza.siniestros))
                                .order_by(Poliza.id)).unique())),
    ("/polizas/{id}", "selectinload", "obtener_poliza", "/polizas/1",
     lambda db, i: db.scalar(select(Poliza).options(selectinload(Poliza.siniestros)).where(Poliza.id == i))),
    ("/polizas/{id}", "joinedload", "obtener_poliza", "/polizas/1",
     lambda db, i: db.scalar(select(Poliza).options(joinedload(Poliza.siniestros)).where(Poliza.id == i))),
    ("/siniestros", "lazy", "listar_siniestros", "/siniestros",
     lambda db: list(db.scalars(select(Siniestro).order_by(Siniestro.id)))),
    ("/siniestros", "selectinload", "listar_siniestros", "/siniestros",
     lambda db: list(db.scalars(select(Siniestro).options(selectinload(Siniestro.poliza)).order_by(Siniestro.id)))),
    ("/resumen", "selectinload (suma en Python)", "resumen", "/resumen", resumen_en_python),
]

with TestClient(app) as cliente:
    sembradas = 0
    for n in (10, 2000):
        sembrar(cliente, n - sembradas, 3, prefijo="POL-A", desde=sembradas + 1)
        sembradas = n
        for endpoint, estrategia, funcion, ruta, alternativa in ALTERNATIVAS:
            original = getattr(servicios, funcion)
            setattr(servicios, funcion, alternativa)
            try:
                cliente.get(ruta)                       # calentamiento
                contador["n"] = 0
                t0 = time.perf_counter()
                r = cliente.get(ruta)
                ms = (time.perf_counter() - t0) * 1000
            finally:
                setattr(servicios, funcion, original)
            print(f"  {endpoint:<14} {estrategia:<30} n={n:<5} consultas {contador['n']:>5}  "
                  f"{ms:8.1f} ms  (HTTP {r.status_code})")
