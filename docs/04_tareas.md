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

## 1. Fases e hitos

| Fase | Objetivo | Hito de cierre |
|------|----------|----------------|
| **F0 — Setup** | Repo, herramientas, CI y validar las APIs | **H0:** CI en verde, spike de datos con su conclusión |
| **F1 — Datos y entorno** | Dataset v1 y `PolymarketEnv` v1 testeado | **H1:** un baseline corre episodios de extremo a extremo sobre datos reales |
| **F2 — Agentes online** | Baselines, PPO y DQN entrenados, primer backtest | **H2:** primera tabla comparativa en *val* |
| **F3 — Offline RL y ajuste** | CQL/BC, ablación de la recompensa, ajuste de hiperparámetros, 5 semillas | **H3:** modelos finales congelados |
| **F4 — Evaluación final y demo** | Evaluación en test, demo, informe y presentación | **H4:** release `v1.0` y entrega |

```
Fase:        F0            F1                F2                F3               F4
R1 Infra     [INF-01..04 ][INF-05/06       ][INF-07 E2E      ][INF-08         ][INF-09/10 ]
R2 Datos     [DAT-01     ][DAT-02..06      ][DAT-07/08       ][DAT-09 ETH (P2)][DOC       ]
R3 Entorno   [ENV-01     ][ENV-02..06      ][ENV-07          ][ENV-08 ablación][DOC       ]
R4 Agentes   [AGT-01     ][AGT-02/03       ][AGT-04..06      ][AGT-07..10     ][DOC       ]
R5 Eval/Demo [EVA-01     ][EVA-02          ][EVA-03..05      ][EVA-06/07      ][EVA-08..10]
Hitos:            H0            H1                H2                H3              H4
```

---

## 2. Tareas por rol

### R1 — Líder técnico e integrador

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
|----|-------|------|------|------------|------------------------|
| INF-01 | Crear la estructura del repo, `pyproject.toml` con `uv`, el paquete `polyrl` instalable y `src/` layout | F0 | P0 | — | `uv sync && uv run python -c "import polyrl"` funciona en una máquina limpia |
| INF-02 | Configurar `ruff`, `mypy` (permisivo) y `pre-commit` | F0 | P0 | INF-01 | `pre-commit run --all-files` pasa |
| INF-03 | Workflow `ci.yml`: lint, tests y cobertura en cada push a `proyecto` | F0 | P0 | INF-02 | La CI corre en un push de prueba y marca en rojo el commit si falla |
| INF-04 | Tablero en GitHub Projects con todas las tareas de este documento | F0 | P0 | — | Cada tarea es un issue con su rol, fase y prioridad |
| INF-05 | `utils/`: `config.py` (pydantic), `seeding.py`, `logging.py`, `paths.py` | F1 | P0 | INF-01 | Tests unitarios. La misma semilla da resultados idénticos. |
| INF-06 | Definir los **contratos** como código: `schemas.py` (con R2), protocolo `Policy` (con R4) y claves de `info` (con R3) | F1 | P0 | INF-05 | Revisado y aceptado por R2, R3 y R4 antes de subirlo |
| INF-07 | CLI `typer` (`data build`, `train`, `collect-offline`, `evaluate`, `report`) y test de integración E2E sobre el mini-dataset | F2 | P0 | DAT-05, ENV-05, AGT-03, EVA-02 | `pytest -m integration` corre todo el pipeline en < 2 min |
| INF-08 | Job *smoke-train* en la CI y workflow `nightly.yml` (tests `slow` y backtest corto) | F3 | P1 | INF-07 | El nightly corre por `workflow_dispatch` y por cron |
| INF-09 | `release.yml` (CD): en un tag `v*` genera el reporte y adjunta las tablas, figuras y modelos finales al GitHub Release | F4 | P1 | EVA-06 | El tag `v1.0` produce un Release con sus artefactos |
| INF-10 | Revisión de reproducibilidad: un integrante que no participó clona el repo y reproduce un resultado siguiendo el README | F4 | P0 | H3 | El resultado coincide dentro de la tolerancia (± IC) |

