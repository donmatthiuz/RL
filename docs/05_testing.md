# 05 — Testing y CI/CD

En un proyecto de RL financiero, **un bug en el entorno o en el backtest produce resultados falsos
que parecen buenos**. Una fuga de información del futuro, por ejemplo, da un agente "genial" que no
sirve. Por eso el testing no es opcional: es parte del método científico del proyecto.

---

## 1. Normas generales

1. **Toda entrega que agrega lógica agrega tests.** Un commit sin tests solo se acepta si es de
   documentación, configuración o un notebook.
2. **Los tests unitarios no usan la red.** Las APIs se simulan con respuestas grabadas
   (`tests/fixtures/api/*.json`) mediante la librería `responses`.
3. **Los tests son deterministas.** Todo lo que tenga aleatoriedad recibe una semilla fija. Un test
   que falla "a veces" se considera roto y se arregla o se marca `xfail` y se anota en el tablero.
4. **Los tests son rápidos.** La suite por defecto (`pytest`) debe correr en **< 60 s** en una
   laptop. Lo lento se marca con `@pytest.mark.slow`.
5. **Un bug encontrado = un test de regresión** que lo reproduce, agregado en el mismo commit que lo
   arregla.
6. **Cobertura mínima: 70 %** de líneas en `src/polym4v/`. Los módulos críticos (`env/`,
   `evaluation/metrics.py` y `data/splits.py`) deben llegar a **≥ 90 %**. `app/` y `notebooks/`
   quedan fuera de la medición.
7. **No se baja la cobertura**: una entrega que la reduce más de 1 punto debe justificarlo.

---

## 2. Tipos de tests y marcadores

| Tipo | Carpeta | Marcador | Qué prueba | Corre en |
| ------ | --------- | ---------- | ------------ | ---------- |
| Unitario | `tests/unit/` | (ninguno) | Funciones y clases aisladas | Cada push |
| Propiedades | `tests/unit/` | (ninguno) | Invariantes con `hypothesis` | Cada push |
| Integración | `tests/integration/` | `integration` | Varios módulos juntos sobre el mini-dataset | Cada push |
| Smoke de entrenamiento | `tests/integration/` | `smoke` | PPO/DQN/CQL entrenan unos pocos miles de pasos sin errores | Cada push |
| Lento | `tests/` | `slow` | Entrenamientos más largos, backtest completo de val | Nightly / manual |
| Red | `tests/network/` | `network` | Que las APIs reales sigan respondiendo con el esquema esperado | Nightly / manual |

Configuración en `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers -m 'not slow and not network'"
markers = [
  "integration: varios módulos sobre el mini-dataset",
  "smoke: entrenamiento muy corto para detectar errores de integración",
  "slow: tarda más de 10 s",
  "network: usa la red real (APIs de Polymarket/Binance)",
]

[tool.coverage.run]
source = ["src/polym4v"]
branch = true

[tool.coverage.report]
fail_under = 70
show_missing = true
```

Comandos:

```bash
make test        # suite por defecto (rápida)
make coverage    # con cobertura (mínimo 70 %)
make check       # lo mismo que la CI: lint, tipos y cobertura
```

Los targets de integración (`-m integration`) y del nightly (`-m "slow or network"`) se agregan
al `Makefile` cuando existan esos tests (INF-07 e INF-08).

---

## 3. Qué hay que testear, módulo por módulo

### 3.1 `data/` (R2)

| Test | Qué verifica |
| ------ | -------------- |
| Parseo de clientes | Con un JSON grabado de Gamma/CLOB, se obtienen los campos y tipos esperados (`clobTokenIds` viene como string JSON y se parsea bien) |
| Paginación | El cliente recorre todas las páginas y se detiene bien |
| Reintentos | Ante un 429 o 5xx, reintenta con backoff y al final lanza un error claro |
| Caché | La segunda ejecución no hace ninguna llamada HTTP |
| Esquema | `markets.parquet` y `steps.parquet` validan con `pandera`: `p_yes ∈ [0,1]`, `ts` creciente por mercado y `outcome ∈ {0,1}` |
| **No-lookahead del re-muestreo** | Solo *forward-fill*: el valor en `t` es igual al último dato observado con `ts ≤ t` |
| **Split** | Intersección vacía de mercados entre splits y orden temporal train < val < test |
| Reproducibilidad | Construir el dataset dos veces con la misma config da el mismo hash |

### 3.2 `features/` (R2)

