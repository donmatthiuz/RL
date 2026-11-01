# 02 — Arquitectura

La arquitectura busca ser **robusta pero simple**. Es un proyecto universitario de un semestre con
5 personas, así que se priorizan la reproducibilidad, la separación clara entre módulos (para que
cada rol trabaje en paralelo) y la facilidad de testear, por sobre el rendimiento o la escala.

**Principios:**

1. **Un solo paquete Python** (`polym4v`) con módulos desacoplados por contratos claros.
2. **Todo se configura en YAML**: nada de números mágicos dentro del código.
3. **Reproducibilidad**: semillas fijas, datasets versionados por hash y configuraciones guardadas
   junto a cada modelo.
4. **Sin fuga de información del futuro** (*lookahead*): es la regla de oro del backtesting.
5. **Interfaz común para todas las políticas**: los baselines, PPO, DQN y Offline RL se evalúan con
   el mismo código.

---

## 1. Vista general

```mermaid
flowchart LR
    CFG["configs/*.yaml"]
    API["APIs<br/>Gamma · CLOB · Binance"] --> DATA["data/<br/>ingesta y limpieza"]
    DATA --> FEAT["features/<br/>ingeniería de features"]
    FEAT --> ENV["env/<br/>PolymarketEnv (Gymnasium)"]
    ENV <--> AG["agents/<br/>PPO · DQN · CQL · baselines"]
    AG --> EVAL["evaluation/<br/>backtest · métricas · estadística"]
    CFG -.-> DATA & FEAT & ENV & AG & EVAL
    DATA --> RAW[("data/raw/<br/>JSON crudo")]
    FEAT --> PROC[("data/processed/<br/>Parquet + split")]
    AG --> MOD[("models/<br/>checkpoints, config y logs")]
    EVAL --> REP[("reports/<br/>tablas y gráficos")]
    REP --> APP["app/demo.py<br/>Streamlit"]
```

Flujo: **ingesta → dataset procesado → entorno → entrenamiento → evaluación → demo**.
Cada flecha es un archivo en disco con un esquema definido. Así los módulos se pueden desarrollar
y testear de forma independiente, usando *fixtures*.

---

## 2. Módulos

### 2.1 `data/` — Ingesta y construcción del dataset (Rol 2)

**Fuentes:**

| Fuente | Endpoint | Para qué |
| -------- | ---------- | ---------- |
| Gamma API (vía SDK) | `PublicClient.list_events(series_ids=10114, closed=True)` | Metadatos: pregunta, `condition_id`, tokens, ventana, resultado, esquema de comisiones |
| CLOB API | `GET https://clob.polymarket.com/prices-history?market=<token_id>&startTs=&endTs=&fidelity=1` | Serie de precios `{t, p}` del token YES, un punto por minuto (ADR-007) |
| Binance (público) | `GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m` (y `1h`) | Precio spot como feature y verificación del resultado |

La Data API v2 del SDK (`list_price_history`) devuelve vacío en mercados cerrados, por eso no se
usa para el historial ([spike de datos](notas/spike_datos.md)).

**Familia de mercados:** *"Bitcoin Up or Down"* **horario** (ADR-004). Hay del orden de 12 000
episodios homogéneos y resuelven con la vela 1h de Binance. El detalle del ETL, el contrato de
datos ampliado y la observación del agente están en
[08_datos_y_entrada_modelo.md](08_datos_y_entrada_modelo.md).

**Componentes:**

```
src/polym4v/data/
├── clients/
│   ├── gamma.py        # GammaClient: lista y filtra mercados, maneja paginación
│   ├── clob.py         # ClobClient: historia de precios por token
│   └── binance.py      # BinanceClient: klines spot
├── cache.py            # Caché en disco de respuestas crudas (data/raw/), evita volver a descargar
├── schemas.py          # Esquemas pandera/pydantic de MarketMeta y PriceStep
├── build_dataset.py    # Orquesta descarga → limpieza → alineación temporal → Parquet
└── splits.py           # Split temporal train/val/test POR MERCADO
```

**Reglas:**

- Rate limiting y reintentos con *backoff* exponencial (`tenacity`).
- Todas las respuestas crudas se cachean en `data/raw/`, así que reconstruir el dataset no repite
  las llamadas de red.
- Los precios se re-muestrean a una grilla fija (por ejemplo, 1 minuto) con *forward-fill* hacia
  adelante **únicamente**. Nunca se usa *back-fill*, porque introduciría información del futuro.
