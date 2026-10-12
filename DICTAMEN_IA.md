# Dictamen sobre `ia_tests_propuesta.py` — Parte D

**Grupo:** Individual · **Integrantes:** Laura Pabon

> Cada mutación se aplicó con `sed` sobre el servicio ya corregido, se mostró con `git diff`, se
> corrieron la batería original (`ia_tests_propuesta.py`) y la corregida (`tests/test_ia_corregido.py`)
> y se deshizo con `git checkout -- <archivo>`. Con el servicio sano las dos baterías están en verde y
> `pytest -q tests/` da 37 passed. Las salidas son las de nuestra terminal (Windows, Git Bash).

## Defecto 1

- **Qué está mal**: tests que no pueden fallar. Las aserciones aceptan a la vez el resultado correcto y el incorrecto: `status_code in (200, 404)` para una póliza inexistente, `in (200, 201, 422)` al crear, `< 500` al listar y `"puntaje" in r.json() or "error" in r.json()` en `/score`. Un servicio roto y uno sano dan el mismo verde.
- **Por qué es un defecto** (M10 · 5. TestClient de FastAPI): un test de API tiene que fijar el código de estado que exige el contrato; si admite 200 y 404 no distingue «la encontré» de «no existe», que es justo lo que M6 · 5. Routing y CRUD obliga a separar.
- **Cómo lo comprobamos**: hicimos que el 404 deje de devolverse (sale 200). La batería original sigue en verde; la corregida falla.

```diff
diff --git a/main.py b/main.py
index 3232c1a..4068ae7 100644
--- a/main.py
+++ b/main.py
@@ -21,7 +21,7 @@ app = FastAPI(title="Pólizas API", version="1.0.0")


 def _no_existe(que) -> HTTPException:
-    return HTTPException(status_code=404, detail=f"no existe la póliza {que}")
+    return HTTPException(status_code=200, detail=f"no existe la póliza {que}")
```

```
$ pytest -q --tb=line -W ignore ia_tests_propuesta.py::test_consultar_poliza_inexistente
.                                                                                                                                                                                                          [100%]
1 passed in 1.14s
```

```
$ pytest -q --tb=line -W ignore tests/test_ia_corregido.py::test_poliza_inexistente_da_404
F                                                                                                                                                                                                          [100%]
=================================================================================================== FAILURES ====================================================================================================
E   AssertionError: assert 200 == 404
     +  where 200 = <Response [200 OK]>.status_code
     +    where <Response [200 OK]> = get('/polizas/999999')
     +      where get = <starlette.testclient.TestClient object at 0x000002A89353A510>.get
C:\Users\lvpabon\Documents\Universidad\Python\TallerII_Python\TallerCorteII_Python\tests\test_ia_corregido.py:87: AssertionError: assert 200 == 404
============================================================================================ short test summary info ============================================================================================
FAILED tests/test_ia_corregido.py::test_poliza_inexistente_da_404 - AssertionError: assert 200 == 404
1 failed in 0.28s
```

- **Corrección**: cada test afirma un único resultado (`== 201`, `== 404`, `== 409`, `== 422`) y comprueba el cuerpo; `test_poliza_inexistente_da_404` cubre GET, PUT, siniestros y `/score`.

## Defecto 2

- **Qué está mal**: tests que no prueban lo que dicen probar. (a) El «aislamiento» registra `app.dependency_overrides[get_db]` con una función `get_db` definida en el propio archivo, no con `database.get_db`, que es la que usan las rutas: el override nunca se aplica y las pruebas escriben en la base real. (b) `test_score_de_poliza_recien_creada` mira que haya `puntaje` en la respuesta, pero no que la predicción quede registrada, que es lo que hace `/score`.
- **Por qué es un defecto** (M10 · 6. Fixtures en pytest): la sustitución de dependencias se hace sobre la dependencia que inyecta la ruta; sobrescribir otra clave no aísla nada. Y comprobar una escritura exige volver a leerla.
- **Cómo lo comprobamos**: primero el aislamiento: `polizas.db` tenía 0 pólizas antes de correr la batería «aislada» y 7 después.

```
$ python -c "...select count(*) from polizas..."
(0,)
$ pytest -q -W ignore ia_tests_propuesta.py
......                                                                                                                                                                                                     [100%]
6 passed in 3.41s
$ python -c "...select count(*) from polizas..."
(7,)
```

Luego quitamos el `commit` de `/score`. La batería original sigue en verde; la corregida falla porque la predicción no quedó registrada.

```diff
diff --git a/servicios.py b/servicios.py
index e2fa3a5..216343e 100644
--- a/servicios.py
+++ b/servicios.py
@@ -113,7 +113,6 @@ def puntuar(db: Session, numero: str, settings: Settings) -> Prediccion:
     prediccion = Prediccion(poliza=poliza, puntaje=puntaje,
                             alto_riesgo=puntaje > settings.umbral_alto_riesgo)
     db.add(prediccion)
-    db.commit()
     return prediccion
```

```
$ pytest -q --tb=line -W ignore ia_tests_propuesta.py::test_score_de_poliza_recien_creada
.                                                                                                                                                                                                          [100%]
1 passed in 3.19s
```

