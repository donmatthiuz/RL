# 04 — Tareas

Backlog completo del proyecto, organizado por **fases** y por **rol**. Cada tarea tiene un ID, que
se usa en los mensajes de commit (ver [06_flujo_trabajo.md](06_flujo_trabajo.md)), sus dependencias
y un criterio de aceptación verificable.

> Las fases marcan el **orden** de trabajo, no fechas. Si el tiempo aprieta, se cortan primero
> las tareas **P2** y después las **P1**.

**Prefijos de ID:** `INF` = R1 (infraestructura), `DAT` = R2 (datos), `ENV` = R3 (entorno),
`AGT` = R4 (agentes), `EVA` = R5 (evaluación y demo), `DOC` = informe y presentación.

**Prioridad:** **P0** = sin esto no hay proyecto · **P1** = necesario para una buena nota ·
**P2** = deseable si da el tiempo.

---

## Tablero

El seguimiento del proyecto se lleva **solo en este documento** (ADR-015): no hay tablero en GitHub
Projects ni issues. R1 actualiza esta sección en `proyecto` cada vez que se abre o se mezcla un PR,
y el estado de cada tarea se marca en su fila (por ejemplo, **En PR** o **Hecha el 31/10/2026**).

- **Hecha:** está en `proyecto`.
- **En PR:** el código o el documento ya existe; falta que se revise y se mezcle.
- **Falta:** todavía no se empezó.

### Avance por rol

Al 01/11/2026, de 66 tareas: 9 hechas, 31 en PR y 26 sin empezar. Ningún PR se mezcló todavía.