- Se descartan los mercados con muy pocos puntos, con huecos largos o con una resolución ambigua.
- **El split es temporal y por mercado**: train = los mercados más antiguos (≈70 %), val = los
  siguientes (≈15 %) y test = los más recientes (≈15 %). Un mismo mercado nunca aparece en dos
  splits.

**Contrato de salida** (`data/processed/<dataset_id>/`):

`markets.parquet` — una fila por mercado:

| Columna | Tipo | Descripción |
| --------- | ------ | ------------- |
| `market_id` | str | `conditionId` |
| `question` | str | Texto de la pregunta |
| `asset` | str | `BTC` / `ETH` |
| `start_ts`, `end_ts` | int (unix s) | Ventana del episodio |
| `outcome` | int | `1` si se resolvió YES, `0` si NO |
| `split` | str | `train` / `val` / `test` |

`steps.parquet` — una fila por (mercado, paso):

| Columna | Tipo | Descripción |
| --------- | ------ | ------------- |
| `market_id` | str | FK a `markets` |
| `ts` | int | Timestamp del paso |
| `p_yes` | float ∈ [0,1] | Precio del token YES (el de NO se aproxima como `1 - p_yes`) |
| `spot` | float | Precio spot del activo subyacente |
| `spot_open` | float | Precio spot al inicio de la ventana (referencia en los mercados Up/Down) |

`manifest.json` — configuración usada, fecha de construcción, número de mercados por split y hash
SHA-256 de los Parquet.

### 2.2 `features/` — Ingeniería de features (Rol 2)

Funciones **puras** que solo reciben la historia hasta `t` (inclusive):

| Feature | Descripción |
| --------- | ------------- |
| `p_yes_t` | Precio actual |
| `ret_p_{1,5,15}` | Cambio de `p_yes` en los últimos 1/5/15 pasos |
| `vol_p_15` | Desviación estándar de los cambios de `p_yes` (15 pasos) |
| `spot_ret_{1,5,15}` | Retorno log del spot |
| `spot_vs_open` | `(spot - spot_open) / spot_open`, la señal clave en los mercados Up/Down |
| `time_left` | Fracción del episodio que queda, en [0,1] |

La normalización (media y desviación) se ajusta **solo con train** y se guarda junto al dataset.

La lista concreta para la serie horaria, con la volatilidad del spot, el valor justo `p_fair` y
`edge = p_fair - p_yes`, está en la sección 4.1 de
[08_datos_y_entrada_modelo.md](08_datos_y_entrada_modelo.md).

### 2.3 `env/` — Entorno simulado (Rol 3)

`PolymarketEnv(gymnasium.Env)`: **un episodio = un mercado**.

```
src/polym4v/env/
├── market_env.py   # PolymarketEnv: reset/step, ejecución (S4), acciones inválidas (S6) y fin (S10)
├── market_data.py  # Episodios desde steps y prices_raw, con la normalización de train
├── portfolio.py    # Portfolio: caja, posición, valor de liquidación (S9) y liquidación 0/1
├── execution.py    # Modelo de costos: medio spread y comisión taker (S5)
├── reward.py       # Variantes de recompensa de la ablación de ENV-08, elegibles por config
└── synthetic.py    # Mercados sintéticos: mercado nulo (ENV-10) y control positivo (AGT-06)
```

La especificación del MDP, con el origen de cada regla, está en [mdp.md](notas/mdp.md). La config
es `configs/env.yaml` (`SimulatorConfig`).

**Espacio de observación** — `Box(shape=(16,))`:

- Las 13 features de mercado del paso `t`, de `steps.parquet` (sección 4.1 de
  [08_datos_y_entrada_modelo.md](08_datos_y_entrada_modelo.md)), con el z-score de train.
- El estado del agente: `pos_side ∈ {-1: NO, 0: nada, 1: YES}`, `entry_price` (0 sin posición) y
  `upnl`, el PnL no realizado sobre el monto apostado con la posición valorada a liquidación (S9).

**Espacio de acción** — `Discrete(4)`: `0 = WAIT`, `1 = BUY_YES`, `2 = BUY_NO`, `3 = SELL`.

**Reglas de la simulación:**

