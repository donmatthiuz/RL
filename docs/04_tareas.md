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

- **Hecha:** está en `proyecto` y cumple su criterio.
- **Código mezclado / En curso:** el código está en `proyecto`, pero falta correr algo para cumplir
  el criterio (casi siempre, entrenar o evaluar en val).
- **Falta:** todavía no se empezó.

### Avance por rol

Al 09/11/2026, de 68 tareas: 59 hechas, 4 en curso, 1 omitida y 4 sin empezar. Todos los PR
(#1 a #45, salvo #38, que queda abierto) están mezclados en `proyecto`, y test ya se evaluó.

| Rol | Hechas | En curso | Faltan |
| --- | --- | --- | --- |
| R1 Josué | INF-01 a INF-09, EVA-12, EVA-13 y DOC-01 | INF-10 (la corre Mathew) | — |
| R2 Mathew | DAT-01 a DAT-08, DAT-10 y DAT-11 | — | DAT-09 (P2) |
| R3 Gustavo | ENV-01 a ENV-08 y ENV-10 | — | ENV-09 (P2) |
| R4 (lo asume R1) | AGT-02 a AGT-10, salvo AGT-01 (omitida) | — | — |
| R5 Carlos | EVA-01 a EVA-09 y EVA-11 | EVA-10 y DOC-11 (video, guion con OpenCode) | — |
| Todos (documento) | DOC-01 a DOC-10 | DOC-12, durante todo el proyecto | DOC-13 y DOC-14 |

AGT-01 (prototipo en CartPole) se omite: los adaptadores y el test de cordura de AGT-06 ya cubren
lo que buscaba.

### Resultado y lo que falta

**Resultado en test (EVA-06, #34, una sola vez):** ningún agente de RL le gana a `NoTrade`, el
baseline de referencia ([comparación](../reports/test/comparison.md)).

| Agente | Media de D (normal) | IC 98,75 % | Normal | Estricto |
| --- | --- | --- | --- | --- |
| PPO | −0,0005 | −0,0029 a +0,0018 | equivalente | equivalente |
| DQN | −0,0018 | −0,0082 a +0,0036 | equivalente | inconcluso |
| CQL | −0,0126 | −0,0263 a −0,0027 | inferior | inferior |
| BC | −0,0014 | −0,0050 a −0,0000 | peor, pero no relevante | equivalente |

- PPO y DQN aprendieron a operar en pocos mercados y quedan equivalentes a no operar, que es un
  resultado válido según D1. CQL parecía el mejor en val (+0,0109) y en test es inferior. BC opera
  en 23 mercados y su IC no es confiable.
- Todas las heurísticas pierden; la mejor es `fair_value`, con −0,0214.
- **Qué aprendió cada agente (EVA-12, exploratorio y fuera del protocolo):**
  [comportamiento en val](../reports/val/behavior.md) e
  [inspección posterior de test](../reports/test/inspection.md).
  - PPO compra casi siempre el favorito cerca del final (minuto mediano 54), el 88 % de las veces a
    más de 0,98. Desordenar las features del spot de Binance cambia el 96 % de sus compras, y
    desordenar el precio de Polymarket, el 51 %: decide sobre todo con lo lejos que está BTC de la
    apertura (`z`). Eso no demuestra que prediga mejor que el precio, que ya está calibrado en ese
    tramo (en val, en el minuto 55, el favorito a más de 0,99 ganó los 753 mercados).
  - Precisión no es rentabilidad: comprar a más de 0,98 cuesta 0,9988 por acción, así que hay que
    acertar el 99,88 % para no perder. PPO acertó el lado en 907 de 907 compras de val (IC 95 % de
    0,9958 a 1) y en 836 de 838 de test (0,9913 a 0,9993), con un neto de −27,23 USDC en test. Las
    dos pérdidas grandes de test (−20 y −18,4 USDC) son el mismo mercado en dos semillas: BTC estaba
    0,11 % bajo la apertura en el minuto 50 y terminó 0,03 % arriba.
  - CQL ganó en val con apuestas a precios bajos (long shots): sus 10 mejores operaciones suman
    +5 940 USDC, más que su total de +2 019. En test esas apuestas pierden −2 205 USDC. La caída es
    compatible con una estrategia de alta varianza elegida en val, pero test no identifica la causa
    por sí solo.
- Test abarca 76 días, no los 73 que supuso el protocolo. Solo cambia la MDE, que queda un 2 % más
  grande (conservadora); se declara en el informe.

Camino seguido: ablación (#30), umbrales de los baselines (#31), búsqueda de hiperparámetros (#32),
entrenamiento final y reporte de val (#33) y test (#34).

**Lo que falta:**

1. **Documento:** hecho. `Informe_final.pdf` (20 páginas, Mathew, 09/11/2026) cubre DOC-02 a
   DOC-09.
2. **Slides:** hechas (DOC-10). Mathew dejó 8 slides, el guion y el reparto de la exposición; R1
   agregó `generar_pdf.sh` y `PolyRL_presentacion.pdf`.
3. **Falta:** el video (DOC-11, guion con OpenCode), el ensayo con
   `REPARTO_EXPOSICION.md` (DOC-13) y subir a Canvas `Informe_final.pdf` y
   `PolyRL_presentacion.pdf` (DOC-14).
4. **Cierre técnico (R1):** hecho. El Release `v1.0` tiene los reportes, los modelos finales y las
   trayectorias (09/11/2026). `proyecto` no se lleva a `main` (decisión del 09/11/2026; el PR #38
   queda abierto).
5. **Mathew (R2):** la reproducción de INF-10 con la guía del README. La demo ya está publicada en
   Cloud Run (EVA-09, ADR-018).

### Decisiones del 02/11/2026

- **Revisión de PR por tiempo:** R2 no validó #1, #2, #3, #5, #7, #9 ni #10. El equipo los asumió
  correctos y R1 los mezcló; queda escrito en cada PR. Lo mismo con los PR que esperaban a R4 o a
  R5 y con #21 y #25. Lo que aparezca en una revisión posterior va en un PR de corrección.
- **Roles:** R1 asume R4, que no tenía dueño. R5 es Carlos.
- **Protocolo congelado (#8):** E1 (`Δ_min` = 1 % del stake por mercado), E2 (`NoTrade`, salvo que
  una heurística le gane en val con el IC 95 % por encima de cero) y la clasificación simétrica, con
  "peor, pero no relevante", a partir de la revisión de R5. Cambiarlo exige un ADR. Val está
  abierto.
- **Modo de entrenamiento:** normal; el modo estricto se usa solo al evaluar, como pide el
  protocolo (actualización de ADR-017).
- **Cómputo:** se entrena en CPU, varias semillas en paralelo. Medido el 02/11/2026 con torch
  2.15.0, la GPU (RTX 5070, CUDA 13.2) fue más lenta con estas redes de 64 × 64:

  | Medición | CPU | GPU |
  | --- | --- | --- |
  | PPO, entrenar (pasos/s) | 3 463 | 602 |
  | PPO, evaluar paso a paso (pasos/s) | 9 136 | 1 332 |
  | DQN, entrenar (pasos/s) | 2 585 | 680 |
  | CQL, pasos de gradiente/s (batch 256) | 337 | 110 |

- **Etapa B de la ablación:** `λ_dd` en 0,5 y 1, `λ_hold` = 2,5e-5 por paso (30 minutos con
  posición cuestan lo mismo que entrar) y `a` = 1. `λ_dd = 1` ganó en el borde de lo probado, y no
  se prueba más: subirlo empuja a no operar nunca, y probar más en val infla lo elegido.
- **AGT-09:** PPO lr {1e-4, 3e-4} × `ent_coef` {0; 0,01} × red {64×64, 128×128}; DQN lr × exploración
  {0,1; 0,3} × `target_update_interval` {2000, 10000}; CQL `alpha` {0,5; 1; 4} × lr {3e-5, 1e-4};
  BC lr {3e-4, 1e-3, 3e-3}. Dos semillas por punto; se elige en val.
- **Demo:** `streamlit` queda en el grupo `demo` instalado por defecto, así sus tests corren en la
  CI (#24).

Las decisiones del simulador (ADR-016 y ADR-017), la lista de la ablación (01/11/2026) y las
decisiones previas al diseño (D1 a D9, en
[decisiones_previas_al_diseno.md](notas/decisiones_previas_al_diseno.md)) siguen vigentes.

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
| R1 Infra | INF-01 a 04 | INF-05, 06 | INF-07 E2E | INF-08 | INF-09, 10, EVA-12, 13 |
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
| INF-06 | **Hecha el 02/11/2026 (#1, #4 y #11).** Definir los **contratos** como código: `schemas.py` (con R2), protocolo `Policy` (con R4) y claves de `info` (con R3) | F1 | P0 | INF-05 | Revisado y aceptado por R2, R3 y R4 antes de subirlo |
| INF-07 | **Hecha el 02/11/2026 (#21)**, con `argparse`. CLI `typer` (`data build`, `train`, `collect-offline`, `evaluate`, `report`) y test de integración E2E sobre el mini-dataset | F2 | P0 | DAT-05, ENV-05, AGT-03, EVA-02 | `pytest -m integration` corre todo el pipeline en < 2 min |
| INF-08 | **Hecha el 02/11/2026 (#25)**; el nightly no corre en GitHub, porque `proyecto` no se lleva a `main` (09/11/2026): se corre en local con `make nightly`. Job *smoke-train* en la CI y workflow `nightly.yml` (tests `slow` y backtest corto) | F3 | P1 | INF-07 | El nightly corre por `workflow_dispatch` y por cron |
| INF-09 | **Hecha el 09/11/2026 (#37 y el tag `v1.0`):** el Release trae `reportes-v1.0.zip`, `modelos-v1.0.zip` y `trayectorias-v1.0.zip`. El reporte no se recalcula en la CI, porque los datos y los modelos no se versionan: el Release publica `reports/` y R1 adjunta los modelos y las trayectorias con `make release-modelos` ([05_testing.md](05_testing.md), sección 6). `release.yml` (CD): en un tag `v*` genera el reporte y adjunta las tablas, figuras y modelos finales al GitHub Release | F4 | P1 | EVA-06 | El tag `v1.0` produce un Release con sus artefactos |
| INF-10 | **Guía en el README (#37); la corre Mathew.** Ensayo de R1 el 09/11/2026 en un clon limpio: PPO s0 en val da exactamente el `total_pnl` del reporte (77,99 en 1 861 mercados). Revisión de reproducibilidad: un integrante que no participó clona el repo y reproduce un resultado siguiendo el README | F4 | P0 | H3 | El resultado coincide dentro de la tolerancia (± IC) |

### R2 — Ingeniero de datos

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| DAT-01 | **Hecha el 30/10/2026: ver [spike](notas/spike_datos.md) y ADR-004, ADR-007 a ADR-009.** **Spike de APIs:** probar Gamma, CLOB `prices-history` y Binance. Medir la granularidad real en mercados cerrados, los límites de rate y los campos disponibles. Elegir la familia de mercados. | F0 | P0 | — | Nota en `docs/notas/spike_datos.md`, más un ADR con la familia de mercados y la granularidad elegidas |
| DAT-02 | **Hecha el 31/10/2026 dentro de DAT-10:** `capture_series` lista los eventos cerrados de Gamma por serie, con paginación, y sus tests usan una fuente falsa, sin red. `GammaClient`: listar mercados cerrados filtrados por tag o texto, con paginación | F1 | P0 | DAT-01, INF-01 | Tests con respuestas grabadas (`responses`), sin red |
| DAT-03 | **Hecha el 02/11/2026 (#2).** `ClobClient` y `BinanceClient`, con caché en disco, reintentos y rate limiting | F1 | P0 | DAT-01 | Una segunda ejecución no hace llamadas de red (test con contador) |
| DAT-04 | **Hecha el 02/11/2026 (#5 y #10).** Limpieza, re-muestreo a una grilla fija (solo *forward-fill*), alineación con el spot y filtros de calidad | F1 | P0 | DAT-02, DAT-03 | Test: ningún valor en `t` se deriva de datos con `ts > t` |
| DAT-05 | **Hecha el 02/11/2026 (#5 y #10).** `build_dataset.py`: `markets.parquet`, `steps.parquet` y `manifest.json` con hash. **Mini-dataset de fixtures** (≈ 5 mercados) para los tests. | F1 | P0 | DAT-04, INF-06 | `polym4v data build` dos veces da el mismo hash. Valida con `pandera`. |
| DAT-06 | **Hecha el 02/11/2026 (#3).** Split temporal por mercado (70/15/15) | F1 | P0 | DAT-05 | Test: hay intersección vacía entre splits y `max(ts_train) < min(ts_val) < min(ts_test)` |
| DAT-07 | **Hecha el 02/11/2026 (#10).** `features/`: features de la sección 2.2 de la arquitectura y normalización ajustada solo con train | F2 | P0 | DAT-05 | Test de no-*lookahead*: truncar la serie en `t` no cambia las features en `≤ t` |
| DAT-08 | **Hecha el 02/11/2026 (#7).** Notebook de EDA y una sección breve con sus hallazgos | F2 | P1 | DAT-05 | Notebook ejecutado y versionado, con ≥ 5 gráficos comentados |
| DAT-09 | Extensión a ETH y/o a la segunda familia de mercados | F3 | P2 | DAT-07 | Dataset `eth_*` construido y evaluación de transferencia BTC → ETH |
| DAT-10 | **Hecha el 31/10/2026:** BTC con 12 471 mercados y ETH con 12 149, sin errores ([11_descarga_de_datos.md](11_descarga_de_datos.md)). **Captura del crudo (S8, ADR-013):** historial de 1 minuto de los tokens YES y NO de todos los mercados horarios cerrados, con metadatos de cada petición y hash | F0 | P0 | DAT-01 | Una segunda ejecución no hace llamadas de red y el manifest lista cada archivo con su hash |
| DAT-11 | **Hecha el 02/11/2026 (#9)**: val y test, y train capturado el 01/11/2026 (actualización de ADR-017). **Captura de trades (S4b, ADR-017):** trades taker públicos de los mercados de val y test, con el mismo esquema de crudo, caché y manifest que DAT-10 | F1 | P0 | DAT-10 | Una segunda ejecución no hace llamadas de red y el manifest lista cada archivo con su hash |

### R3 — Ingeniero del entorno y la recompensa

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| ENV-01 | **Hecha el 02/11/2026 (#11):** `docs/notas/mdp.md`, aprobado por R1 como R4. Especificar el MDP por escrito (estado, acciones, transición, recompensa y fin de episodio) y revisarlo con el equipo | F0 | P0 | — | Sección "MDP" en `docs/notas/mdp.md` aprobada por R4 |
| ENV-02 | **Hecha el 02/11/2026 (#11).** `Portfolio`: abrir y cerrar posiciones, mark-to-market y liquidación al resolver | F1 | P0 | ENV-01 | Tests unitarios de cada operación con valores calculados a mano |
| ENV-03 | **Hecha el 01/11/2026 (#6).** `execution.py`: spread, slippage y comisión configurables | F1 | P0 | ENV-02 | Test: un ciclo compra-venta inmediata sin cambio de precio pierde exactamente los costos |
| ENV-04 | **Hecha el 02/11/2026 (#11).** `PolymarketEnv` v1: `reset` (elige un mercado del split), `step` y espacios. Manejo de acciones inválidas. | F1 | P0 | ENV-02, DAT-05 (fixtures) | Pasa `gymnasium.utils.env_checker.check_env` |
| ENV-05 | **Hecha el 02/11/2026 (#11 y #23)**, con las seis variantes de la [investigación](ia/investigaciones/recompensas_rl_trading.md) aprobadas el 01/11/2026. `reward.py`: variantes `pnl`, `pnl_risk` y `terminal`, elegibles por config. `reward_components` en `info`. | F1 | P0 | ENV-04 | Test: con `pnl`, la suma de recompensas del episodio = PnL final / V_0 |
| ENV-06 | **Hecha el 02/11/2026 (#15 y #23).** Suite de invariantes con `hypothesis`: conservación del dinero, `cash ≥ 0` y política aleatoria durante N episodios sin errores | F1 | P0 | ENV-05 | Pasa con ≥ 200 ejemplos generados |
| ENV-07 | **Hecha el 02/11/2026 (#10, #11 y #17).** Integrar las features de R2 en la observación, wrapper de normalización y `render()` en modo texto | F2 | P0 | DAT-07 | El entorno con features reales pasa `check_env` y el test de no-*lookahead* |
| ENV-08 | **Hecha el 02/11/2026 (#30):** gana `pnl_risk` con base `pnl_mid` y `λ_dd = 1` ([tabla](../reports/val/ablation.md)). **Ablación de la recompensa** (con R4): PPO con la lista aprobada el 01/11/2026, en dos etapas: `pnl`, `pnl_mid` y `terminal`; después `pnl_risk` (2 valores de `λ_dd`), `pnl_hold` y `utility` sobre la ganadora | F3 | P1 | AGT-04, ENV-05 | Tabla de ablación en `reports/` con 5 semillas por variante (3 si el tiempo no alcanza, y se dice en el reporte) |
| ENV-09 | Variante `execute_at: next` y análisis de sensibilidad a los costos (spread × 0, ×1, ×2) | F3 | P2 | ENV-07 | Gráfico de retorno frente al costo para el mejor agente |
| ENV-10 | **Hecha el 02/11/2026 (#11).** **Tests de no-fuga (ADR-013):** mercado nulo donde el precio es el valor justo, y alteración de datos con `ts > t` | F1 | P0 | ENV-04 | En el mercado nulo ninguna política gana de forma significativa, y alterar el futuro no cambia la observación |

### R4 — Ingeniero de agentes RL

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| AGT-01 | **Se omite (02/11/2026):** los adaptadores y el test de cordura de AGT-06 ya cubren el dominio de las librerías. Revisar la teoría y las librerías (SB3 PPO/DQN, d3rlpy CQL) y hacer un prototipo en `CartPole` para dominar la API | F0 | P1 | — | Notebook o script donde PPO resuelve CartPole |
| AGT-02 | **Hecha el 02/11/2026 (#4 y #18).** Protocolo `Policy` y adaptadores `SB3Policy` y `D3rlpyPolicy` | F1 | P0 | INF-06 | Test: el adaptador devuelve acciones válidas para observaciones del espacio |
| AGT-03 | **Hecha el 02/11/2026 (#12).** Baselines: `Random`, `NoTrade`, `Favorite`, `Momentum` y `MeanReversion` (con R5) | F1 | P0 | AGT-02 | Tests con escenarios de precio sintéticos donde el comportamiento esperado es obvio |
| AGT-04 | **Hecha el 02/11/2026 (#19 y #33):** PPO queda en +0,0012 en val y `Random` en −1,52. `train_sb3.py` para **PPO**: entornos vectorizados, `EvalCallback` en *val*, checkpoints, TensorBoard y guardado de la config resuelta | F2 | P0 | ENV-07, INF-05 | PPO entrena y **supera a `Random`** en val en una corrida corta |
| AGT-05 | **Hecha el 02/11/2026 (#19 y #33):** DQN queda en −0,0015 en val y `Random` en −1,52. **DQN** con el mismo script (ε-schedule, replay buffer, target network) | F2 | P0 | AGT-04 | DQN entrena y supera a `Random` en val |
| AGT-06 | **Hecha el 02/11/2026 (#19).** Test de cordura: entorno sintético donde existe una estrategia óptima conocida (por ejemplo, el precio siempre converge al resultado). PPO y DQN deben aprenderla. | F2 | P0 | AGT-04 | Ambos alcanzan ≥ 90 % del retorno óptimo en el entorno sintético |
| AGT-07 | **Hecha el 02/11/2026 (#20).** `collect-offline`: generar el dataset de transiciones con baselines ε-greedy sobre train | F3 | P0 | AGT-03 | Archivo `data/offline/*.h5` con ≥ 100k transiciones y su manifest |
| AGT-08 | **Hecha el 02/11/2026 (#20 y #33):** CQL y BC evaluados en val. Entrenar **Discrete CQL** y **Discrete BC** con d3rlpy y su adaptador `Policy` | F3 | P0 | AGT-07 | Ambos evaluados en val con `run_backtest` |
| AGT-09 | **Hecha el 02/11/2026 (#32):** 25 configs × 2 semillas ([tabla](../reports/hparams.md)). Ajuste de hiperparámetros acotado (≤ 20 configs por algoritmo, selección por val) | F3 | P1 | AGT-05, AGT-08 | Tabla de búsqueda en `reports/hparams.md` |
| AGT-10 | **Hecha el 02/11/2026 (#32 y #33):** `configs/final/`, 5 semillas por algoritmo en `models/final/`. Entrenamiento final: 5 semillas por algoritmo con la mejor config, y modelos congelados | F3 | P0 | AGT-09 | `models/final/` completo, con config, semilla y commit en cada run |

### R5 — Evaluación, backtesting y demo

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
| ---- | ------- | ------ | ------ | ------------ | ------------------------ |
| EVA-01 | **Hecha el 02/11/2026 (#8)**: protocolo congelado, con E1, E2 y la clasificación simétrica. Definir el protocolo de evaluación (métricas, splits, semillas y pruebas estadísticas) en `docs/notas/protocolo_eval.md` | F0 | P0 | — | Aprobado por el equipo **antes** de ver resultados (evita el *p-hacking*) |
| EVA-02 | **Hecha el 02/11/2026 (#13).** `run_backtest(policy, env, markets)` → DataFrame de trayectorias con todas las claves de `info` | F1 | P0 | ENV-04, AGT-02 | Test: el `NoTrade` termina con `V_final = V_0` en todos los mercados |
| EVA-03 | **Hecha el 02/11/2026 (#16).** `metrics.py`: retorno, Sharpe, max drawdown, win rate, operaciones, costos y % de acciones inválidas | F2 | P0 | EVA-02 | Tests con curvas de capital hechas a mano y su resultado conocido |
| EVA-04 | **Hecha el 02/11/2026 (#26 y #27, R5).** `stats.py`: IC por bootstrap y diferencia pareada agente frente a baseline | F2 | P0 | EVA-03 | Test: el IC contiene la media verdadera en datos simulados (≈ 95 %) |
| EVA-05 | **Hecha el 02/11/2026 (#22).** `report.py` y `polym4v report`: tabla comparativa y figuras (curvas de capital, distribución del PnL, curvas de aprendizaje) | F2 | P0 | EVA-03 | Se genera `reports/val/` de forma automática con un solo comando |
| EVA-06 | **Hecha el 02/11/2026 (#34), una sola vez:** [reports/test/](../reports/test/comparison.md). **Evaluación final en test** (una sola vez, con los modelos congelados de AGT-10) | F4 | P0 | AGT-10 | `reports/test/` con la tabla final e IC 95 % |
| EVA-07 | **Hecha el 02/11/2026 (#24).** Demo Streamlit v1: elegir mercado y agente, reproductor paso a paso, gráfico del precio con marcas y panel de estado | F3 | P0 | EVA-02 | La demo funciona con las trayectorias del mini-dataset |
| EVA-08 | **Hecha el 09/11/2026 (#28 y #36).** La demo abre test con el mejor agente del protocolo (PPO, con su semilla mediana) frente a `NoTrade`, en el primer mercado donde operó. Demo v2: comparar varios agentes en el mismo mercado y mostrar la curva de capital acumulada | F4 | P1 | EVA-07, EVA-06 | Muestra el mejor agente frente al mejor baseline en un mercado de test |
| EVA-09 | **Hecha el 09/11/2026 (#36 y #44):** publicada en Cloud Run (ADR-018) en <https://polyrl-demo-248394644314.us-east1.run.app>, con `make deploy-gcp` desde `proyecto`. Revisada en la nube: las cuatro páginas abren sin errores y la reproducción responde. (CD) Desplegar la demo pública desde `proyecto` | F4 | P2 | EVA-08 | URL pública funcionando, enlazada desde el README |
| EVA-10 | **En curso:** informe y slides listos; faltan video, ensayo y Canvas. Coordinar el informe final y la presentación (ver DOC-*) | F4 | P0 | EVA-06 | Entregados en la fecha |
| EVA-11 | **Hecha el 02/11/2026 (#14, #33 y #34):** los reportes de val y test traen el porcentaje de ejecuciones verificadas y la clasificación en los dos modos. **Validación de ejecuciones (S4a, ADR-017):** clasificar cada ejecución simulada como verificable o no con los trades de DAT-11 y repetir la evaluación en modo estricto | F2 | P0 | EVA-02, DAT-11 | El reporte de val y de test incluye el porcentaje de ejecuciones verificables y la clasificación de EVA-01 en los dos modos |
| EVA-12 | **Hecha el 02/11/2026 (#35); exploratoria, fuera del protocolo (R1).** Análisis del comportamiento de los agentes (XAI): mapa de decisiones, precisión contra rentabilidad, calibración del precio e importancia de features por permutación, en val; en test, solo la descripción de las trayectorias de EVA-06 | F4 | P1 | EVA-06 | `make behavior` genera `reports/val/behavior.md` y `reports/test/inspection.md` sin volver a evaluar test |
| EVA-13 | **Hecha el 09/11/2026 (#40 y #41, R1).** Diseño de la demo con la identidad de `entregas/final/presentacion/DESIGN.md`: inicio, simulación minuto a minuto con BTC, precio YES, narración y botones de reproducción, comparación con el veredicto del protocolo y una guía del mercado, el entorno, las políticas y los datos | F4 | P1 | EVA-08 | La demo abre sin errores en local y con la muestra de Cloud, y sus tests cubren la reproducción, el cierre y la elección del protocolo |

### Documento, slides y video (todos)

Alineadas con lo que pide el curso ([10_entrega_final.md](10_entrega_final.md)). Cada sección del
documento vive en `entregas/final/informe/`.

| ID | Tarea | Responsable | Fase | Depende de |
| ---- | ------- | ------------- | ------ | ------------ |
| DOC-01 | **Hecha el 31/10/2026.** Requisitos seleccionados en `docs/10_entrega_final.md` y estructura del documento con las secciones exigidas | R1 | F1 | — |
| DOC-02 | **Hecha el 09/11/2026 (Mathew, `Informe_final.md`).** Descripción del problema | R1 + R5 | F4 | DOC-01 |
| DOC-03 | **Hecha el 09/11/2026 (Mathew).** Análisis: datos, EDA, supuestos y riesgos | R2 | F4 | DAT-08 |
| DOC-04 | **Hecha el 09/11/2026:** borrador de R3 (03/11/2026) integrado por Mathew en el informe final. Propuesta de solución: por qué RL, MDP y recompensa | R3 + R4 | F4 | ENV-08 |
| DOC-05 | **Hecha el 09/11/2026 (Mathew).** Descripción de la solución: datos, entorno, agentes, evaluación, ingeniería y proceso iterativo | Todos | F4 | AGT-10, INF-10 |
| DOC-06 | **Hecha el 09/11/2026 (Mathew).** Herramientas aplicadas: las no vistas en clase en detalle, los prompts de IA y la evolución de la idea | R1 | F4 | DOC-12 |
| DOC-07 | **Hecha el 09/11/2026 (Mathew).** Resultados (métricas) contra los baselines | R5 (con todos) | F4 | EVA-06 |
| DOC-08 | **Hecha el 09/11/2026 (Mathew).** Conclusión | R5 (con todos) | F4 | DOC-07 |
| DOC-09 | **Hecha el 09/11/2026 (Mathew).** Bibliografía verificada y con un solo formato | R4 + R5 | F4 | DOC-02 a DOC-08 |
| DOC-10 | **Hecha el 09/11/2026:** base y slides 1 a 3 (#42 y #43, R1); 8 slides en estilo Laboratorio nocturno, guion y reparto (Mathew); `generar_pdf.sh` y `PolyRL_presentacion.pdf` (R1). Slides en HTML (máximo 10, flechas, `p` pantalla completa, `o` vista general y transiciones) y `generar_pdf.sh`. Se diseña al final, con un `DESIGN.md` | R5 + R1 | F4 | DOC-07 |
| DOC-11 | **En curso:** guion corto con OpenCode en `entregas/final/video/`. Video: funcionamiento, implementación y hallazgos | R5 | F4 | EVA-08 |
| DOC-12 | **En curso; al día al 09/11/2026 (P1 a P25).** Historial de prompts con su evaluación, **durante todo el proyecto** (`docs/ia/`) | Todos; R1 consolida | F1–F4 | — |
| DOC-13 | Reparto listo en `entregas/final/presentacion/REPARTO_EXPOSICION.md`. Ensayo de la presentación en clase | Todos | F4 | DOC-10 |
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
- [x] MDP especificado (ENV-01) y protocolo de evaluación aprobado (EVA-01)
- [x] Integrantes asignados a cada rol en [03_roles.md](03_roles.md) (R1 asume R4)

**H1 (cierre de F1)**

- [x] `polym4v data build` produce el dataset v1 con el split
- [x] `PolymarketEnv` pasa `check_env` y la suite de invariantes
- [ ] El baseline `Random` corre sobre todos los mercados de val vía `run_backtest`

**H2 (cierre de F2)**

- [x] PPO y DQN entrenados, y ambos superan a `Random` en val
- [x] Test de cordura en el entorno sintético aprobado (AGT-06)
- [x] Primera tabla comparativa en val (`reports/val/`)
- [x] Pipeline E2E en la CI (INF-07)

**H3 (cierre de F3)**

- [x] CQL y BC entrenados
- [x] Ablación de la recompensa terminada
- [x] Modelos finales congelados con 5 semillas (`models/final/`)
- [x] Demo v1 funcionando

**H4 (cierre de F4)**

- [x] Evaluación en test hecha una sola vez y documentada
- [ ] Demo v2, informe y presentación entregados
- [ ] Release `v1.0` con artefactos y reproducibilidad verificada por un tercero (INF-10)