### R2 — Ingeniero de datos

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
|----|-------|------|------|------------|------------------------|
| DAT-01 | **Spike de APIs:** probar Gamma, CLOB `prices-history` y Binance. Medir la granularidad real en mercados cerrados, los límites de rate y los campos disponibles. Elegir la familia de mercados. | F0 | P0 | — | Nota en `docs/notas/spike_datos.md`, más un ADR con la familia de mercados y la granularidad elegidas |
| DAT-02 | `GammaClient`: listar mercados cerrados filtrados por tag o texto, con paginación | F1 | P0 | DAT-01, INF-01 | Tests con respuestas grabadas (`responses`), sin red |
| DAT-03 | `ClobClient` y `BinanceClient`, con caché en disco, reintentos y rate limiting | F1 | P0 | DAT-01 | Una segunda ejecución no hace llamadas de red (test con contador) |
| DAT-04 | Limpieza, re-muestreo a una grilla fija (solo *forward-fill*), alineación con el spot y filtros de calidad | F1 | P0 | DAT-02, DAT-03 | Test: ningún valor en `t` se deriva de datos con `ts > t` |
| DAT-05 | `build_dataset.py`: `markets.parquet`, `steps.parquet` y `manifest.json` con hash. **Mini-dataset de fixtures** (≈ 5 mercados) para los tests. | F1 | P0 | DAT-04, INF-06 | `polyrl data build` dos veces da el mismo hash. Valida con `pandera`. |
| DAT-06 | Split temporal por mercado (70/15/15) | F1 | P0 | DAT-05 | Test: hay intersección vacía entre splits y `max(ts_train) < min(ts_val) < min(ts_test)` |
| DAT-07 | `features/`: features de la sección 2.2 de la arquitectura y normalización ajustada solo con train | F2 | P0 | DAT-05 | Test de no-*lookahead*: truncar la serie en `t` no cambia las features en `≤ t` |
| DAT-08 | Notebook de EDA y una sección breve con sus hallazgos | F2 | P1 | DAT-05 | Notebook ejecutado y versionado, con ≥ 5 gráficos comentados |
| DAT-09 | Extensión a ETH y/o a la segunda familia de mercados | F3 | P2 | DAT-07 | Dataset `eth_*` construido y evaluación de transferencia BTC → ETH |

### R3 — Ingeniero del entorno y la recompensa

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
|----|-------|------|------|------------|------------------------|
| ENV-01 | Especificar el MDP por escrito (estado, acciones, transición, recompensa y fin de episodio) y revisarlo con el equipo | F0 | P0 | — | Sección "MDP" en `docs/notas/mdp.md` aprobada por R4 |
| ENV-02 | `Portfolio`: abrir y cerrar posiciones, mark-to-market y liquidación al resolver | F1 | P0 | ENV-01 | Tests unitarios de cada operación con valores calculados a mano |
| ENV-03 | `execution.py`: spread, slippage y comisión configurables | F1 | P0 | ENV-02 | Test: un ciclo compra-venta inmediata sin cambio de precio pierde exactamente los costos |
| ENV-04 | `PolymarketEnv` v1: `reset` (elige un mercado del split), `step` y espacios. Manejo de acciones inválidas. | F1 | P0 | ENV-02, DAT-05 (fixtures) | Pasa `gymnasium.utils.env_checker.check_env` |
| ENV-05 | `reward.py`: variantes `pnl`, `pnl_risk` y `terminal`, elegibles por config. `reward_components` en `info`. | F1 | P0 | ENV-04 | Test: con `pnl`, la suma de recompensas del episodio = PnL final / V_0 |
| ENV-06 | Suite de invariantes con `hypothesis`: conservación del dinero, `cash ≥ 0` y política aleatoria durante N episodios sin errores | F1 | P0 | ENV-05 | Pasa con ≥ 200 ejemplos generados |
| ENV-07 | Integrar las features de R2 en la observación, wrapper de normalización y `render()` en modo texto | F2 | P0 | DAT-07 | El entorno con features reales pasa `check_env` y el test de no-*lookahead* |
| ENV-08 | **Ablación de la recompensa** (con R4): PPO con `pnl`, `pnl_risk` (2–3 valores de `λ_dd`) y `terminal` | F3 | P1 | AGT-04 | Tabla de ablación en `reports/` con ≥ 3 semillas por variante |
| ENV-09 | Variante `execute_at: next` y análisis de sensibilidad a los costos (spread × 0, ×1, ×2) | F3 | P2 | ENV-07 | Gráfico de retorno frente al costo para el mejor agente |