| Test | Qué verifica |
| ------ | -------------- |
| **No-lookahead** | `features(serie[:t+1])[t] == features(serie)[t]` para todo `t`: agregar datos futuros no cambia el pasado |
| Valores conocidos | En una serie lineal o constante, los retornos y volatilidades son los esperados |
| Normalización | Se ajusta solo con train, y val/test usan esos mismos parámetros |
| NaN | No hay NaN después del período de calentamiento |

### 3.3 `env/` (R3) — el módulo más crítico

| Test | Qué verifica |
| ------ | -------------- |
| API Gymnasium | `gymnasium.utils.env_checker.check_env(env)` pasa |
| Espacios | Las observaciones están siempre dentro de `observation_space` |
| Reset | `reset(seed=s)` es determinista y elige un mercado del split correcto |
| **Conservación del dinero** | En cada paso: `V_t - V_{t-1} = Δprecio · tamaño - costos_t` |
| **Sin apalancamiento** | `cash ≥ 0` siempre (propiedad con `hypothesis` sobre secuencias de acciones arbitrarias) |
| Costos | Comprar y vender de inmediato con el precio constante pierde exactamente `spread + 2·slippage + fees` |
| Liquidación | Una posición YES en un mercado con `outcome=1` cobra `tamaño × 1.0`, y con `outcome=0` cobra `0` |
| Acciones inválidas | `BUY_*` con una posición abierta y `SELL` sin posición se tratan como `WAIT`, `action_valid=False` y se aplica la penalización |
| **Recompensa telescópica** | Con `reward=pnl`, `Σ r_t = (V_final - V_0) / V_0` |
| **No-lookahead en observación** | Modificar los precios con `ts > t` no cambia la observación en `t` |
| Fin de episodio | `terminated=True` exactamente en el último paso del mercado |
| Política aleatoria | 500 episodios con acciones aleatorias, sin excepciones ni NaN |

Ejemplo de test de propiedades:

```python
from hypothesis import given, settings, strategies as st


@settings(max_examples=200, deadline=None)
@given(actions=st.lists(st.integers(min_value=0, max_value=3), min_size=1, max_size=60))
def test_cash_never_negative(fixture_env, actions):
    obs, info = fixture_env.reset(seed=0)
    for a in actions:
        obs, r, terminated, truncated, info = fixture_env.step(a)
        assert info["cash"] >= -1e-9
        assert np.isfinite(r)
        if terminated or truncated:
            break
```

### 3.4 `agents/` (R4)

| Test | Qué verifica |
| ------ | -------------- |
| Interfaz `Policy` | Todas las políticas devuelven un `int` dentro de `[0, 3]` |
| Baselines | En escenarios sintéticos obvios hacen lo esperado (por ejemplo, `Favorite` compra YES si `p_yes = 0.8`) |
| Guardar y cargar | Un modelo guardado y cargado de nuevo da las mismas acciones para las mismas observaciones |
| Smoke (`smoke`) | PPO, DQN y CQL entrenan unos 2 000 pasos sobre el mini-dataset sin errores |
| Determinismo | La misma semilla y la misma config dan los mismos pesos o las mismas acciones (CPU) |
| **Cordura (`slow`)** | En el entorno sintético con una solución conocida, el agente alcanza ≥ 90 % del óptimo |

### 3.5 `evaluation/` (R5)

| Test | Qué verifica |
| ------ | -------------- |
| `NoTrade` | Retorno 0 y drawdown 0 en todos los mercados |
| Métricas | Max drawdown, Sharpe y win rate de curvas hechas a mano coinciden con los valores calculados a mano |
| Bootstrap | En datos simulados con media conocida, el IC 95 % la cubre en ≈ 95 % de las repeticiones (`slow`) |
| Backtest | La trayectoria tiene una fila por paso con todas las claves de `info` y es reproducible con semilla |
| Aislamiento del test | `evaluate` sobre `split=test` falla si no se pasa `--final` (protege el conjunto de test) |

### 3.6 `utils/` y CLI (R1)

| Test | Qué verifica |
| ------ | -------------- |
| Config | Un YAML inválido (tipo incorrecto, campo faltante) lanza un error claro de pydantic |
| Semillas | `set_global_seed` fija random, numpy y torch |
| CLI | `typer.testing.CliRunner` ejecuta cada comando con `--help` y con el mini-dataset |
| **E2E (`integration`)** | `data build` (fixtures) → `train` (smoke) → `evaluate` → `report` produce los archivos esperados |

---

## 4. Fixtures compartidas

En `tests/conftest.py` (lo mantiene R1, con aportes de cada dueño):