| Regla | Detalle |
| ------- | --------- |
| Price-taker | El agente no mueve el precio. Compra a `p + half_spread` y vende a `p - half_spread` (S5), con órdenes de 20 USDC (S4b). |
| Ejecución | La orden decidida en `t` se ejecuta al primer precio con fecha posterior a `t + 2 s`, como mucho a `t + 60 s`. Si no hay precio, se cancela y se reporta (S4, ADR-017). Ejecutar al precio de `t` solo se usa para mostrar la ganancia falsa. |
| Una posición a la vez | `BUY_*` con una posición ya abierta es una **acción inválida**: se ejecuta como `WAIT`, sin penalización. Se guardan la acción pedida y la ejecutada (S6). |
| Tamaño fijo | Cada compra usa `stake_fraction` del saldo inicial: 2 %, es decir 20 USDC con un saldo de 1 000 (S4b). |
| `SELL` sin posición | Acción inválida, se ejecuta como `WAIT`, sin penalización (S6). |
| Costos | `buy_price = p + half_spread`, `sell_price = p - half_spread`, dentro de `[tick, 1 - tick]`, más la comisión taker `acciones × fee_rate × (precio × (1 - precio))^fee_exponent` redondeada, pagada en USDC (S5, ADR-009 y `src/polym4v/env/execution.py`). El slippage queda dentro de `half_spread`. Valores en `env.costs` de `configs/env.yaml`. |
| Fin del episodio | No se abren posiciones en los últimos 2 minutos (S10). Al llegar a `w1`, la posición abierta **se liquida** a `1` o `0` según `outcome`, sin comisión; un `SELL` que no se ejecutó antes la deja hasta la liquidación. |
| Precio de NO | `p_no = 1 - p_yes` (aproximación documentada en el ADR-003). |

**Invariantes** (verificados por tests, ver [05_testing.md](05_testing.md)):

- Conservación: `cash + valor_posición` solo cambia por variaciones de precio, costos y liquidación.
- `cash ≥ 0` siempre. No hay apalancamiento.
- La observación en `t` no depende de ningún dato con `ts > t`.

**`info` de cada paso** (INF-06; lo usan el backtest, la validación de ejecuciones y la demo).
Describe la decisión tomada en `ts` y el estado de la cartera en el instante siguiente. Las claves
están en `INFO_KEYS` de `market_env.py`:

| Clave | Contenido |
| --- | --- |
| `market_id`, `k`, `ts`, `p_yes` | Mercado, paso, instante de la decisión y último precio YES visto |
| `action`, `action_executed`, `action_valid` | Acción pedida, ejecutada y si era válida (S6). En `reset` valen `None` |
| `order_status` | `ejecutada`, `sin_precio` (no hubo precio en la ventana de S4), `no_verificable` (modo estricto, EVA-11), `invalida` o `ninguna` |
| `exec_ts`, `exec_p` | Fecha y precio YES del punto con que se ejecutó la orden |
| `exec_verified` | Si un trade real respalda la ejecución (EVA-11): `True`, `False`, o `None` sin verificador o sin trades del mercado |
| `fill_price`, `fill_shares`, `fee` | Precio pagado o recibido por el lado operado, acciones y comisión de la operación |
| `position_side`, `position_size`, `cash` | Cartera después de la operación |
| `portfolio_value`, `fees_paid` | Valor de la cartera (S9) en el instante siguiente y comisiones acumuladas del episodio |
| `reward_components` | `pnl`, `drawdown`, `hold`, `invalid` y `terminal` del paso; suman la recompensa |

### 2.4 Función de recompensa (Rol 3, en colaboración con Rol 4)

Se implementa como un objeto configurable para poder hacer ablaciones:

```
r_t =  ΔV_t / V_0                         # beneficio/pérdida mark-to-market del paso
     - λ_dd   · max(0, DD_t - DD_{t-1})   # penaliza el aumento del drawdown (riesgo)
     - λ_cost · costos_t / V_0            # costos ya incluidos en ΔV; se pueden reforzar
     - λ_inv  · 1[acción inválida]        # acciones que no tienen sentido
     - λ_hold · 1[posición abierta]       # opcional: costo por mantener (timing)
```

donde `V_t = cash_t + valor_mark_to_market_t` y `DD_t = max_{τ≤t} V_τ - V_t`.

| Variante (`reward.name`) | Descripción | Etapa de la ablación (ENV-08) |
| -------------------------- | ------------- | ----- |
| `pnl` | Solo `ΔV_t / V_0`; la de `configs/env.yaml` hasta cerrar la ablación | A |
| `pnl_mid` | `ΔM_t / V_0`, con la posición a precio medio: no adelanta el costo de salir | A |
| `terminal` | Solo el PnL final del episodio (recompensa escasa) | A |
| `pnl_risk` | `base` más la penalización de drawdown (`λ_dd`) | B |
| `pnl_hold` | `base` más el costo por mantener (`λ_hold`) | B |
| `utility` | Solo al final, utilidad CARA del PnL sobre el monto (`a`) | B |