### R4 — Ingeniero de agentes RL

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
|----|-------|------|------|------------|------------------------|
| AGT-01 | Revisar la teoría y las librerías (SB3 PPO/DQN, d3rlpy CQL) y hacer un prototipo en `CartPole` para dominar la API | F0 | P1 | — | Notebook o script donde PPO resuelve CartPole |
| AGT-02 | Protocolo `Policy` y adaptadores `SB3Policy` y `D3rlpyPolicy` | F1 | P0 | INF-06 | Test: el adaptador devuelve acciones válidas para observaciones del espacio |
| AGT-03 | Baselines: `Random`, `NoTrade`, `Favorite`, `Momentum` y `MeanReversion` (con R5) | F1 | P0 | AGT-02 | Tests con escenarios de precio sintéticos donde el comportamiento esperado es obvio |
| AGT-04 | `train_sb3.py` para **PPO**: entornos vectorizados, `EvalCallback` en *val*, checkpoints, TensorBoard y guardado de la config resuelta | F2 | P0 | ENV-07, INF-05 | PPO entrena y **supera a `Random`** en val en una corrida corta |
| AGT-05 | **DQN** con el mismo script (ε-schedule, replay buffer, target network) | F2 | P0 | AGT-04 | DQN entrena y supera a `Random` en val |
| AGT-06 | Test de cordura: entorno sintético donde existe una estrategia óptima conocida (por ejemplo, el precio siempre converge al resultado). PPO y DQN deben aprenderla. | F2 | P0 | AGT-04 | Ambos alcanzan ≥ 90 % del retorno óptimo en el entorno sintético |
| AGT-07 | `collect-offline`: generar el dataset de transiciones con baselines ε-greedy sobre train | F3 | P0 | AGT-03 | Archivo `data/offline/*.h5` con ≥ 100k transiciones y su manifest |
| AGT-08 | Entrenar **Discrete CQL** y **Discrete BC** con d3rlpy y su adaptador `Policy` | F3 | P0 | AGT-07 | Ambos evaluados en val con `run_backtest` |
| AGT-09 | Ajuste de hiperparámetros acotado (≤ 20 configs por algoritmo, selección por val) | F3 | P1 | AGT-05, AGT-08 | Tabla de búsqueda en `reports/hparams.md` |
| AGT-10 | Entrenamiento final: 5 semillas por algoritmo con la mejor config, y modelos congelados | F3 | P0 | AGT-09 | `models/final/` completo, con config, semilla y commit en cada run |

### R5 — Evaluación, backtesting y demo

