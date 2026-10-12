# ---------- Etapa 1: construir el entorno con las dependencias ----------
FROM python:3.11.9-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -r requirements.txt

# ---------- Etapa 2: imagen final, solo lo necesario para correr ----------
FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATABASE_URL=sqlite:////app/data/polizas.db

# Usuario sin privilegios: el proceso no corre como root.
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/data && chown appuser:appuser /app/data

USER appuser
EXPOSE 8000

# La imagen slim no trae curl: el chequeo usa Python.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

# Crea/actualiza el esquema y arranca. Sin --reload; 0.0.0.0 para que responda desde el host.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000"]