Con mark-to-market, la suma de las recompensas `pnl` del episodio es igual al PnL total, así que la
recompensa densa no cambia el objetivo final: solo da más señal en cada paso. Esto se verifica con
un test, también para `pnl_mid`.

`V_t` valora la posición a liquidación (S9, ADR-016). `base` es la ganadora de la etapa A, sobre la
que `pnl_risk` y `pnl_hold` suman su penalización, y `scale` divide por `V_0` o por el monto. La
config rechaza un parámetro que la variante no usa. `λ_cost` y `sharpe_like` quedaron fuera: los
costos ya están en `ΔV_t`, y un Sharpe de 60 pasos con una sola posición es muy ruidoso.

**Decisión (R1, 01/11/2026):** antes de elegir la recompensa principal se revisaron cinco entornos
de referencia y la literatura
([investigación](ia/investigaciones/recompensas_rl_trading.md)). Ninguno castiga el drawdown en
cada paso, y con la valoración a liquidación `pnl_risk` paga la entrada `1 + λ_dd` veces. La
principal se elige con la ablación de ENV-08 en val, en dos etapas: primero `pnl`, `pnl_mid` y
`terminal`, y después las variantes con riesgo sobre la ganadora. Hasta entonces,
`configs/env.yaml` usa `pnl`.

### 2.5 `agents/` — Agentes y baselines (Rol 4)

Todos implementan la misma interfaz, definida en `src/polym4v/agents/base.py` (INF-06):

```python
class Action(IntEnum):
    WAIT = 0
    BUY_YES = 1
    BUY_NO = 2
    SELL = 3


@runtime_checkable
class Policy(Protocol):
    name: str

    def act(self, obs: np.ndarray, info: Mapping[str, Any] | None = None) -> int: ...
    def reset(self) -> None: ...  # al empezar cada episodio; limpia el estado interno
```

| Agente | Implementación | Notas |
| -------- | ---------------- | ------- |
| `RandomPolicy` | propia | Piso mínimo |
| `NoTradePolicy` | propia | Siempre `WAIT`. Retorno = 0 |
| `FavoritePolicy` | propia | Compra el lado con precio > 0.5 en el paso `k` y mantiene hasta la resolución |
| `MomentumPolicy` | propia | Compra en la dirección del cambio reciente de `p_yes` o del spot y sale con un umbral |
| `MeanReversionPolicy` | propia | Lo contrario de momentum |
| `PPOAgent` | `stable_baselines3.PPO` | `MlpPolicy` y entornos vectorizados (`SubprocVecEnv` o `DummyVecEnv`) |
| `DQNAgent` | `stable_baselines3.DQN` | Replay buffer y target network |
| `OfflineAgent` | `d3rlpy` `DiscreteCQL`, más `DiscreteBC` como referencia | Entrenado con un dataset fijo |

**Generación del dataset offline:** se ejecutan los baselines heurísticos con ε-greedy (por ejemplo,
`ε = 0.2`) sobre los mercados de **train** y se guardan las transiciones `(s, a, r, s', done)` en
`data/offline/<id>.h5`. Con eso se entrena CQL, que nunca interactúa con el entorno.

```
src/polym4v/agents/
├── base.py         # Policy Protocol y Action
├── adapters.py     # SB3Policy (PPO, DQN) y D3rlpyPolicy (CQL, BC) → Policy
├── baselines.py    # Políticas heurísticas
├── train_sb3.py    # Entrenamiento PPO/DQN: 10 checkpoints evaluados con la métrica de EVA-01
├── offline.py      # Dataset offline (baselines ε-greedy, acción ejecutada) y CQL/BC con checkpoints
└── registry.py     # nombre → constructor, para cargar desde config
```

**Selección de modelos:** el checkpoint se elige con su retorno medio en **val**. El conjunto de
**test** solo se usa **una vez**, para la tabla final.

### 2.6 `evaluation/` — Backtesting y métricas (Rol 5)

