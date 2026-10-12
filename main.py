"""
polizas-api — Gestión de pólizas y siniestros.
Aseguradora Santo Tomás · prototipo interno.

Las rutas solo hablan HTTP: validan la entrada con los esquemas, piden la sesión
y la configuración con Depends y delegan en servicios.py.
"""
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

import servicios
from config import Settings, get_settings
from database import get_db
from esquemas import (PolizaActualizacion, PolizaEntrada, PolizaSalida, PrediccionSalida,
                      PuntuacionEntrada, PuntuacionSalida, ResumenPoliza, Salud,
                      SiniestroConPoliza, SiniestroEntrada, SiniestroSalida)

app = FastAPI(title="Pólizas API", version="1.0.0")


def _no_existe(que) -> HTTPException:
    return HTTPException(status_code=404, detail=f"no existe la póliza {que}")


@app.get("/health", response_model=Salud)
def salud(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="la base de datos no responde")
    return Salud(estado="ok", base_de_datos="ok")


@app.post("/polizas", response_model=PolizaSalida, status_code=201)
def crear_poliza(datos: PolizaEntrada, db: Session = Depends(get_db),
                 settings: Settings = Depends(get_settings)):
    try:
        return servicios.crear_poliza(db, datos, settings)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"ya existe la póliza {datos.numero}")


@app.get("/polizas", response_model=list[PolizaSalida])
def listar_polizas(db: Session = Depends(get_db)):
    return servicios.listar_polizas(db)


@app.get("/polizas/{id_poliza}", response_model=PolizaSalida)
def obtener_poliza(id_poliza: int, db: Session = Depends(get_db)):
    try:
        return servicios.obtener_poliza(db, id_poliza)
    except servicios.NoEncontrada:
        raise _no_existe(id_poliza)


@app.put("/polizas/{id_poliza}", response_model=PolizaSalida)
def actualizar_poliza(id_poliza: int, datos: PolizaActualizacion, db: Session = Depends(get_db)):
    try:
        return servicios.actualizar_poliza(db, id_poliza, datos)
    except servicios.NoEncontrada:
        raise _no_existe(id_poliza)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/polizas/{id_poliza}/siniestros", response_model=SiniestroSalida, status_code=201)
def declarar_siniestro(id_poliza: int, datos: SiniestroEntrada, db: Session = Depends(get_db)):
    try:
        return servicios.declarar_siniestro(db, id_poliza, datos)
    except servicios.NoEncontrada:
        raise _no_existe(id_poliza)


@app.get("/siniestros", response_model=list[SiniestroConPoliza])
def listar_siniestros(db: Session = Depends(get_db)):
    return servicios.listar_siniestros(db)


@app.get("/resumen", response_model=list[ResumenPoliza])
def resumen(db: Session = Depends(get_db)):
    return servicios.resumen(db)


@app.post("/score", response_model=PuntuacionSalida)
def puntuar(datos: PuntuacionEntrada, db: Session = Depends(get_db),
            settings: Settings = Depends(get_settings)):
    try:
        prediccion = servicios.puntuar(db, datos.numero, settings)
    except servicios.NoEncontrada:
        raise _no_existe(datos.numero)
    return PuntuacionSalida(numero=datos.numero, puntaje=round(prediccion.puntaje, 4),
                            alto_riesgo=prediccion.alto_riesgo)


@app.get("/predicciones", response_model=list[PrediccionSalida])
def listar_predicciones(db: Session = Depends(get_db)):
    return servicios.listar_predicciones(db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
