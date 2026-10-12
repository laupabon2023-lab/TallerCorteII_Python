# polizas-api

Servicio de gestión de pólizas de la Aseguradora Santo Tomás. Registra pólizas
y los siniestros que se les declaran, resume la cartera y puntúa el riesgo de
cada póliza con un modelo (`modelo.pkl`), guardando cada predicción.

FastAPI · SQLAlchemy 2.0 · Alembic · pytest · Docker. Requiere Python 3.11 o superior.

## Arranque local (uvicorn)

```bash
python -m venv venv
source venv/bin/activate          # Windows Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env              # ajuste SECRETO_FIRMA; .env no se versiona
alembic upgrade head              # crea el esquema en la base de DATABASE_URL
uvicorn main:app --host 127.0.0.1 --port 8000
```

Compruebe que responde: `curl localhost:8000/health` → `{"estado":"ok","base_de_datos":"ok"}`.
Durante el desarrollo puede añadir `--reload`; en producción y en el contenedor no se usa.

La base de datos **no** viene en el repositorio: la crea `alembic upgrade head` en la ruta
que diga `DATABASE_URL` (por defecto `polizas.db`).

## Arranque en contenedor (Docker)

```bash
docker build -t polizas-api .
docker run -d --name polizas -p 8000:8000 polizas-api
curl localhost:8000/health
```

La imagen no lleva `.env` ni base de datos: al arrancar, el contenedor ejecuta
`alembic upgrade head` y crea `/app/data/polizas.db` dentro del contenedor.
Para conservar los datos aunque se borre el contenedor, monte un volumen:

```bash
docker run -d --name polizas -p 8000:8000 -v polizas-datos:/app/data polizas-api
```

Para producción, pase el secreto como variable: `-e SECRETO_FIRMA=...`.

## Configuración

| Variable | Por defecto | Qué es |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./polizas.db` | Base de datos; la leen la app y Alembic |
| `SECRETO_FIRMA` | valor de desarrollo | Secreto para firmar las pólizas |
| `CLAVE_API_REASEGURO` | vacío | Clave del servicio de reaseguro |
| `RUTA_MODELO` | `modelo.pkl` | Modelo serializado |
| `UMBRAL_ALTO_RIESGO` | `0.6` | Puntaje a partir del cual una póliza es de alto riesgo |

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | Estado del servicio y de la base de datos |
| POST | `/polizas` | Crea una póliza, con sus siniestros si ya tiene (201 · 409 · 422) |
| GET | `/polizas` | Lista las pólizas con sus siniestros |
| GET | `/polizas/{id}` | Consulta una póliza (404 si no existe) |
| PUT | `/polizas/{id}` | Actualiza solo los campos enviados (404 · 422) |
| POST | `/polizas/{id}/siniestros` | Declara un siniestro (201 · 404 · 422) |
| GET | `/siniestros` | Lista los siniestros con el número de su póliza |
| GET | `/resumen` | Número de siniestros y monto total por póliza |
| POST | `/score` | Puntúa el riesgo de una póliza y guarda la predicción (404 · 422) |
| GET | `/predicciones` | Histórico de predicciones con el número de la póliza |

### Ejemplo

```bash
curl -X POST localhost:8000/polizas \
  -H "Content-Type: application/json" \
  -d '{"numero": "POL-2026-09001", "asegurado": "Ana Rueda", "tipo": "auto", "prima": 1250000,
       "fecha_inicio": "2026-01-15", "fecha_fin": "2027-01-14"}'

curl -X POST localhost:8000/score -H "Content-Type: application/json" -d '{"numero": "POL-2026-09001"}'
```

## Pruebas

```bash
pytest
```

Los tests propios (`tests/test_api.py`, `tests/test_ia_corregido.py`) usan una base temporal
por test mediante `app.dependency_overrides`: no tocan la base de la aplicación.

## Utilidades

- `sembrar_datos.py` crea pólizas de ejemplo a través de la API.
- `contar_consultas.py` cuenta las sentencias SQL de cada endpoint y escribe `CONSULTAS.csv`.
