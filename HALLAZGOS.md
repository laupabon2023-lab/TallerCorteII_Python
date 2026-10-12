# Hallazgos — Parte A

**Grupo:** Individual · **Integrantes:** Laura Pabon

> Todas las evidencias se ejecutaron sobre `v0-semilla` con el servicio levantado
> (`uvicorn main:app --host 127.0.0.1 --port 8000`) y en el orden de la tabla: H13 y H14
> dejan el servicio del semilla en mal estado y por eso van al final.

| ID | Síntoma observable | Causa | Módulo · Sección | SHA donde se observa | Comando de evidencia | Salida obtenida | Corrección aplicada |
|----|--------------------|-------|------------------|----------------------|----------------------|-----------------|---------------------|
| H1 | La aplicación ignora DATABASE_URL y usa app.db. También tiene una clave secreta escrita en el código. | No lee correctamente la configuración desde variables de entorno y deja secretos en el código. | M8 · 3. De lo duro a lo flexible: variables de entorno | `v0-semilla` | `DATABASE_URL=sqlite:///otra.db python -c "import config, database; print(database.engine.url, config.CLAVE_API_REASEGURO[:3])"` | `sqlite:///app.db rk-` |Leer la configuración desde variables de entorno y no guardar secretos directamente en el código. |
| H2 | Las dependencias no tienen versiones fijadas, app.db está en Git y .gitignore es insuficiente. | No se configuraron correctamente las versiones ni los archivos que deben excluirse del repositorio. | M10 · 7. Reproducibilidad sin Docker | `v0-semilla` | `echo "$(grep -c == requirements.txt) $(git ls-files '*.db') $(cat .gitignore)"` | `0 app.db *.pyc` | Fijar versiones compatibles, sacar app.db del repositorio y ampliar .gitignore. |
| H3 | Las tablas se crean automáticamente cuando inicia la aplicación.| Se utiliza create_all() y no se gestionan los cambios con migraciones de Alembic. | M9 · 6. Modelado de BD y migraciones con Alembic | `v0-semilla` | `grep -n "create_all" main.py` | `17:Base.metadata.create_all(engine)` | Usar Alembic para controlar los cambios en la estructura de la base de datos. |
| H4 | Docker inicia la aplicación con recarga automática y escucha en 127.0.0.1. | Se utiliza una configuración de desarrollo que no es apropiada para producción. | M11 · 6. Estructura de un Dockerfile | `v0-semilla` | `grep "^CMD" Dockerfile` | `CMD ["uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"]` | Quitar --reload en producción y configurar el servicio para escuchar en 0.0.0.0. |
| H5 | Las pruebas pasan la primera vez, pero fallan al ejecutarlas nuevamente. | Los datos permanecen en la base de datos y afectan las siguientes ejecuciones. | M10 · 6. Fixtures en pytest | `v0-semilla` | `pytest -q -p no:cacheprovider tests/test_api.py >/dev/null 2>&1; echo -n "$? "; pytest -q -p no:cacheprovider tests/test_api.py >/dev/null 2>&1; echo $?` | `0 1` | Usar una base de datos temporal y preparar y limpiar los datos de las pruebas. |
| H6 |Al crear una póliza, la respuesta muestra token_firma y devuelve código 200. |La respuesta no oculta el campo sensible y no utiliza el código de estado correcto.| M6 · 5. Routing y CRUD | `v0-semilla` | `curl -s -w "%{http_code}" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-EV-00001","asegurado":"Ana Rueda","tipo":"auto","prima":1250000,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14"}' \| grep -o -e '"token_firma"' -e '[0-9]*$' \| paste -sd' '` | `"token_firma" 200` | Excluir token_firma de la respuesta y devolver 201 al crear una póliza. |
| H7 | El campo asegurado aparece como null. | El `field_validator` de `asegurado` procesa el nombre, pero no devuelve el valor validado, y Pydantic guarda `None` | M7 · 4. Validadores de campo | `v0-semilla` | `curl -s -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-EV-00002","asegurado":"Bruno Celis","tipo":"hogar","prima":980000,"fecha_inicio":"2026-02-01","fecha_fin":"2027-01-31"}' \| grep -o '"asegurado":[a-z]*'` | `"asegurado":null` | Hacer que el validador devuelva el nombre normalizado. |
| H8 | Se acepta una póliza que termina antes de empezar | No se comprueba que las fechas tengan un orden válido. | M7 · 4. Validadores de campo | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-EV-00003","asegurado":"Carla Ibanez","tipo":"vida","prima":500000,"fecha_inicio":"2027-01-14","fecha_fin":"2026-01-15"}'` | `200` | Validar que la fecha final sea posterior a la inicial. |
| H9 | La API acepta un siniestro con monto negativo. | Los siniestros se reciben como diccionarios sin validaciones específicas. | M7 · 5. Modelos anidados y topología jerárquica | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/polizas -H "Content-Type: application/json" -d '{"numero":"POL-EV-00004","asegurado":"Diego Fajardo","tipo":"auto","prima":700000,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14","siniestros":[{"fecha":"2026-03-02","monto":-50,"descripcion":"Choque leve"}]}'` | `200` | `siniestros: list[SiniestroEntrada]`Crear un modelo SiniestroEntrada que valide los datos y no permita montos negativos. |
| H10 | Consultar o actualizar una póliza inexistente responde 200 | Las rutas devuelven un `dict` con `error` en vez de lanzar `HTTPException(404)`. La aplicación no verifica correctamente si la póliza existe. | M6 · 5. Routing y CRUD | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code} " localhost:8000/polizas/999999; curl -s -o /dev/null -w "%{http_code}" -X PUT localhost:8000/polizas/999999 -H "Content-Type: application/json" -d '{"prima": 10}'` | `200 200` | `HTTPException(status_code=404)` en GET, PUT, siniestros y `/score`. Comprobar la existencia de la póliza y devolver 404 cuando no exista. |
| H11 |Al actualizar un solo campo, otros datos de la póliza quedan en null. | La actualización procesa campos que el usuario no envió. Escribe `None` en todos los campos no enviados | M9 · 8. Ejercicio integrador: tareas con categorías | `v0-semilla` | `curl -s -X PUT localhost:8000/polizas/2 -H "Content-Type: application/json" -d '{"prima": 999000}' \| grep -o '"tipo":[a-z]*'` | `"tipo":null` | Actualizar solo los campos enviados mediante model_dump(exclude_unset=True). |
| H12 | La respuesta de /predicciones no incluye el número de la póliza | El modelo de respuesta o la consulta no incorpora ese dato | M9 · 7. SQLite local e integración con FastAPI | `v0-semilla` | `curl -s localhost:8000/predicciones \| grep -c '"numero"'` | `0` | `PrediccionSalida` con `numero` (`from_attributes=True`) y `joinedload` de la póliza |
| H13 | Se puede declarar un siniestro de una póliza que no existe, y después `/siniestros` revienta | SQLite trae las claves foráneas apagadas y la ruta no comprueba la póliza: queda un siniestro huérfano | M9 · 7. SQLite local e integración con FastAPI | `v0-semilla` | `curl -s -o /dev/null -w "%{http_code} " -X POST localhost:8000/polizas/999999/siniestros -H "Content-Type: application/json" -d '{"fecha":"2026-03-02","monto":850000,"descripcion":"Choque leve"}'; curl -s -o /dev/null -w "%{http_code}" localhost:8000/siniestros` | `200 500` |Activar las claves foráneas y comprobar la existencia de la póliza antes de crear el siniestro y 404 si la póliza no existe |
| H14 | Un número repetido da 500 y el servicio deja de responder. Después de intentar registrar un duplicado, las siguientes solicitudes también fallan.| La sesión compartida de la base de datos queda en estado de error y no se recupera correctamente. | M8 · 4. Inyección de dependencias con Depends | `v0-semilla` | `D='{"numero":"POL-EV-00005","asegurado":"Elena Ortiz","tipo":"auto","prima":600000,"fecha_inicio":"2026-01-15","fecha_fin":"2027-01-14"}'; curl -s -o /dev/null -w "%{http_code} " -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "$D"; curl -s -o /dev/null -w "%{http_code} " -X POST localhost:8000/polizas -H "Content-Type: application/json" -d "$D"; curl -s -o /dev/null -w "%{http_code}" localhost:8000/polizas` | `200 500 500` | Crear una sesión por petición, ejecutar rollback cuando ocurra un error y devolver 409 para duplicados |


