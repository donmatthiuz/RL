# 03 — Roles

El equipo tiene **5 personas**. Cada rol es **dueño** de uno o dos módulos de la arquitectura
([02_arquitectura.md](02_arquitectura.md)). Ser dueño significa decidir sobre el módulo, mantenerlo
y verificar que lo que se entrega en él pase sus tests. No significa trabajar solo. Todos programan, todos escriben tests y todos
escriben una parte del informe.

> **Asignación de personas:** completar la columna "Integrante" en la primera reunión.

| Rol | Integrante | Módulos de los que es dueño | Backup (lo cubre si se ausenta) |
| ----- | ------------ | ----------------------------- | --------------------------------- |
| **R1** Líder técnico e integrador (MLOps) | Josué | `utils/`, `cli.py`, `pyproject.toml`, `docs/`, contratos entre módulos (CI/CD fuera del alcance, ADR-010) | R4 |
| **R2** Ingeniero de datos | Mathew | `data/`, `features/`, `notebooks/eda` | R5 |
| **R3** Ingeniero del entorno y la recompensa | Gustavo | `env/` (incluye `reward.py`) | R4 |
| **R4** Ingeniero de agentes RL | _por asignar_ | `agents/` (PPO, DQN, Offline RL) | R3 |
| **R5** Evaluación, backtesting y demo | _por asignar_ | `evaluation/`, `app/`, `reports/` | R2 |

---

## R1 — Líder técnico e integrador (MLOps)

**Misión:** que las piezas encajen, que el repositorio esté sano y que el proyecto llegue a tiempo.

**Responsabilidades:**

- Montar la base del repositorio: `pyproject.toml`, `uv`, `ruff`, `pre-commit`, estructura de
  carpetas y el paquete `polym4v` instalable.
- Configurar y mantener la **CI/CD** (GitHub Actions) sobre la rama `proyecto`.
- Implementar `utils/` (configuración, semillas, logging, rutas) y la **CLI** (`typer`).
- Definir y hacer cumplir los **contratos** entre módulos: esquemas de datos, la interfaz `Policy`
  y el formato de `info`.
- Hacer las **integraciones** de extremo a extremo (datos → entorno → entrenamiento → evaluación).
- Dirigir las reuniones de avance y mantener el tablero (GitHub Projects).
- Mantener `docs/` coherente y escribir las secciones de _Metodología_ y _Reproducibilidad_ del
  informe.

**Entregables clave:** repositorio base, `ci.yml`, CLI funcional, pipeline E2E y release `v1.0`.

**Perfil sugerido:** la persona con más experiencia en Git y en ingeniería de software.

---

## R2 — Ingeniero de datos

**Misión:** entregar un dataset limpio, sin fugas de información y reproducible.

**Responsabilidades:**

- Investigar las APIs de Polymarket (Gamma y CLOB) y de Binance. **Antes de cualquier otra tarea**
  debe validar qué granularidad entregan para los mercados cerrados (riesgo R1).
- Implementar los clientes HTTP con caché, reintentos y rate limiting.
- Seleccionar los mercados (familia _BTC Up or Down_, y ETH como extensión) y documentar los
  criterios de filtrado.
- Limpiar, re-muestrear y alinear temporalmente el precio del token con el spot.
- Implementar `features/` como funciones puras, sin _lookahead_.
- Implementar el **split temporal por mercado** y el `manifest.json` con hash.
- Hacer un notebook de **EDA**: distribución de resultados, curvas de precio típicas y relación
  entre `spot_vs_open` y el resultado.
- Escribir la sección _Datos_ del informe.

**Entregables clave:** `polym4v data build`, `data/processed/<id>/`, fixtures para los tests y el
notebook de EDA.

**Perfil sugerido:** experiencia con pandas y con consumo de APIs.

---

## R3 — Ingeniero del entorno y la recompensa

**Misión:** construir un simulador fiel, correcto y bien testeado. Si el entorno tiene bugs, todo
lo que se haga encima no sirve.

**Responsabilidades:**

- Implementar `PolymarketEnv` (Gymnasium): `reset`, `step`, `render` (texto) y los espacios de
  observación y acción.
- Implementar `Portfolio` y el modelo de ejecución (spread, slippage, comisión y liquidación).
- Implementar las variantes de la **función de recompensa** como componentes intercambiables.
- Garantizar los **invariantes**: conservación del dinero, `cash ≥ 0` y no usar datos del futuro.
- Escribir los tests más exigentes del proyecto: `check_env`, invariantes y tests de propiedades
  con `hypothesis`.