```
src/polym4v/evaluation/
├── backtest.py     # run_backtest(policy, env, markets) → DataFrame de trayectorias
├── metrics.py      # Métricas por episodio y agregadas
├── stats.py        # Bootstrap IC 95 %, test de diferencias pareadas
└── report.py       # Tablas markdown/LaTeX y gráficos (matplotlib)
```

**Métricas:**

| Métrica | Definición |
| --------- | ------------ |
| Retorno medio por mercado | `mean(V_final / V_0 - 1)` |
| Retorno acumulado | Capital compuesto mercado a mercado, en orden cronológico |
| Sharpe (por episodio) | `mean(ret) / std(ret)` |
| Max drawdown | Sobre la curva de capital acumulada |
| Win rate | % de mercados con PnL > 0 (entre los que operó) |
| Nº de operaciones y costos pagados | Para detectar *overtrading* |
| % de acciones inválidas | Calidad de la política |

**Protocolo estadístico:**

- Cada agente de RL se entrena con **≥ 5 semillas**. Se reporta la media ± la desviación entre
  semillas.
- IC 95 % por *bootstrap* sobre los mercados de test.
- Comparación **pareada** (los mismos mercados) entre el agente y el mejor baseline.

### 2.7 `app/` — Demo (Rol 5)

Streamlit (`app/demo.py`):

- Se elige un mercado de test y un agente (o varios para compararlos).
- Un reproductor paso a paso (*play/pause* y *slider* de tiempo).
- Gráfico de `p_yes` con marcas de compra y venta, curva de capital del agente frente a los
  baselines, y un panel con la acción, la posición, el saldo y la recompensa del paso actual.
- Lee trayectorias ya calculadas en `reports/trajectories/*.parquet`, así que no necesita GPU ni
  red.

### 2.8 `utils/` y CLI (Rol 1)

```
src/polym4v/utils/
├── config.py       # Carga YAML → dataclasses/pydantic validados
├── seeding.py      # set_global_seed(seed): random, numpy, torch, gym
├── logging.py      # logging estándar + TensorBoard
└── paths.py        # Rutas centralizadas (data/, models/, reports/)
src/polym4v/cli.py   # argparse: build-dataset | backtest | collect-offline | train | evaluate (y las capturas)
```

---

## 3. Estructura del repositorio

```
RL/
├── README.md
├── pyproject.toml              # dependencias, ruff, pytest, coverage, mypy
├── uv.lock
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml              # lint, mypy y tests con cobertura en cada push y PR a proyecto
│       ├── nightly.yml         # tests lentos y backtest corto (INF-08, previsto)
│       └── release.yml         # CD: en tag v* publica reporte y modelos (INF-09, previsto)
├── configs/
│   ├── data.yaml
│   ├── env.yaml
│   ├── ppo.yaml
│   ├── dqn.yaml
│   ├── offline.yaml
│   └── eval.yaml
├── src/polym4v/
│   ├── data/  features/  env/  agents/  evaluation/  utils/
│   └── cli.py
├── app/
│   └── demo.py
├── notebooks/                  # EDA y exploración (no es código de producción)
├── tests/
│   ├── unit/  integration/
│   ├── fixtures/               # JSON de API grabados + mini-dataset Parquet
│   └── conftest.py
├── docs/                       # esta documentación
├── data/        (gitignored)   # raw/, processed/, offline/
├── models/      (gitignored)   # <agente>/<run_id>/{model.zip, config.yaml, metrics.json}
└── reports/                    # resultados finales (tablas y figuras sí se versionan)
```

---

## 4. Stack tecnológico

| Área | Herramienta | Justificación |
| ------ | ------------- | --------------- |
| Lenguaje | Python 3.11 | Estándar en RL. Lo soportan todas las librerías. |
| Gestión de entorno | `uv` (alternativa: `pip` + `venv`) | Rápido y con lockfile reproducible |
| Entorno RL | `gymnasium` | API estándar que esperan SB3 y d3rlpy |
| PPO / DQN | `stable-baselines3` 2.9.2 (PyTorch) | Implementaciones probadas, para no reimplementar |
| Offline RL | `d3rlpy` 2.8.1 | Trae `DiscreteCQL` y `DiscreteBC`; exige `gymnasium` 1.0.0 (S7) |
| Redes | `torch` solo CPU, del índice de PyTorch | Las redes son MLP pequeñas; la CI y cada integrante instalan lo mismo |
| Datos | `pandas`, `pyarrow`, `requests`, `tenacity` | Simples y suficientes |
| Validación | `pydantic` (configs), `pandera` (DataFrames) | Detecta errores de datos temprano |
| CLI | `typer` | Comandos legibles |
| Tracking | TensorBoard + `metrics.json` por run | Liviano, sin servidor |
| Visualización | `matplotlib`, `plotly` | Informe y demo |
| Demo | `streamlit` | Una app interactiva en pocas líneas |
| Calidad | `ruff` (lint + format), `mypy` (modo permisivo), `pre-commit` | |
| Tests | `pytest`, `pytest-cov`, `responses`, `hypothesis` | Ver [05_testing.md](05_testing.md) |
| CI/CD | GitHub Actions (ADR-014) | Gratis en repos de GitHub; corre en cada push y PR a `proyecto` |