---

# Parte C — Interpretación de las consultas

> Conteos de `python contar_consultas.py` (sin modificarlo) con 10 y 2000 pólizas de 3 siniestros
> cada una. Para decidir medimos también las estrategias que no dejamos en el código con
> `python comparar_estrategias.py` (script añadido: cambia por un momento la función de
> `servicios.py`, cuenta y la restaura; no modifica el servicio). Esos números van entre paréntesis.
> Los tiempos son de una sola corrida en nuestra máquina y solo sirven de referencia.

## `/polizas`

Estrategia en el código: **selectinload** (`servicios.listar_polizas`). Con 10 pólizas salen 2
consultas: una por las pólizas y un `SELECT ... WHERE poliza_id IN (...)` con sus 10 ids. Con 2000
salen 5: la de pólizas más 4 de siniestros, porque SQLAlchemy parte el `IN` en bloques de 500 ids
(2000 / 500 = 4). Crece con n/500, no con n. Con `lazy` serían 11 y 2001 (N+1: una consulta por
póliza; 1761 ms con 2000). Con `joinedload` sale 1 en los dos tamaños, pero con 2000 pólizas tardó
249 ms frente a 179 ms de selectinload: el `JOIN` de uno a muchos devuelve 6000 filas que repiten
los datos de cada póliza 3 veces. Menos consultas no fue más rápido; además el JOIN rompe la
paginación con `LIMIT`. Nos quedamos con selectinload.