- Diseñar, junto con R4, los experimentos de **ablación de la recompensa**.
- Escribir la sección _Formulación como MDP y función de recompensa_ del informe.

**Entregables clave:** `PolymarketEnv` v1 validado, `reward.py` con ≥ 3 variantes y la suite de
tests del entorno.

**Perfil sugerido:** la persona más cuidadosa con los detalles y con la lógica.

---

## R4 — Ingeniero de agentes RL

**Misión:** entrenar PPO, DQN y Offline RL de forma correcta, comparable y reproducible.

**Responsabilidades:**

- Implementar la interfaz `Policy` y los adaptadores para SB3 y d3rlpy.
- Implementar los **baselines heurísticos**, junto con R5, que los usa en la evaluación.
- Escribir los scripts de entrenamiento de **PPO** y **DQN**: callbacks, checkpoints, evaluación
  periódica en _val_ y TensorBoard.
- Recolectar el **dataset offline** y entrenar **Discrete CQL** y **BC**.
- Ajustar los hiperparámetros con una búsqueda pequeña y acotada (grid o Optuna con un presupuesto
  fijo).
- Entrenar con ≥ 5 semillas por configuración final.
- Escribir la sección _Algoritmos y entrenamiento_ del informe.

**Entregables clave:** `configs/{ppo,dqn,offline}.yaml`, modelos entrenados en `models/`, curvas de
aprendizaje y una tabla de hiperparámetros.

**Perfil sugerido:** la persona más interesada en la teoría de RL. También lidera la parte teórica
en la presentación.

---

## R5 — Evaluación, backtesting y demo

**Misión:** demostrar con rigor si el agente aprendió algo, y mostrarlo de forma clara.

**Responsabilidades:**

- Implementar `run_backtest`, que es común para cualquier `Policy`, y guardar las trayectorias.
- Implementar las métricas (retorno, Sharpe, drawdown, win rate, operaciones y costos) y la parte
  estadística (bootstrap, comparación pareada).
- Generar las tablas y figuras del informe (`polym4v report`).
- Construir la **demo en Streamlit**: reproductor paso a paso, gráficos y panel de estado.
- Mantener el despliegue de la demo (CD), si se publica.
- Coordinar la redacción del **informe final** y de la **presentación**. Escribir las secciones
  _Resultados_ y _Discusión_.

**Entregables clave:** `polym4v evaluate`, `reports/` con tablas y figuras, `app/demo.py`, el
informe y las diapositivas.

**Perfil sugerido:** interés en estadística y en visualización, y buena comunicación.

---

## Matriz RACI

**R** = Responsable (lo hace) · **A** = Aprueba (_accountable_) · **C** = Consultado ·
**I** = Informado

| Entregable | R1 | R2 | R3 | R4 | R5 |
| ------------ | ---- | ---- | ---- | ---- | ---- |
| Repositorio base, CI/CD | **R/A** | I | I | I | I |
| Contratos entre módulos | **A** | C | R | R | C |
| Clientes API y dataset | C | **R/A** | I | I | C |
| Features | I | **R/A** | C | C | I |
| Entorno y portfolio | C | C | **R/A** | C | I |
| Función de recompensa | I | I | **R/A** | C | C |
| Baselines | I | I | C | **R/A** | R |
| PPO / DQN | C | I | C | **R/A** | I |
| Offline RL | C | I | C | **R/A** | I |
| Backtest y métricas | C | I | C | C | **R/A** |
| Demo | C | I | I | I | **R/A** |
| Informe final | **A** | R | R | R | **R** |
| Presentación | C | R | R | R | **R/A** |

---

## Dinámica del equipo

| Ritual | Frecuencia | Duración | Quién |
| -------- | ------------ | ---------- | ------- |
| Reunión de avance (avances, bloqueos y plan) | Cada 2–3 días | 30 min | Todos. La modera R1. |
| _Check-in_ asíncrono (qué hice, qué haré, qué me bloquea) | Diario | — | Todos, en el canal del grupo |
| Verificación de entregas (correr los tests de lo subido a `proyecto`) | En cada entrega | — | El dueño del módulo |
| Demo interna al cierre de cada fase | Por hito | 30 min | Todos |

**Reglas de colaboración:**

Cada persona documenta lo que hace (docstrings, README de su módulo y, si corresponde, un ADR).