| Fixture | Contenido |
| --------- | ----------- |
| `api_responses` | JSON grabados de Gamma, CLOB y Binance (`tests/fixtures/api/`) |
| `mini_dataset` | ≈ 5 mercados reales recortados, en Parquet (`tests/fixtures/mini_dataset/`) |
| `synthetic_market` | Generador de mercados sintéticos con parámetros controlados (tendencia, ruido, resultado) |
| `fixture_env` | `PolymarketEnv` sobre `mini_dataset` con costos conocidos |
| `toy_env` | Entorno sintético con una política óptima conocida (para AGT-06) |

Cómo grabar fixtures nuevas: `uv run python scripts/record_fixtures.py`. El script descarga de la
red y anonimiza o recorta. Las fixtures grabadas **se versionan** y no se regeneran en la CI.

---

## 5. Integración continua (CI) — GitHub Actions

> **Implementado (ADR-014):** el workflow real está en `.github/workflows/ci.yml` y los hooks en
> `.pre-commit-config.yaml`. Sus versiones (checkout v7, setup-uv v10.3.3 fijado por hash, ruff
> 0.17.3) mandan sobre las de los ejemplos de esta sección, que quedan como diseño original.

### 5.1 `ci.yml` — en cada push a `proyecto`

```yaml
name: CI
on:
  push:
    branches: [proyecto]
  workflow_dispatch: {}

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src/polym4v

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras --frozen
      - name: Tests unitarios + integración + smoke, con cobertura
        run: uv run pytest -m "not slow and not network" --cov --cov-report=xml
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage.xml
```

**Reglas de la CI:**

- La CI debe quedar **en verde** después de cada push a `proyecto`. No hay excepciones ni "lo
  arreglo en el próximo commit".
- Si la CI de `proyecto` se rompe, arreglarla es la **prioridad número 1** del autor del último
  push, con R1 como apoyo.
- Tiempo objetivo de la CI: **< 8 minutos**. Si se pasa, R1 mueve tests a `slow`.
- Las dependencias quedan fijadas en `uv.lock`. Actualizarlas requiere un commit propio (`chore(deps): ...`).

### 5.2 `nightly.yml` — tests lentos y verificación de las APIs

```yaml
name: Nightly
on:
  schedule:
    - cron: "0 6 * * *"     # todos los días a las 06:00 UTC
  workflow_dispatch: {}

jobs:
  slow-and-network:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras --frozen
      - run: uv run pytest -m "slow or network"
```

Si falla un test `network`, significa que la API de Polymarket cambió. R2 lo anota en el tablero.

### 5.3 Hooks locales (`pre-commit`)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-added-large-files
        args: [--maxkb=1024]       # evita subir datasets o modelos al repo
      - id: check-yaml
```

Cada integrante ejecuta `make setup` (o solo `make hooks`) una vez después de clonar el repo.

---

## 6. Despliegue continuo (CD)

El CD de este proyecto **no es un servicio en producción**. Consiste en publicar los artefactos de
forma automática y reproducible:

| Qué | Cuándo | Cómo |
|-----|--------|------|
| **GitHub Release** con el reporte (tablas y figuras), `metrics.json` y los modelos finales (`.zip`) | Al crear un tag `v*` (`v0.1` en H1, `v0.2` en H2, `v1.0` en la entrega) | `release.yml`: corre `polym4v report` y `softprops/action-gh-release` adjunta los archivos |
| **Demo pública** (opcional, P2) | En cada push a `proyecto` | Streamlit Community Cloud, conectado al repo, despliega `app/demo.py` de forma automática |

```yaml
# release.yml (resumen)
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras --frozen
      - run: uv run pytest -m "not slow and not network"
      - run: uv run polym4v report --from models/final --out reports/release
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            reports/release/**
```

> Los modelos finales y las trayectorias que usa la demo deben ser **pequeños** (< 50 MB en total).
> Si no lo son, se suben al Release y no al repo.

---

## 7. Checklist de testing para cada entrega

- [ ] Agregué o actualicé tests para la lógica nueva o modificada
- [ ] `uv run pytest` pasa en local
- [ ] `uv run ruff check . && uv run ruff format --check .` pasa
- [ ] Los tests nuevos no usan la red ni dependen del orden de ejecución
- [ ] Si toqué `env/`, `features/` o `data/`: los tests de **no-lookahead** e **invariantes** siguen
      pasando
- [ ] Si arreglé un bug: agregué un test de regresión
- [ ] La cobertura no bajó más de 1 punto