| Rol | Hechas | En PR | Faltan |
| --- | --- | --- | --- |
| R1 Josué | INF-01 a INF-05 y DOC-01 | INF-06 (#1, #4 y #11), INF-07 (#21) e INF-08 (#25) | INF-09 e INF-10 |
| R2 Mathew | DAT-01, DAT-02 (dentro de DAT-10) y DAT-10 | DAT-03 a DAT-08 y DAT-11 (#2, #3, #5, #7, #9 y #10) | DAT-09 (P2) |
| R3 Gustavo | — | ENV-01 a ENV-07 y ENV-10 (#6, #10, #11, #15, #17 y #23) | ENV-08 y ENV-09 (P2) |
| R4 sin asignar | — | AGT-02 a AGT-08 (#4, #12, #18, #19 y #20) | AGT-01, AGT-09 y AGT-10 |
| R5 sin asignar | — | EVA-01 a EVA-03, EVA-05, EVA-07 y EVA-11 (#8, #13, #14, #16, #22 y #24) | EVA-04, EVA-06 y EVA-08 a EVA-10 |
| Todos (documento) | DOC-01 | — | DOC-02 a DOC-14; DOC-12 se lleva durante todo el proyecto |

Mezclar un PR no cierra todas sus tareas: AGT-04, AGT-05 y AGT-08 piden superar a `Random` o
evaluarse en val, y EVA-11 pide el reporte de val y test. Esas quedan abiertas hasta abrir val.

Lo que le falta a cada rol:

- **R1:** mezclar la pila en orden y revisar #21 y #25. El nightly de INF-08 solo corre cuando
  el workflow está en `main` (regla de GitHub), así que empieza cuando `proyecto` llegue a `main`.
  INF-09 espera la evaluación en test (EVA-06) e INF-10 espera los modelos finales (H3).
- **R2:** revisar #1, #2, #3, #5, #7, #9 y #10. DAT-09 (ETH) es opcional.
- **R3:** revisar #1, #6, #11, #15, #17 y #23 (las variantes de recompensa). La ablación
  (ENV-08) espera abrir val. ENV-09 es opcional.
- **R4 (sin dueño):** revisar #4, #11 (el MDP), #12, #18, #19 y #20. AGT-01 (prototipo en
  CartPole) no tiene bloqueos. AGT-09 y AGT-10 esperan abrir val.
- **R5 (sin dueño):** revisar #8 y responder E1 y E2, y revisar #13, #14, #16, #22 (reporte) y
  #24 (demo). EVA-04 espera E1 y E2. EVA-06, EVA-08 y EVA-10 son de la fase final. EVA-09 es
  opcional.

### PR en revisión

Los PR forman una pila: cada uno se mezcla después del que tiene como base (ver "Pilas de PR" en
[06_flujo_trabajo.md](06_flujo_trabajo.md)). Cuatro PR (#11, #14, #19 y #23) necesitan además otra
rama, incorporada con merge: lo marcan las flechas punteadas, y esa rama se mezcla antes. #22, #23 y
#25 salen de #21 y se probaron mezclados juntos, sin conflictos.

```mermaid
flowchart LR
    P["proyecto"] --> PR1["#1 INF-06 datos<br/>R2 y R3"]
    PR1 --> PR2["#2 DAT-03 klines<br/>R2"] --> PR3["#3 DAT-06 split<br/>R2"] --> PR5["#5 DAT-04/05 dataset<br/>R2"]
    PR1 --> PR4["#4 INF-06 Policy<br/>sin revisor (R4)"]
    P --> PR6["#6 ENV-03 costos<br/>R3"]
    P --> PR8["#8 EVA-01 protocolo<br/>sin revisor (R5)"]
    PR5 --> PR7["#7 DAT-08 EDA<br/>R2"]
    PR5 --> PR9["#9 DAT-11 trades<br/>R2"]
    PR5 --> PR10["#10 DAT-07 steps y features<br/>R2"] --> PR11["#11 ENV-04 entorno<br/>R3 y R4"]
    PR4 -.-> PR11
    PR6 -.-> PR11
    PR11 --> PR12["#12 AGT-03 baselines<br/>sin revisor (R4)"] --> PR13["#13 EVA-02 backtest<br/>sin revisor (R5)"] --> PR14["#14 EVA-11 validación<br/>sin revisor (R5)"] --> PR16["#16 EVA-03 métricas<br/>sin revisor (R5)"]
    PR9 -.-> PR14
    PR11 --> PR15["#15 ENV-06 invariantes<br/>R3"]
    PR16 --> PR17["#17 ENV-07 render<br/>R3"]
    PR11 --> PR18["#18 AGT-02 adaptadores<br/>sin revisor (R4)"]
    PR17 --> PR19["#19 AGT-04/05/06 entrenamiento<br/>sin revisor (R4)"]
    PR18 -.-> PR19
    PR19 --> PR20["#20 AGT-07/08 offline: CQL y BC<br/>sin revisor (R4)"]
    PR20 --> PR21["#21 INF-07 integración y evaluate<br/>cualquiera"]
    PR21 --> PR22["#22 EVA-05 reporte<br/>sin revisor (R5)"] --> PR24["#24 EVA-07 demo<br/>sin revisor (R5)"]
    PR21 --> PR23["#23 ENV-05 variantes de recompensa<br/>R3"]
    PR15 -.-> PR23
    PR21 --> PR25["#25 INF-08 smoke y nightly<br/>cualquiera"]
```

| Orden | PR | Tarea | Base | También necesita | Revisa |
| --- | --- | --- | --- | --- | --- |
| 1 | #1 | INF-06: contratos de datos | `proyecto` | — | R2 y R3 |
| 2 | #2 | DAT-03: klines de Binance | #1 | — | R2 |
| 2 | #4 | INF-06: `Policy` y `Action` | #1 | — | Sin asignar (R4) |
| Cuando se quiera | #6 | ENV-03: costos | `proyecto` | — | R3 |
| Antes de ver resultados en val | #8 | EVA-01: protocolo de evaluación, con E1 y E2 para el equipo | `proyecto` | — | Sin asignar (R5) |
| 3 | #3 | DAT-06: split con exclusiones de S11 | #2 | — | R2 |
| 4 | #5 | DAT-04 y DAT-05: `markets`, `prices_raw` y `spot_1m` | #3 | — | R2 |
| 5 | #7 | DAT-08: EDA sobre train | #5 | — | R2 |
| 5 | #9 | DAT-11: trades de val y test, y la captura de train | #5 | — | R2 |
| 5 | #10 | DAT-04, DAT-05 y DAT-07: `steps.parquet`, features y normalización | #5 | — | R2 |
| 6 | #11 | ENV-01, ENV-02, ENV-04, ENV-05, ENV-10 e INF-06 (`info`): el entorno | #10 | #4 y #6 | R3; R4 el MDP |
| 7 | #12 | AGT-03: baselines | #11 | — | Sin asignar (R4) |
| 7 | #15 | ENV-06: invariantes con `hypothesis` | #11 | — | R3 |
| 7 | #18 | AGT-02: adaptadores de SB3 y d3rlpy, con torch solo CPU | #11 | — | Sin asignar (R4) |
| 8 | #13 | EVA-02: backtest | #12 | — | Sin asignar (R5) |
| 9 | #14 | EVA-11: validación de ejecuciones y modo estricto | #13 | #9 | Sin asignar (R5) |
| 10 | #16 | EVA-03: métricas | #14 | — | Sin asignar (R5) |
| 11 | #17 | ENV-07: `render()` en modo texto | #16 | — | R3 |
| 12 | #19 | AGT-04, AGT-05 y AGT-06: entrenamiento de PPO y DQN y prueba de cordura | #17 | #18 | Sin asignar (R4) |
| 13 | #20 | AGT-07 y AGT-08: dataset offline y entrenamiento de CQL y BC | #19 | — | Sin asignar (R4) |
| 14 | #21 | INF-07: pipeline completo por la CLI y comando `evaluate` | #20 | — | Cualquier integrante |
| 15 | #22 | EVA-05: `polym4v report`, con tabla comparativa y figuras | #21 | — | Sin asignar (R5) |
| 15 | #23 | ENV-05: las seis variantes de recompensa de la ablación | #21 | #15 | R3 |
| 15 | #25 | INF-08: job *smoke-train* en la CI y `nightly.yml` con tests `slow` y `network` | #21 | — | Cualquier integrante |
| 16 | #24 | EVA-07: demo en Streamlit que reproduce trayectorias | #22 | — | Sin asignar (R5) |

### Decisiones y bloqueos

**Decisiones del simulador:** todas tomadas el 31/10/2026 (ADR-016 y ADR-017), con sus preguntas y
opciones en la sección 6 de [09_sistema_simulacion.md](09_sistema_simulacion.md). S4a es
provisional hasta validarla con trades reales (DAT-11 y EVA-11).

**Recompensa principal (R1, 31/10/2026 y 01/11/2026):** antes de elegir entre `pnl` y `pnl_risk`
se investigó cómo la diseñan otros entornos y la literatura
([recompensas](ia/investigaciones/recompensas_rl_trading.md)). El 01/11/2026 R1 aprobó la lista de
la ablación de ENV-08, en dos etapas y con 5 semillas por variante:

- **Etapa A:** `pnl`, `pnl_mid` y `terminal`.
- **Etapa B, sobre la ganadora de A:** `pnl_risk` con 2 valores de `λ_dd`, `pnl_hold` y `utility`.

Las seis variantes están en #23. Mientras tanto, `configs/env.yaml` usa `pnl`.

**Trades de train (R1, 31/10/2026):** se capturan en segundo plano (en curso el 01/11/2026), y el
modo de entrenamiento se decide después comparando los dos modos en train (actualización de
ADR-017).

**Val sigue cerrado** hasta mezclar el protocolo (#8), y para eso el equipo tiene que responder E1
y E2 en el PR. Los baselines, el backtest y las métricas solo se corrieron sobre train.

**Sin bloqueos, para empezar:**

- AGT-01: prototipo en CartPole, para quien tome R4.
- ENV-09 y DAT-09 (P2): sensibilidad a los costos y extensión a ETH, si da el tiempo.
- DOC-12: historial de prompts con su evaluación, que se lleva durante todo el proyecto.

**Para que R1 confirme:** en #24, `streamlit` va en un grupo `demo` que `uv sync` instala por
defecto (`default-groups`), así los tests de la demo corren en la CI.

**Esperan respuesta del equipo:** EVA-04 (`stats.py` con la prueba del protocolo) espera E1 y E2
en #8.

**Esperan a abrir val (#8):** entrenar con datos reales y elegir checkpoints (AGT-04 en adelante),
la ablación de la recompensa (ENV-08), la tabla de baselines y el reporte de val (EVA-05) y la
validación de ejecuciones en val (EVA-11).

Las decisiones previas al diseño (D1 a D9) están en
[decisiones_previas_al_diseno.md](notas/decisiones_previas_al_diseno.md) y las ya tomadas, como
ADR, en [07_riesgos_y_decisiones.md](07_riesgos_y_decisiones.md).

---

## 1. Fases e hitos

| Fase | Objetivo | Hito de cierre |
| ------ | ---------- | ---------------- |
| **F0 — Setup** | Repo, herramientas, CI y validar las APIs | **H0:** CI en verde, spike de datos con su conclusión |
| **F1 — Datos y entorno** | Dataset v1 y `PolymarketEnv` v1 testeado | **H1:** un baseline corre episodios de extremo a extremo sobre datos reales |
| **F2 — Agentes online** | Baselines, PPO y DQN entrenados, primer backtest | **H2:** primera tabla comparativa en *val* |
| **F3 — Offline RL y ajuste** | CQL/BC, ablación de la recompensa, ajuste de hiperparámetros, 5 semillas | **H3:** modelos finales congelados |
| **F4 — Evaluación final y demo** | Evaluación en test, demo, informe y presentación | **H4:** release `v1.0` y entrega |

```mermaid
flowchart LR
    F0["F0 — Setup"] --> H0(("H0")) --> F1["F1 — Datos y entorno"] --> H1(("H1"))
    H1 --> F2["F2 — Agentes online"] --> H2(("H2")) --> F3["F3 — Offline RL y ajuste"] --> H3(("H3"))
    H3 --> F4["F4 — Evaluación final y demo"] --> H4(("H4"))
```

| Rol | F0 | F1 | F2 | F3 | F4 |
| --- | --- | --- | --- | --- | --- |
| R1 Infra | INF-01 a 04 | INF-05, 06 | INF-07 E2E | INF-08 | INF-09, 10 |
| R2 Datos | DAT-01 (hecha) | DAT-02 a 06 | DAT-07, 08 | DAT-09 ETH (P2) | DOC |
| R3 Entorno | ENV-01 | ENV-02 a 06 | ENV-07 | ENV-08 ablación | DOC |
| R4 Agentes | AGT-01 | AGT-02, 03 | AGT-04 a 06 | AGT-07 a 10 | DOC |
| R5 Eval/Demo | EVA-01 | EVA-02 | EVA-03 a 05 | EVA-06, 07 | EVA-08 a 10 |

La CI/CD volvió al alcance con el ADR-014, que reemplaza al ADR-010.

---

## 2. Tareas por rol

### R1 — Líder técnico e integrador

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| INF-01 | **Hecha el 30/10/2026.** Crear la estructura del repo, `pyproject.toml` con `uv`, el paquete `polym4v` instalable y `src/` layout | F0 | P0 | — | `uv sync && uv run python -c "import polym4v"` funciona en una máquina limpia |
| INF-02 | **Hecha el 30/10/2026.** Configurar `ruff`, `mypy` (permisivo) y `pre-commit` | F0 | P0 | INF-01 | `pre-commit run --all-files` pasa |
| INF-03 | **Hecha el 30/10/2026.** Workflow `ci.yml`: lint, tests y cobertura en cada push a `proyecto` | F0 | P0 | INF-02 | La CI corre en un push de prueba y marca en rojo el commit si falla |
| INF-04 | **Hecha el 31/10/2026 (ADR-015):** el tablero es la sección "Tablero" de este documento, sin GitHub Projects ni issues | F0 | P0 | — | Cada tarea tiene su estado en su fila y la sección "Tablero" muestra lo que está en PR, bloqueado o sin empezar |
| INF-05 | **Hecha el 31/10/2026.** `utils/`: `config.py` (pydantic), `seeding.py`, `logging.py`, `paths.py` | F1 | P0 | INF-01 | Tests unitarios. La misma semilla da resultados idénticos. |
| INF-06 | **En PR #1, #4 y #11 (`info`).** Definir los **contratos** como código: `schemas.py` (con R2), protocolo `Policy` (con R4) y claves de `info` (con R3) | F1 | P0 | INF-05 | Revisado y aceptado por R2, R3 y R4 antes de subirlo |
| INF-07 | **En PR #21** (con `argparse`). CLI `typer` (`data build`, `train`, `collect-offline`, `evaluate`, `report`) y test de integración E2E sobre el mini-dataset | F2 | P0 | DAT-05, ENV-05, AGT-03, EVA-02 | `pytest -m integration` corre todo el pipeline en < 2 min |
| INF-08 | **En PR #25** (el nightly corre desde `main`). Job *smoke-train* en la CI y workflow `nightly.yml` (tests `slow` y backtest corto) | F3 | P1 | INF-07 | El nightly corre por `workflow_dispatch` y por cron |
| INF-09 | `release.yml` (CD): en un tag `v*` genera el reporte y adjunta las tablas, figuras y modelos finales al GitHub Release | F4 | P1 | EVA-06 | El tag `v1.0` produce un Release con sus artefactos |
| INF-10 | Revisión de reproducibilidad: un integrante que no participó clona el repo y reproduce un resultado siguiendo el README | F4 | P0 | H3 | El resultado coincide dentro de la tolerancia (± IC) |

### R2 — Ingeniero de datos

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| DAT-01 | **Hecha el 30/10/2026: ver [spike](notas/spike_datos.md) y ADR-004, ADR-007 a ADR-009.** **Spike de APIs:** probar Gamma, CLOB `prices-history` y Binance. Medir la granularidad real en mercados cerrados, los límites de rate y los campos disponibles. Elegir la familia de mercados. | F0 | P0 | — | Nota en `docs/notas/spike_datos.md`, más un ADR con la familia de mercados y la granularidad elegidas |
| DAT-02 | **Hecha el 31/10/2026 dentro de DAT-10:** `capture_series` lista los eventos cerrados de Gamma por serie, con paginación, y sus tests usan una fuente falsa, sin red. `GammaClient`: listar mercados cerrados filtrados por tag o texto, con paginación | F1 | P0 | DAT-01, INF-01 | Tests con respuestas grabadas (`responses`), sin red |
| DAT-03 | **En PR #2.** `ClobClient` y `BinanceClient`, con caché en disco, reintentos y rate limiting | F1 | P0 | DAT-01 | Una segunda ejecución no hace llamadas de red (test con contador) |
| DAT-04 | **En PR #5 y #10.** Limpieza, re-muestreo a una grilla fija (solo *forward-fill*), alineación con el spot y filtros de calidad | F1 | P0 | DAT-02, DAT-03 | Test: ningún valor en `t` se deriva de datos con `ts > t` |
| DAT-05 | **En PR #5 y #10.** `build_dataset.py`: `markets.parquet`, `steps.parquet` y `manifest.json` con hash. **Mini-dataset de fixtures** (≈ 5 mercados) para los tests. | F1 | P0 | DAT-04, INF-06 | `polym4v data build` dos veces da el mismo hash. Valida con `pandera`. |
| DAT-06 | **En PR #3.** Split temporal por mercado (70/15/15) | F1 | P0 | DAT-05 | Test: hay intersección vacía entre splits y `max(ts_train) < min(ts_val) < min(ts_test)` |
| DAT-07 | **En PR #10.** `features/`: features de la sección 2.2 de la arquitectura y normalización ajustada solo con train | F2 | P0 | DAT-05 | Test de no-*lookahead*: truncar la serie en `t` no cambia las features en `≤ t` |
| DAT-08 | **En PR #7.** Notebook de EDA y una sección breve con sus hallazgos | F2 | P1 | DAT-05 | Notebook ejecutado y versionado, con ≥ 5 gráficos comentados |
| DAT-09 | Extensión a ETH y/o a la segunda familia de mercados | F3 | P2 | DAT-07 | Dataset `eth_*` construido y evaluación de transferencia BTC → ETH |
| DAT-10 | **Hecha el 31/10/2026:** BTC con 12 471 mercados y ETH con 12 149, sin errores ([11_descarga_de_datos.md](11_descarga_de_datos.md)). **Captura del crudo (S8, ADR-013):** historial de 1 minuto de los tokens YES y NO de todos los mercados horarios cerrados, con metadatos de cada petición y hash | F0 | P0 | DAT-01 | Una segunda ejecución no hace llamadas de red y el manifest lista cada archivo con su hash |
| DAT-11 | **En PR #9** (val y test; train se capturó después, ver la actualización de ADR-017). **Captura de trades (S4b, ADR-017):** trades taker públicos de los mercados de val y test, con el mismo esquema de crudo, caché y manifest que DAT-10 | F1 | P0 | DAT-10 | Una segunda ejecución no hace llamadas de red y el manifest lista cada archivo con su hash |

### R3 — Ingeniero del entorno y la recompensa

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| ENV-01 | **En PR #11:** `docs/notas/mdp.md`. Especificar el MDP por escrito (estado, acciones, transición, recompensa y fin de episodio) y revisarlo con el equipo | F0 | P0 | — | Sección "MDP" en `docs/notas/mdp.md` aprobada por R4 |
| ENV-02 | **En PR #11.** `Portfolio`: abrir y cerrar posiciones, mark-to-market y liquidación al resolver | F1 | P0 | ENV-01 | Tests unitarios de cada operación con valores calculados a mano |
| ENV-03 | **En PR #6.** `execution.py`: spread, slippage y comisión configurables | F1 | P0 | ENV-02 | Test: un ciclo compra-venta inmediata sin cambio de precio pierde exactamente los costos |
| ENV-04 | **En PR #11.** `PolymarketEnv` v1: `reset` (elige un mercado del split), `step` y espacios. Manejo de acciones inválidas. | F1 | P0 | ENV-02, DAT-05 (fixtures) | Pasa `gymnasium.utils.env_checker.check_env` |
| ENV-05 | **En PR #11** (`pnl`, `pnl_risk` y `terminal`) **y #23** (las seis variantes de la [investigación](ia/investigaciones/recompensas_rl_trading.md), aprobadas el 01/11/2026). `reward.py`: variantes `pnl`, `pnl_risk` y `terminal`, elegibles por config. `reward_components` en `info`. | F1 | P0 | ENV-04 | Test: con `pnl`, la suma de recompensas del episodio = PnL final / V_0 |
| ENV-06 | **En PR #15** (con la corrección de un caso que encontró `hypothesis` al ampliarla en #23). Suite de invariantes con `hypothesis`: conservación del dinero, `cash ≥ 0` y política aleatoria durante N episodios sin errores | F1 | P0 | ENV-05 | Pasa con ≥ 200 ejemplos generados |
| ENV-07 | **En PR #10, #11 y #17.** Integrar las features de R2 en la observación, wrapper de normalización y `render()` en modo texto | F2 | P0 | DAT-07 | El entorno con features reales pasa `check_env` y el test de no-*lookahead* |
| ENV-08 | **Ablación de la recompensa** (con R4): PPO con la lista aprobada el 01/11/2026, en dos etapas: `pnl`, `pnl_mid` y `terminal`; después `pnl_risk` (2 valores de `λ_dd`), `pnl_hold` y `utility` sobre la ganadora | F3 | P1 | AGT-04, ENV-05 | Tabla de ablación en `reports/` con 5 semillas por variante (3 si el tiempo no alcanza, y se dice en el reporte) |
| ENV-09 | Variante `execute_at: next` y análisis de sensibilidad a los costos (spread × 0, ×1, ×2) | F3 | P2 | ENV-07 | Gráfico de retorno frente al costo para el mejor agente |
| ENV-10 | **En PR #11.** **Tests de no-fuga (ADR-013):** mercado nulo donde el precio es el valor justo, y alteración de datos con `ts > t` | F1 | P0 | ENV-04 | En el mercado nulo ninguna política gana de forma significativa, y alterar el futuro no cambia la observación |

### R4 — Ingeniero de agentes RL

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| AGT-01 | Revisar la teoría y las librerías (SB3 PPO/DQN, d3rlpy CQL) y hacer un prototipo en `CartPole` para dominar la API | F0 | P1 | — | Notebook o script donde PPO resuelve CartPole |
| AGT-02 | **En PR #4 y #18.** Protocolo `Policy` y adaptadores `SB3Policy` y `D3rlpyPolicy` | F1 | P0 | INF-06 | Test: el adaptador devuelve acciones válidas para observaciones del espacio |
| AGT-03 | **En PR #12.** Baselines: `Random`, `NoTrade`, `Favorite`, `Momentum` y `MeanReversion` (con R5) | F1 | P0 | AGT-02 | Tests con escenarios de precio sintéticos donde el comportamiento esperado es obvio |
| AGT-04 | **En PR #19.** `train_sb3.py` para **PPO**: entornos vectorizados, `EvalCallback` en *val*, checkpoints, TensorBoard y guardado de la config resuelta | F2 | P0 | ENV-07, INF-05 | PPO entrena y **supera a `Random`** en val en una corrida corta |
| AGT-05 | **En PR #19.** **DQN** con el mismo script (ε-schedule, replay buffer, target network) | F2 | P0 | AGT-04 | DQN entrena y supera a `Random` en val |
| AGT-06 | **En PR #19.** Test de cordura: entorno sintético donde existe una estrategia óptima conocida (por ejemplo, el precio siempre converge al resultado). PPO y DQN deben aprenderla. | F2 | P0 | AGT-04 | Ambos alcanzan ≥ 90 % del retorno óptimo en el entorno sintético |
| AGT-07 | **En PR #20.** `collect-offline`: generar el dataset de transiciones con baselines ε-greedy sobre train | F3 | P0 | AGT-03 | Archivo `data/offline/*.h5` con ≥ 100k transiciones y su manifest |
| AGT-08 | **En PR #20.** Entrenar **Discrete CQL** y **Discrete BC** con d3rlpy y su adaptador `Policy` | F3 | P0 | AGT-07 | Ambos evaluados en val con `run_backtest` |
| AGT-09 | Ajuste de hiperparámetros acotado (≤ 20 configs por algoritmo, selección por val) | F3 | P1 | AGT-05, AGT-08 | Tabla de búsqueda en `reports/hparams.md` |
| AGT-10 | Entrenamiento final: 5 semillas por algoritmo con la mejor config, y modelos congelados | F3 | P0 | AGT-09 | `models/final/` completo, con config, semilla y commit en cada run |

### R5 — Evaluación, backtesting y demo

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| EVA-01 | **En PR #8.** Definir el protocolo de evaluación (métricas, splits, semillas y pruebas estadísticas) en `docs/notas/protocolo_eval.md` | F0 | P0 | — | Aprobado por el equipo **antes** de ver resultados (evita el *p-hacking*) |
| EVA-02 | **En PR #13.** `run_backtest(policy, env, markets)` → DataFrame de trayectorias con todas las claves de `info` | F1 | P0 | ENV-04, AGT-02 | Test: el `NoTrade` termina con `V_final = V_0` en todos los mercados |
| EVA-03 | **En PR #16.** `metrics.py`: retorno, Sharpe, max drawdown, win rate, operaciones, costos y % de acciones inválidas | F2 | P0 | EVA-02 | Tests con curvas de capital hechas a mano y su resultado conocido |
| EVA-04 | `stats.py`: IC por bootstrap y diferencia pareada agente frente a baseline | F2 | P0 | EVA-03 | Test: el IC contiene la media verdadera en datos simulados (≈ 95 %) |
| EVA-05 | **En PR #22.** `report.py` y `polym4v report`: tabla comparativa y figuras (curvas de capital, distribución del PnL, curvas de aprendizaje) | F2 | P0 | EVA-03 | Se genera `reports/val/` de forma automática con un solo comando |
| EVA-06 | **Evaluación final en test** (una sola vez, con los modelos congelados de AGT-10) | F4 | P0 | AGT-10 | `reports/test/` con la tabla final e IC 95 % |
| EVA-07 | **En PR #24.** Demo Streamlit v1: elegir mercado y agente, reproductor paso a paso, gráfico del precio con marcas y panel de estado | F3 | P0 | EVA-02 | La demo funciona con las trayectorias del mini-dataset |
| EVA-08 | Demo v2: comparar varios agentes en el mismo mercado y mostrar la curva de capital acumulada | F4 | P1 | EVA-07, EVA-06 | Muestra el mejor agente frente al mejor baseline en un mercado de test |
| EVA-09 | (CD) Desplegar la demo en Streamlit Community Cloud desde `proyecto` | F4 | P2 | EVA-08 | URL pública funcionando, enlazada desde el README |
| EVA-10 | Coordinar el informe final y la presentación (ver DOC-*) | F4 | P0 | EVA-06 | Entregados en la fecha |
| EVA-11 | **En PR #14.** **Validación de ejecuciones (S4a, ADR-017):** clasificar cada ejecución simulada como verificable o no con los trades de DAT-11 y repetir la evaluación en modo estricto | F2 | P0 | EVA-02, DAT-11 | El reporte de val y de test incluye el porcentaje de ejecuciones verificables y la clasificación de EVA-01 en los dos modos |

### Documento, slides y video (todos)

Alineadas con lo que pide el curso ([10_entrega_final.md](10_entrega_final.md)). Cada sección del
documento vive en `entregas/final/informe/`.

| ID | Tarea | Responsable | Fase | Depende de |
| ---- | ------- | ------------- | ------ | ------------ |
| DOC-01 | **Hecha el 31/10/2026.** Requisitos seleccionados en `docs/10_entrega_final.md` y estructura del documento con las secciones exigidas | R1 | F1 | — |
| DOC-02 | Descripción del problema | R1 + R5 | F4 | DOC-01 |
| DOC-03 | Análisis: datos, EDA, supuestos y riesgos | R2 | F4 | DAT-08 |
| DOC-04 | Propuesta de solución: por qué RL, MDP y recompensa | R3 + R4 | F4 | ENV-08 |
| DOC-05 | Descripción de la solución: datos, entorno, agentes, evaluación, ingeniería y proceso iterativo | Todos | F4 | AGT-10, INF-10 |
| DOC-06 | Herramientas aplicadas: las no vistas en clase en detalle, los prompts de IA y la evolución de la idea | R1 | F4 | DOC-12 |
| DOC-07 | Resultados (métricas) contra los baselines | R5 (con todos) | F4 | EVA-06 |
| DOC-08 | Conclusión | R5 (con todos) | F4 | DOC-07 |
| DOC-09 | Bibliografía verificada y con un solo formato | R4 + R5 | F4 | DOC-02 a DOC-08 |
| DOC-10 | Slides en HTML (máximo 10, flechas, `p` pantalla completa, `o` vista general y transiciones) y `generar_pdf.sh`. Se diseña al final, con un `DESIGN.md` | R5 + R1 | F4 | DOC-07 |
| DOC-11 | Video: funcionamiento, implementación y hallazgos | R5 | F4 | EVA-08 |
| DOC-12 | Historial de prompts con su evaluación, **durante todo el proyecto** (`docs/ia/`) | Todos; R1 consolida | F1–F4 | — |
| DOC-13 | Ensayo de la presentación en clase | Todos | F4 | DOC-10 |
| DOC-14 | Subir a Canvas el PDF del documento, con el enlace al repositorio, y el PDF de las slides | R1 | F4 | DOC-09, DOC-10 |

---

## 3. Grafo de dependencias críticas

La **ruta crítica** es la cadena que, si se atrasa, atrasa todo el proyecto:

```mermaid
flowchart LR
    DAT01["DAT-01 (hecha)"] --> DAT0203["DAT-02/03"] --> DAT04["DAT-04"] --> DAT05["DAT-05"] --> DAT07["DAT-07"]
    DAT07 --> ENV07["ENV-07"] --> AGT04["AGT-04"] --> AGT09["AGT-09"] --> AGT10["AGT-10"] --> EVA06["EVA-06"] --> DOC07["DOC-07"]
    ENV01["ENV-01"] --> ENV02["ENV-02"] --> ENV04["ENV-04"] --> ENV05["ENV-05"] --> ENV07
    DAT05 -. "fixtures desde el principio" .-> ENV04
```

**Cómo trabajar en paralelo sin esperar a nadie:**

- R3 y R4 desarrollan contra el **mini-dataset de fixtures** y un **entorno sintético**. No
  necesitan el dataset real para empezar.
- R5 desarrolla el backtest y las métricas con el baseline `Random` y con curvas de capital
  sintéticas.
- R1 publica los contratos (INF-06) **al inicio de F1**. Después de eso, cada módulo avanza solo.

---

## 4. Checklist por hito

**H0 (cierre de F0)**

- [x] Repo con CI en verde sobre la rama `proyecto`
- [x] Spike de datos documentado y familia de mercados elegida (ADR-004)
- [ ] MDP especificado (ENV-01) y protocolo de evaluación aprobado (EVA-01)
- [ ] Integrantes asignados a cada rol en [03_roles.md](03_roles.md)

**H1 (cierre de F1)**

- [ ] `polym4v data build` produce el dataset v1 con el split
- [ ] `PolymarketEnv` pasa `check_env` y la suite de invariantes
- [ ] El baseline `Random` corre sobre todos los mercados de val vía `run_backtest`

**H2 (cierre de F2)**

- [ ] PPO y DQN entrenados, y ambos superan a `Random` en val
- [ ] Test de cordura en el entorno sintético aprobado (AGT-06)
- [ ] Primera tabla comparativa en val (`reports/val/`)
- [ ] Pipeline E2E en la CI (INF-07)

**H3 (cierre de F3)**

- [ ] CQL y BC entrenados
- [ ] Ablación de la recompensa terminada
- [ ] Modelos finales congelados con 5 semillas (`models/final/`)
- [ ] Demo v1 funcionando

**H4 (cierre de F4)**

- [ ] Evaluación en test hecha una sola vez y documentada
- [ ] Demo v2, informe y presentación entregados
- [ ] Release `v1.0` con artefactos y reproducibilidad verificada por un tercero (INF-10)
