"""Pruebas propias del servicio, aisladas con dependency_overrides (ver conftest.py).

    pytest tests/test_api.py
"""
POLIZA = {
    "numero": "POL-TEST-00001",
    "asegurado": "Prueba Interna",
    "tipo": "auto",
    "prima": 1_000_000,
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-12-31",
}


def test_crear_poliza(cliente):
    r = cliente.post("/polizas", json=POLIZA)
    assert r.status_code == 201
    assert r.json()["numero"] == POLIZA["numero"]


def test_listar_polizas(cliente):
    cliente.post("/polizas", json=POLIZA)
    r = cliente.get("/polizas")
    assert r.status_code == 200
    assert [p["numero"] for p in r.json()] == [POLIZA["numero"]]


def test_health_indica_la_base(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok", "base_de_datos": "ok"}


def test_resumen_cuenta_y_suma_por_poliza(cliente):
    cliente.post("/polizas", json={**POLIZA, "siniestros": [
        {"fecha": "2026-02-01", "monto": 100.5, "descripcion": "Rotura de vidrios"},
        {"fecha": "2026-03-01", "monto": 200.25, "descripcion": "Robo de equipo"}]})
    cliente.post("/polizas", json={**POLIZA, "numero": "POL-TEST-00002"})
    assert cliente.get("/resumen").json() == [
        {"numero": "POL-TEST-00001", "n_siniestros": 2, "monto_total": 300.75},
        {"numero": "POL-TEST-00002", "n_siniestros": 0, "monto_total": 0.0}]
