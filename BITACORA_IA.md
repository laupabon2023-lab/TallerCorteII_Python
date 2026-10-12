# Bitácora de uso de IA

**Grupo:** Individual · **Integrantes:** Laura Pabon
**Herramientas usadas:** Claude (claude.ai); ChatGPT

## Prompts

| # | Parte | Quién | Prompt (resumido si es largo) |
|---|-------|-------|-------------------------------|
| 1 | A–E | Laura Pabon | «Este es el segundo taller. Ayúdame a entender qué debo hacer y como realizarlo |
| 2 | A–E | Laura Pabon | «Genérame paso a paso lo qué debo hacer desde gitbash y cómo; lo realizaré sola» |
| 3 | Inicio | Laura Pabon | «¿En qué parte dice que hay que descargar lo del docente?» (antes de clonar el semilla) |
| 4 | A | Laura Pabon | A otra IA: revisión de mi `HALLAZGOS.md` |
| 5 | B | Laura Pabon | «¿Qué es lo que estamos haciendo en toda esta parte luego de los hallazgos?» |
| 6 | B9 | Laura Pabon | Qué hacer cuando Docker Desktop no arranca por virtualización y no tengo permisos de administrador |
| 7 | E | Laura Pabon | Genérame la bitácora de Ia de toda la conversación que hemos tenido |


## Aceptado

| # | Qué propuso la IA | Por qué lo aceptamos | Qué cambiamos antes de usarlo |
|---|-------------------|----------------------|-------------------------------|
| 1 | Partir de `v0-semilla` con `git reset --hard` en vez de la punta de `main` del semilla | Pregunté de dónde salía; la IA mostró que el docente subió el 10 de octubre un commit cuyo correo `verificar_entrega.py` contaría como persona extra | Nada |
| 2 | 14 defectos con comandos de evidencia para `HALLAZGOS.md` | Corrí los 14 comandos sobre `v0-semilla` y todos reprodujeron el síntoma | Reescribí con mis palabras algunas correcciones (p. ej. H14); en H5 dejé `0 1`, la salida de la primera corrida |
| 3 | Refactor de `config.py`, `database.py`, `modelos.py`, `esquemas.py`, `main.py` y `servicios.py` | `tests/test_contrato.py` pasó 12/12 dos veces y quedó intacto | Nada |
| 4 | Batería corregida y tres mutaciones para la Parte D | Cada mutación dejó la batería original en verde y la corregida en rojo en mi máquina | Nada |
| 5 | Usar GitHub Codespaces para probar Docker | Mi equipo no permite activar WSL 2 sin permisos de administrador | No hago commits desde el Codespace: allí Git usaría otra identidad |

## Rechazado

| # | Qué propuso la IA | Por qué lo rechazamos | Qué hicimos en su lugar |
|---|-------------------|-----------------------|-------------------------|
| 1 | Otra IA indicó que en H6–H14 de `HALLAZGOS.md` había descripciones en vez de comandos y pidió reemplazarlas | Lo verifiqué con un script que imprime la columna «Comando de evidencia» de cada fila: las 14 tenían 8 columnas y el comando exacto que ejecuté | Mantuve la tabla sin cambios |
| 2 | Interpretación de la Parte C con números (alternativas lazy, joinedload y tiempos) medidos en la máquina de la IA | La rúbrica califica la explicación de **mis** números; no los había medido yo | Corrí `comparar_estrategias.py` y reescribí los cuatro párrafos con mis conteos y tiempos. En mi máquina `joinedload` en `/polizas` hizo 1 consulta pero tardó más (249 ms) que `selectinload` (179 ms con 5 consultas), y sumar en Python el `/resumen` fue unas 4 veces más lento que agregar, no 10 |
| 3 | Activar WSL 2 desde PowerShell como administrador (`dism` y `wsl --install`) para que arrancara Docker Desktop | No tengo permisos de administrador en el equipo | Probé la imagen en GitHub Codespaces: build, `/health`, usuario `appuser` y `healthy` |
| 4 | La batería `ia_tests_propuesta.py` completa | Aserciones que no pueden fallar, aislamiento falso y datos aleatorios que dependen del estado de la base (ver `DICTAMEN_IA.md`) | `tests/test_ia_corregido.py` |
