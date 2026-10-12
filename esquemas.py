"""Esquemas de entrada y de salida."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TipoPoliza = Literal["auto", "hogar", "vida"]
EstadoSiniestro = Literal["abierto", "pagado", "rechazado"]


def _normalizar_nombre(v: str) -> str:
    """Quita espacios sobrantes y pone el nombre con mayúscula inicial."""
    limpio = " ".join(v.split()).title()
    if len(limpio) < 3:
        raise ValueError("el asegurado debe tener al menos 3 caracteres visibles")
    return limpio


# ---------------------------------------------------------------- entrada ---

class SiniestroEntrada(BaseModel):
    fecha: date
    monto: float = Field(gt=0, description="Monto reclamado, en pesos")
    descripcion: str = Field(min_length=3, max_length=200)
    estado: EstadoSiniestro = "abierto"


class PolizaEntrada(BaseModel):
    numero: str = Field(min_length=8, max_length=20, description="Número único de la póliza")
    asegurado: str = Field(min_length=3, max_length=80)
    tipo: TipoPoliza
    prima: float = Field(gt=0, description="Prima anual, en pesos")
    fecha_inicio: date
    fecha_fin: date
    siniestros: list[SiniestroEntrada] = Field(default_factory=list, description="Siniestros ya declarados")

    @field_validator("asegurado")
    @classmethod
    def normalizar_asegurado(cls, v: str) -> str:
        return _normalizar_nombre(v)

    @model_validator(mode="after")
    def fin_posterior_al_inicio(self):
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return self


class PolizaActualizacion(BaseModel):
    """PUT parcial: solo se tocan los campos enviados. Enviar null es 422."""
    asegurado: str | None = Field(default=None, min_length=3, max_length=80)
    tipo: TipoPoliza | None = None
    prima: float | None = Field(default=None, gt=0)
    fecha_fin: date | None = None

    @field_validator("asegurado")
    @classmethod
    def normalizar_asegurado(cls, v: str | None) -> str | None:
        return None if v is None else _normalizar_nombre(v)

    @model_validator(mode="after")
    def sin_nulos_explicitos(self):
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"no se admite null en: {', '.join(sorted(nulos))}")
        return self


class PuntuacionEntrada(BaseModel):
    numero: str = Field(min_length=8, max_length=20)


# ----------------------------------------------------------------- salida ---

class SiniestroSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    poliza_id: int
    fecha: date
    monto: float
    descripcion: str
    estado: str


class SiniestroConPoliza(SiniestroSalida):
    numero_poliza: str


class PolizaSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    asegurado: str
    tipo: str
    prima: float
    fecha_inicio: date
    fecha_fin: date
    siniestros: list[SiniestroSalida]


class ResumenPoliza(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero: str
    n_siniestros: int
    monto_total: float


class PuntuacionSalida(BaseModel):
    numero: str
    puntaje: float = Field(ge=0, le=1)
    alto_riesgo: bool


class PrediccionSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    puntaje: float
    alto_riesgo: bool
    creado_en: datetime


class Salud(BaseModel):
    estado: str
    base_de_datos: str
