# 07 — Riesgos y decisiones

## 1. Registro de riesgos

**Probabilidad / Impacto:** Alta · Media · Baja

| ID | Riesgo | Prob. | Impacto | Mitigación | Dueño |
|----|--------|-------|---------|------------|-------|
| R1 | La API `prices-history` da una **granularidad gruesa** en los mercados ya cerrados (pocos puntos por episodio) | Media | Alta | Spike DAT-01 antes que cualquier otra tarea. Alternativas: pedir ventanas cortas con `startTs`/`endTs`, reconstruir el precio desde los trades (Data API o subgraph) o usar mercados de duración diaria con fidelidad horaria | R2 |
| R2 | **Fuga de información del futuro** (*lookahead*) en las features, el re-muestreo o el split | Media | Alta | Tests obligatorios de no-lookahead ([05_testing.md](05_testing.md)), split temporal por mercado y solo forward-fill | R2, R3 |
| R3 | **Sobreajuste** a train y al conjunto de val por exceso de ajuste | Alta | Alta | Test intocable hasta EVA-06, presupuesto de ajuste acotado (≤ 20 configs), varias semillas e IC | R4, R5 |
| R4 | El agente no supera a los baselines (mercado eficiente) | Alta | Media | Es un resultado válido si está bien medido. Se reporta con honestidad y se analiza en qué mercados o momentos sí o no hay ventaja. | R5 |
| R5 | Recompensa mal diseñada: el agente aprende a no operar nunca, o a operar todo el tiempo | Media | Media | Ablación de la recompensa, monitoreo del nº de operaciones y del % de acciones inválidas, y penalizaciones calibradas | R3 |
| R6 | Bugs en el entorno que invalidan los resultados | Media | Alta | Suite de invariantes con `hypothesis` y entorno sintético con solución conocida (AGT-06) | R3 |
| R7 | Costos irreales (spread y slippage) que hacen ver el PnL demasiado optimista | Media | Media | Costos conservadores por defecto y análisis de sensibilidad (ENV-09) | R3 |
| R8 | Entrenamiento demasiado lento en CPU | Baja | Media | MLP pequeñas, entornos vectorizados, Colab como respaldo y presupuesto de timesteps fijo | R4 |
| R9 | Cambios o caída de las APIs de Polymarket durante el semestre | Baja | Media | Caché de los datos crudos en disco desde el principio. El dataset construido se respalda (Drive o Release). | R2 |
| R10 | Integración tardía: los módulos funcionan solos pero no juntos | Media | Alta | Contratos al inicio de F1 (INF-06) y test E2E en la CI desde F2 (INF-07) | R1 |
| R11 | Un integrante se ausenta o se atrasa | Media | Media | Roles con backup ([03_roles.md](03_roles.md)), commits pequeños y documentación por módulo | R1 |
| R12 | Problemas de compatibilidad entre `d3rlpy` y `stable-baselines3` (versiones de torch o gymnasium) | Media | Baja | Fijar versiones en `uv.lock` en F0. Si hay conflicto, el Offline RL queda como extra opcional. | R4 |

**Revisión:** R1 revisa este registro en cada hito y actualiza la probabilidad y el impacto.

---

## 2. Registro de decisiones de arquitectura (ADR)

Formato corto: **contexto → decisión → consecuencias**. Una decisión nueva se agrega al final con
el siguiente número. Las decisiones antiguas no se borran: se marcan como *Reemplazada por
ADR-XXX*.

### ADR-001 — Usar librerías de RL existentes en lugar de implementar los algoritmos

- **Estado:** Aceptada
- **Contexto:** El objetivo del curso es aplicar RL a un problema real y evaluarlo con rigor.
  Reimplementar PPO o DQN consume tiempo y agrega bugs.
- **Decisión:** Usar `stable-baselines3` (PPO, DQN) y `d3rlpy` (CQL, BC).
- **Consecuencias:** El esfuerzo va al entorno, la recompensa y la evaluación. El informe debe
  explicar igual la teoría de cada algoritmo y sus hiperparámetros.

### ADR-002 — Un episodio = un mercado; split temporal por mercado

- **Estado:** Aceptada
- **Contexto:** Si el split se hace por pasos dentro de un mismo mercado, el resultado del mercado
  se filtra entre train y test.
- **Decisión:** Cada mercado es un episodio completo. Los mercados se separan en train, val y test
  por orden cronológico de su fecha de resolución.
- **Consecuencias:** Se necesitan suficientes mercados (≥ 300 en total para una evaluación con
  sentido). Esto refuerza la elección de mercados recurrentes (ADR-004).

### ADR-003 — Simulador price-taker con `p_no = 1 - p_yes` y costos fijos

- **Estado:** Aceptada
- **Contexto:** No hay historia pública del order book de Polymarket.
- **Decisión:** El agente no mueve el precio. El precio de NO se aproxima como `1 - p_yes`, y los
  costos se modelan con `spread`, `slippage` y `fee_rate` configurables.
- **Consecuencias:** Los resultados son optimistas para tamaños grandes. Se documenta como una
  limitación y se hace un análisis de sensibilidad a los costos.

### ADR-004 — Familia de mercados inicial: "Bitcoin Up or Down"

- **Estado:** Propuesta. Se confirma tras el spike DAT-01.
- **Contexto:** Hacen falta muchos episodios homogéneos, con duración fija y una regla de
  resolución clara.
- **Decisión:** Empezar con los mercados recurrentes *BTC Up or Down* (horarios o diarios, según
  la granularidad disponible). ETH es una extensión.
- **Consecuencias:** La feature `spot_vs_open` (spot de Binance) se vuelve central. Hay que
  documentar cuál es la fuente de precio que usa Polymarket para resolver.

### ADR-005 — Espacio de acción discreto de 4 acciones y una posición a la vez

- **Estado:** Aceptada
- **Contexto:** DQN y CQL discreto requieren acciones discretas, y un espacio simple se aprende
  más rápido.
- **Decisión:** `Discrete(4) = {WAIT, BUY_YES, BUY_NO, SELL}`, con tamaño fijo y como máximo una
  posición abierta.
- **Consecuencias:** No se aprende a dimensionar la posición. Queda como trabajo futuro: acciones
  con varios tamaños o un espacio continuo para PPO.

### ADR-006 — Herramientas: `uv`, `ruff`, `pytest`, GitHub Actions y Streamlit

- **Estado:** Aceptada
- **Contexto:** Se necesita un entorno reproducible, una CI gratuita y una demo fácil de hacer.
- **Decisión:** Las que lista la sección 4 de [02_arquitectura.md](02_arquitectura.md).
- **Consecuencias:** Todo el equipo instala `uv`. Quien no pueda usa `pip install -e ".[dev]"` como
  alternativa.

<!-- Plantilla para nuevas decisiones:
### ADR-00X — Título
- **Estado:** Propuesta | Aceptada | Reemplazada por ADR-XXX
- **Contexto:**
- **Decisión:**
- **Consecuencias:**
-->
