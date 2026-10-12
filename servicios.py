"""Lógica del servicio: consultas, reglas de negocio y puntuación.

Las rutas de main.py solo traducen HTTP <-> estas funciones. Aquí vive la
decisión de la Parte C: cómo se carga cada relación.
"""
import hashlib
import pickle
from datetime import date
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from config import Settings
from esquemas import PolizaActualizacion, PolizaEntrada, SiniestroEntrada
from modelos import Poliza, Prediccion, Siniestro


class NoEncontrada(Exception):
    """La póliza pedida no existe (la ruta la traduce a 404)."""


def firmar(numero: str, secreto: str) -> str:
    return hashlib.sha256(f"{numero}:{secreto}".encode()).hexdigest()


# ------------------------------------------------------------ pólizas ---

def crear_poliza(db: Session, datos: PolizaEntrada, settings: Settings) -> Poliza:
    poliza = Poliza(**datos.model_dump(exclude={"siniestros"}),
                    token_firma=firmar(datos.numero, settings.secreto_firma))
    poliza.siniestros = [Siniestro(**s.model_dump()) for s in datos.siniestros]
    db.add(poliza)
    db.commit()          # IntegrityError (número repetido) sube a la ruta -> 409
    return poliza


def listar_polizas(db: Session) -> list[Poliza]:
    # selectinload: 1 consulta para las pólizas + 1 por cada bloque de ids para los siniestros.
    return list(db.scalars(select(Poliza).options(selectinload(Poliza.siniestros)).order_by(Poliza.id)))


def obtener_poliza(db: Session, id_poliza: int) -> Poliza:
    # lazy, a propósito: 1 consulta por la póliza y 1 más cuando se leen sus siniestros.
    poliza = db.get(Poliza, id_poliza)
    if poliza is None:
        raise NoEncontrada(id_poliza)
    return poliza


def actualizar_poliza(db: Session, id_poliza: int, datos: PolizaActualizacion) -> Poliza:
    poliza = obtener_poliza(db, id_poliza)
    cambios = datos.model_dump(exclude_unset=True)
    fecha_fin = cambios.get("fecha_fin", poliza.fecha_fin)
    if fecha_fin <= poliza.fecha_inicio:
        raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
    for campo, valor in cambios.items():
        setattr(poliza, campo, valor)
    db.commit()
    return poliza


# ---------------------------------------------------------- siniestros ---

def declarar_siniestro(db: Session, id_poliza: int, datos: SiniestroEntrada) -> Siniestro:
    obtener_poliza(db, id_poliza)                     # 404 si no existe
    siniestro = Siniestro(poliza_id=id_poliza, **datos.model_dump())
    db.add(siniestro)
    db.commit()
    return siniestro


def listar_siniestros(db: Session) -> list[Siniestro]:
    # joinedload: muchos-a-uno, el JOIN no multiplica filas -> 1 consulta.
    return list(db.scalars(select(Siniestro).options(joinedload(Siniestro.poliza)).order_by(Siniestro.id)))


# ------------------------------------------------------------- resumen ---

def resumen(db: Session):
    # agregada: la base cuenta y suma; no se traen los siniestros a Python.
    consulta = (
        select(Poliza.numero,
               func.count(Siniestro.id).label("n_siniestros"),
               func.round(func.coalesce(func.sum(Siniestro.monto), 0), 2).label("monto_total"))
        .outerjoin(Siniestro, Siniestro.poliza_id == Poliza.id)
        .group_by(Poliza.id)
        .order_by(Poliza.id)
    )
    return db.execute(consulta).all()


# --------------------------------------------------------- puntuación ---

@lru_cache
def cargar_modelo(ruta: str):
    with open(ruta, "rb") as fh:
        return pickle.load(fh)


def puntuar(db: Session, numero: str, settings: Settings) -> Prediccion:
    fila = db.execute(
        select(Poliza, func.count(Siniestro.id), func.coalesce(func.sum(Siniestro.monto), 0))
        .outerjoin(Siniestro, Siniestro.poliza_id == Poliza.id)
        .where(Poliza.numero == numero)
        .group_by(Poliza.id)
    ).first()
    if fila is None:
        raise NoEncontrada(numero)
    poliza, n_siniestros, monto_total = fila
    rasgos = [[poliza.prima, n_siniestros, monto_total, (date.today() - poliza.fecha_inicio).days]]
    puntaje = float(cargar_modelo(settings.ruta_modelo).predict_proba(rasgos)[0][1])
    prediccion = Prediccion(poliza=poliza, puntaje=puntaje,
                            alto_riesgo=puntaje > settings.umbral_alto_riesgo)
    db.add(prediccion)
    db.commit()
    return prediccion


def listar_predicciones(db: Session) -> list[Prediccion]:
    return list(db.scalars(select(Prediccion).options(joinedload(Prediccion.poliza)).order_by(Prediccion.id)))
