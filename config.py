"""Configuración del servicio.

Todo lo que cambia entre entornos (ruta de la base, secretos, umbrales) se lee
de variables de entorno o de un archivo `.env` que NO se versiona. Los valores
por defecto solo sirven para desarrollo local.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # DATABASE_URL: la leen la app (database.py) y Alembic (alembic/env.py).
    database_url: str = "sqlite:///./polizas.db"
    # Secreto con el que se firma cada póliza. El valor por defecto NO es un
    # secreto: solo permite arrancar en desarrollo. En producción se inyecta.
    secreto_firma: str = "solo-desarrollo-no-usar-en-produccion"
    clave_api_reaseguro: str | None = None
    ruta_modelo: str = "modelo.pkl"
    umbral_alto_riesgo: float = Field(default=0.6, ge=0, le=1)


@lru_cache
def get_settings() -> Settings:
    """Una sola instancia por proceso; se inyecta con Depends(get_settings)."""
    return Settings()