**Hardware:** todo debe correr en una laptop con CPU. Las redes son MLP pequeñas (`[64, 64]`). Si
hace falta más cómputo, se puede usar Google Colab.

---

## 5. Configuración y reproducibilidad

- **Qué va en YAML y qué en `.env`:** todo parámetro que define un experimento va en
  `configs/*.yaml`, se versiona y se valida con pydantic (claves desconocidas y valores
  inconsistentes se rechazan). Las rutas de cada máquina (`POLYM4V_DATA_DIR`,
  `POLYM4V_MODELS_DIR`, `POLYM4V_REPORTS_DIR`), el nivel de log (`POLYM4V_LOG_LEVEL`) y las
  credenciales van en `.env`, que no se versiona; `.env.example` es la plantilla. El entorno
  nunca cambia parámetros de un experimento. `make config CONFIG=configs/data.yaml` valida un
  archivo y lo muestra resuelto.
- Cada run guarda en `models/<agente>/<run_id>/` el `config.yaml` **resuelto**, el `dataset_id`, el
  `git commit`, la semilla, los checkpoints, `best.zip`, `metrics.json` y los registros de
  TensorBoard (`src/polym4v/agents/train_sb3.py`).
- `run_id = <fecha>_<agente>_<reward>_s<seed>`.
- `dataset_id` = los primeros 8 caracteres del hash del `manifest.json`.
- Las configs de los agentes son `configs/ppo.yaml` y `configs/dqn.yaml` (`ExperimentConfig`). Sus
  bloques `env` y `reward` tienen que ser iguales a `configs/env.yaml`, con el que corren los
  baselines; lo comprueba un test. Resumen de `configs/ppo.yaml`:

```yaml
dataset_id: btc_updown_1h_v1
env: ...                    # igual que configs/env.yaml
reward: ...                 # igual que configs/env.yaml
agent:
  algo: ppo
  policy: MlpPolicy
  net_arch: [64, 64]
  learning_rate: 3.0e-4
  gamma: 0.999              # S9: cerca de 1
  total_timesteps: 500000
  n_envs: 4
  checkpoints: 10           # protocolo de EVA-01, sección 5
  params:                   # propios de PPO; SB3 los valida
    n_steps: 512
    batch_size: 256
    ent_coef: 0.01
seeds: [0, 1, 2, 3, 4]
eval_split: val
```

- `make train AGENT=ppo` entrena todas las semillas; `SEED=0` entrena una sola.
- CQL y BC usan `configs/cql.yaml` y `configs/bc.yaml`, con una sección `offline` (baselines, `ε` y
  semilla). Primero `make collect-offline AGENT=cql` recolecta el dataset en `data/offline/`, con
  su manifest; su nombre cambia si cambian los baselines, `ε` o la semilla. En CQL y BC,
  `total_timesteps` son pasos de gradiente.

---

## 6. Límites conocidos del diseño

| Simplificación | Impacto | Por qué se acepta |
| ---------------- | --------- | ------------------- |
| No hay order book histórico | El spread y el slippage son supuestos | Polymarket no publica la historia del libro |
| Price-taker | Sobreestima lo ejecutable con tamaños grandes | Los tamaños simulados son pequeños |
| `p_no = 1 - p_yes` | Ignora pequeñas diferencias entre los dos libros | Se compensa con el spread |
| Granularidad de la API | Un punto por minuto; algunos minutos sin dato | Verificado en el spike DAT-01. Se rellena hacia adelante y se informa la antigüedad del precio (`p_stale`). |
| Comisiones uniformes | Los mercados anteriores a 2026 no cobraban | Se evalúa con el costo real de hoy (ADR-009) |

Estas limitaciones van en el informe final. Más detalle en
[07_riesgos_y_decisiones.md](07_riesgos_y_decisiones.md).
