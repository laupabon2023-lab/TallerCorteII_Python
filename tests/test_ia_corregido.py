"""
Batería corregida de ia_tests_propuesta.py (Parte D).

Qué cambia frente a la original:
  1. Cada test afirma UN resultado esperado (201, 404, 409, 422), nunca «A o B».
  2. El aislamiento es real: la fixture `cliente` de conftest.py sustituye
     database.get_db (la dependencia que usan las rutas) por una sesión sobre
     una base nueva en tmp_path. La base de la aplicación no se toca.
  3. Los datos son fijos y explícitos: sin random, el mismo test hace siempre
     lo mismo, y los casos inválidos se prueban a propósito.
  4. Lo que se escribe se vuelve a leer: tras cada POST/PUT se consulta de nuevo
     para comprobar que quedó persistido (detecta un commit que falta).

    pytest tests/test_ia_corregido.py -v
"""
import pytest

SINIESTRO = {"fecha": "2026-03-02", "monto": 850_000, "descripcion": "Choque leve", "estado": "abierto"}


def _poliza(numero="POL-IA-00001", **extra) -> dict:
    base = {"numero": numero, "asegurado": "Prueba Automática", "tipo": "hogar",
            "prima": 1_500_000, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"}
    base.update(extra)
    return base


# --- creación y persistencia --------------------------------------------------

def test_crear_poliza_devuelve_201_y_queda_guardada(cliente):
    r = cliente.post("/polizas", json=_poliza())
    assert r.status_code == 201
    creada = r.json()
    assert creada["numero"] == "POL-IA-00001" and "token_firma" not in creada
    leida = cliente.get(f"/polizas/{creada['id']}")
    assert leida.status_code == 200
    assert leida.json()["prima"] == 1_500_000


@pytest.mark.parametrize("tipo, prima", [("auto", 1), ("hogar", 350_000.5), ("vida", 4_800_000)])
def test_primas_y_tipos_validos_son_aceptados(cliente, tipo, prima):
    r = cliente.post("/polizas", json=_poliza(tipo=tipo, prima=prima))
    assert r.status_code == 201
    assert (r.json()["tipo"], r.json()["prima"]) == (tipo, prima)


def test_el_asegurado_se_normaliza(cliente):
    r = cliente.post("/polizas", json=_poliza(asegurado="  ana   rueda "))
    assert r.status_code == 201
    assert r.json()["asegurado"] == "Ana Rueda"


def test_siniestros_anidados_se_guardan(cliente):
    r = cliente.post("/polizas", json=_poliza(siniestros=[SINIESTRO]))
    assert r.status_code == 201
    leida = cliente.get(f"/polizas/{r.json()['id']}").json()
    assert [s["monto"] for s in leida["siniestros"]] == [850_000]


def test_numero_duplicado_da_409(cliente):
    assert cliente.post("/polizas", json=_poliza()).status_code == 201
    assert cliente.post("/polizas", json=_poliza()).status_code == 409
    assert len(cliente.get("/polizas").json()) == 1


# --- validación: lo que NO debe entrar -------------------------------------------

@pytest.mark.parametrize("cambio", [
    {"prima": 0},
    {"prima": -100},
    {"tipo": "moto"},
    {"asegurado": "  "},
    {"fecha_inicio": "2027-01-14", "fecha_fin": "2026-01-15"},
    {"fecha_inicio": "2026-01-15", "fecha_fin": "2026-01-15"},
    {"siniestros": [{**SINIESTRO, "monto": -50}]},
    {"siniestros": [{**SINIESTRO, "estado": "inventado"}]},
])
def test_entradas_invalidas_dan_422_y_no_se_guardan(cliente, cambio):
    r = cliente.post("/polizas", json=_poliza(**cambio))
    assert r.status_code == 422
    assert cliente.get("/polizas").json() == []


# --- recursos que no existen -------------------------------------------------------

def test_poliza_inexistente_da_404(cliente):
    assert cliente.get("/polizas/999999").status_code == 404
    assert cliente.put("/polizas/999999", json={"prima": 10}).status_code == 404
    assert cliente.post("/polizas/999999/siniestros", json=SINIESTRO).status_code == 404
    assert cliente.post("/score", json={"numero": "POL-NO-EXISTE"}).status_code == 404


# --- actualización parcial ---------------------------------------------------------

def test_put_parcial_cambia_solo_lo_enviado_y_persiste(cliente):
    creada = cliente.post("/polizas", json=_poliza(asegurado="Bruno Celis")).json()
    r = cliente.put(f"/polizas/{creada['id']}", json={"prima": 999_000})
    assert r.status_code == 200
    leida = cliente.get(f"/polizas/{creada['id']}").json()
    assert leida["prima"] == 999_000
    assert (leida["asegurado"], leida["tipo"], leida["fecha_fin"]) == ("Bruno Celis", "hogar", "2026-12-31")


def test_put_rechaza_nulos_y_fechas_incoherentes(cliente):
    creada = cliente.post("/polizas", json=_poliza()).json()
    assert cliente.put(f"/polizas/{creada['id']}", json={"tipo": None}).status_code == 422
    assert cliente.put(f"/polizas/{creada['id']}", json={"fecha_fin": "2025-01-01"}).status_code == 422
    assert cliente.get(f"/polizas/{creada['id']}").json()["tipo"] == "hogar"


# --- siniestros, resumen y puntuación ----------------------------------------------

def test_declarar_siniestro_da_201_y_aparece_en_el_listado(cliente):
    creada = cliente.post("/polizas", json=_poliza()).json()
    r = cliente.post(f"/polizas/{creada['id']}/siniestros", json=SINIESTRO)
    assert r.status_code == 201
    listado = cliente.get("/siniestros").json()
    assert [(s["numero_poliza"], s["monto"]) for s in listado] == [("POL-IA-00001", 850_000)]


def test_resumen_cuenta_y_suma_por_poliza(cliente):
    cliente.post("/polizas", json=_poliza(siniestros=[SINIESTRO, {**SINIESTRO, "monto": 150_000}]))
    cliente.post("/polizas", json=_poliza(numero="POL-IA-00002"))
    assert cliente.get("/resumen").json() == [
        {"numero": "POL-IA-00001", "n_siniestros": 2, "monto_total": 1_000_000},
        {"numero": "POL-IA-00002", "n_siniestros": 0, "monto_total": 0}]


def test_score_devuelve_puntaje_y_registra_la_prediccion(cliente):
    cliente.post("/polizas", json=_poliza())
    r = cliente.post("/score", json={"numero": "POL-IA-00001"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["numero"] == "POL-IA-00001"
    assert 0.0 <= cuerpo["puntaje"] <= 1.0 and isinstance(cuerpo["alto_riesgo"], bool)
    registradas = cliente.get("/predicciones").json()
    assert [(p["numero"], round(p["puntaje"], 4)) for p in registradas] == [("POL-IA-00001", cuerpo["puntaje"])]