```
$ pytest -q --tb=line -W ignore tests/test_ia_corregido.py::test_score_devuelve_puntaje_y_registra_la_prediccion
F                                                                                                                                                                                                          [100%]
=================================================================================================== FAILURES ====================================================================================================
E   AssertionError: assert [] == [('POL-IA-00001', 0.0369)]

      Right contains one more item: ('POL-IA-00001', 0.0369)
      Use -v to get more diff
C:\Users\lvpabon\Documents\Universidad\Python\TallerII_Python\TallerCorteII_Python\tests\test_ia_corregido.py:137: AssertionError: assert [] == [('POL-IA-00001', 0.0369)]
============================================================================================ short test summary info ============================================================================================
FAILED tests/test_ia_corregido.py::test_score_devuelve_puntaje_y_registra_la_prediccion - AssertionError: assert [] == [('POL-IA-00001', 0.0369)]
1 failed in 1.96s
```

- **Corrección**: fixture `cliente` en `tests/conftest.py` que sustituye `database.get_db` por una sesión sobre una base nueva en `tmp_path` y restaura el override al terminar. Tras cada escritura el test vuelve a leer (`GET /polizas/{id}`, `GET /siniestros`, `GET /predicciones`).

## Defecto 3

- **Qué está mal**: tests que unas veces pasan y otras no. Usan datos aleatorios sin semilla (`random.choice`, `random.uniform`) y dependen del estado de la base real que comparten con la aplicación. Con el mismo código, la batería da 6 failed si `polizas.db` no tiene el esquema y 6 passed después de `alembic upgrade head`; y cada corrida deja 7 pólizas más en esa base. Los datos «variados» además son siempre válidos: nunca prueban una entrada que deba rechazarse.
- **Por qué es un defecto** (M10 · 3. Pirámide de testing): un test debe ser determinista y aislado; si su resultado depende de lo que haya en la base o de un número aleatorio, un fallo no se puede reproducir y un éxito no dice qué se probó.
- **Cómo lo comprobamos**: primero el mismo código con dos estados de la base:

```
$ rm polizas.db
$ pytest -q -W ignore ia_tests_propuesta.py
FFFFFF
(traza de cada fallo omitida: todas terminan en «no such table: polizas»)
FAILED ia_tests_propuesta.py::test_crear_poliza_responde - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: polizas
FAILED ia_tests_propuesta.py::test_primas_variadas_son_aceptadas - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: polizas
FAILED ia_tests_propuesta.py::test_consultar_poliza_inexistente - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: polizas
FAILED ia_tests_propuesta.py::test_listar_polizas_no_falla - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: polizas
FAILED ia_tests_propuesta.py::test_resumen_devuelve_lista - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: polizas
FAILED ia_tests_propuesta.py::test_score_de_poliza_recien_creada - sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: polizas
6 failed in 10.10s
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 9ed42bb32284, esquema inicial
$ pytest -q -W ignore ia_tests_propuesta.py
......                                                                                                                                                                                                     [100%]
6 passed in 2.49s
```

Luego hicimos que el validador de fechas acepte lo que no debe. La batería original sigue en verde; la corregida falla en los dos casos de fechas (invertidas e iguales).

```diff
diff --git a/esquemas.py b/esquemas.py
index f22d8ca..f417ded 100644
--- a/esquemas.py
+++ b/esquemas.py
@@ -42,7 +42,7 @@ class PolizaEntrada(BaseModel):
     @model_validator(mode="after")
     def fin_posterior_al_inicio(self):
         if self.fecha_fin <= self.fecha_inicio:
-            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
+            pass
         return self
```

```
$ pytest -q --tb=line -W ignore ia_tests_propuesta.py
......                                                                                                                                                                                                     [100%]
6 passed in 2.51s
```

```
$ pytest -q --tb=line -W ignore tests/test_ia_corregido.py::test_entradas_invalidas_dan_422_y_no_se_guardan
....FF..                                                                                                                                                                                                   [100%]
=================================================================================================== FAILURES ====================================================================================================
E   assert 201 == 422
     +  where 201 = <Response [201 Created]>.status_code
C:\Users\lvpabon\Documents\Universidad\Python\TallerII_Python\TallerCorteII_Python\tests\test_ia_corregido.py:80: assert 201 == 422
E   assert 201 == 422
     +  where 201 = <Response [201 Created]>.status_code
C:\Users\lvpabon\Documents\Universidad\Python\TallerII_Python\TallerCorteII_Python\tests\test_ia_corregido.py:80: assert 201 == 422
============================================================================================ short test summary info ============================================================================================
FAILED tests/test_ia_corregido.py::test_entradas_invalidas_dan_422_y_no_se_guardan[cambio4] - assert 201 == 422
FAILED tests/test_ia_corregido.py::test_entradas_invalidas_dan_422_y_no_se_guardan[cambio5] - assert 201 == 422
2 failed, 6 passed in 1.40s
```

- **Corrección**: datos fijos y explícitos, sin `random`; los casos válidos e inválidos se enumeran con `pytest.mark.parametrize` (prima 0 y negativa, tipo inexistente, asegurado vacío, fechas invertidas e iguales, siniestro anidado con monto negativo o estado inventado), y cada test parte de una base vacía.