| ID | Tarea | Fase | Prio | Depende de | Criterio de aceptación |
|----|-------|------|------|------------|------------------------|
| EVA-01 | Definir el protocolo de evaluación (métricas, splits, semillas y pruebas estadísticas) en `docs/notas/protocolo_eval.md` | F0 | P0 | — | Aprobado por el equipo **antes** de ver resultados (evita el *p-hacking*) |
| EVA-02 | `run_backtest(policy, env, markets)` → DataFrame de trayectorias con todas las claves de `info` | F1 | P0 | ENV-04, AGT-02 | Test: el `NoTrade` termina con `V_final = V_0` en todos los mercados |
| EVA-03 | `metrics.py`: retorno, Sharpe, max drawdown, win rate, operaciones, costos y % de acciones inválidas | F2 | P0 | EVA-02 | Tests con curvas de capital hechas a mano y su resultado conocido |
| EVA-04 | `stats.py`: IC por bootstrap y diferencia pareada agente frente a baseline | F2 | P0 | EVA-03 | Test: el IC contiene la media verdadera en datos simulados (≈ 95 %) |
| EVA-05 | `report.py` y `polyrl report`: tabla comparativa y figuras (curvas de capital, distribución del PnL, curvas de aprendizaje) | F2 | P0 | EVA-03 | Se genera `reports/val/` de forma automática con un solo comando |
| EVA-06 | **Evaluación final en test** (una sola vez, con los modelos congelados de AGT-10) | F4 | P0 | AGT-10 | `reports/test/` con la tabla final e IC 95 % |
| EVA-07 | Demo Streamlit v1: elegir mercado y agente, reproductor paso a paso, gráfico del precio con marcas y panel de estado | F3 | P0 | EVA-02 | La demo funciona con las trayectorias del mini-dataset |
| EVA-08 | Demo v2: comparar varios agentes en el mismo mercado y mostrar la curva de capital acumulada | F4 | P1 | EVA-07, EVA-06 | Muestra el mejor agente frente al mejor baseline en un mercado de test |
| EVA-09 | (CD) Desplegar la demo en Streamlit Community Cloud desde `proyecto` | F4 | P2 | EVA-08 | URL pública funcionando, enlazada desde el README |
| EVA-10 | Coordinar el informe final y la presentación (ver DOC-*) | F4 | P0 | EVA-06 | Entregados en la fecha |

### Informe y presentación (todos)

| ID | Tarea | Responsable | Fase | Depende de |
|----|-------|-------------|------|------------|
| DOC-01 | Plantilla del informe (LaTeX/Overleaf o Markdown) y estructura de secciones | R5 | F3 | — |
| DOC-02 | Introducción, motivación y trabajo relacionado | R4 + R5 | F4 | DOC-01 |
| DOC-03 | Datos y EDA | R2 | F4 | DAT-08 |
| DOC-04 | Formulación como MDP y función de recompensa, incluida la ablación | R3 | F4 | ENV-08 |
| DOC-05 | Algoritmos, entrenamiento e hiperparámetros | R4 | F4 | AGT-10 |
| DOC-06 | Metodología de evaluación, reproducibilidad e ingeniería (CI/CD) | R1 | F4 | INF-10 |
| DOC-07 | Resultados, discusión, limitaciones y trabajo futuro | R5 (con todos) | F4 | EVA-06 |
| DOC-08 | Diapositivas y ensayo de la presentación con la demo en vivo | Todos | F4 | DOC-07, EVA-08 |

---

## 3. Grafo de dependencias críticas

La **ruta crítica** es la cadena que, si se atrasa, atrasa todo el proyecto:

```
DAT-01 ─▶ DAT-02/03 ─▶ DAT-04 ─▶ DAT-05 ─▶ DAT-07 ─▶ ENV-07 ─▶ AGT-04 ─▶ AGT-09 ─▶ AGT-10 ─▶ EVA-06 ─▶ DOC-07
                                    │
ENV-01 ─▶ ENV-02 ─▶ ENV-04 ─▶ ENV-05 ┘ (el entorno usa fixtures de DAT-05 desde el principio)
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
- [ ] Repo con CI en verde sobre la rama `proyecto`
- [ ] Spike de datos documentado y familia de mercados elegida (ADR)
- [ ] MDP especificado (ENV-01) y protocolo de evaluación aprobado (EVA-01)
- [ ] Integrantes asignados a cada rol en [03_roles.md](03_roles.md)

**H1 (cierre de F1)**
- [ ] `polyrl data build` produce el dataset v1 con el split
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