## `/polizas/{id}`

Estrategia en el código: **lazy** (`db.get` y la relación se carga al serializar). Salen 2 consultas
con 10 y con 2000 pólizas: una por la póliza y otra por sus siniestros cuando `PolizaSalida` los lee.
No cambia con el tamaño porque siempre se pide una sola póliza. Aquí el código no sigue la regla
«cargar todo de una vez» y la medición da exactamente igual: con `selectinload` también salen 2 y 2,
porque para una sola póliza «la consulta aparte» es la misma consulta. `joinedload` baja a 1, pero
es una consulta fija por petición (4.5 ms frente a 2.8 ms con lazy en nuestra corrida); dejamos lazy,
que es lo más simple. Esto solo se ve contando.

## `/siniestros`

Estrategia en el código: **joinedload** de `Siniestro.poliza`. Sale 1 consulta con 10 y con 2000:
un `SELECT` de siniestros con `LEFT OUTER JOIN polizas`. La relación es de muchos a uno, así que el
JOIN no multiplica filas: cada siniestro trae exactamente una póliza. Con `lazy` serían 11 y 2001
(una por póliza distinta; 1890 ms con 2000) y con `selectinload` 2 y 5 (264 ms frente a 102 ms).

## `/resumen`

Estrategia en el código: **agregada** (`COUNT` y `SUM` con `GROUP BY` en la base). Sale 1 consulta
con 10 y con 2000: la base devuelve una fila por póliza y ningún siniestro viaja a Python. Aquí
seguir la regla «cargar todo de una vez» da peor rendimiento: cargar las pólizas con sus siniestros
(`selectinload`) y sumar en Python da 2 y 5 consultas y trae los 6000 siniestros para descartarlos;
con 2000 pólizas tardó 225 ms frente a 52 ms de la agregación, unas 4 veces más. La agregación
conserva además las pólizas sin siniestros (`LEFT OUTER JOIN` y `COALESCE`, con total 0).
