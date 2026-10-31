# 07 — Riesgos y decisiones

## 1. Registro de riesgos

**Probabilidad / Impacto:** Alta · Media · Baja

| ID | Riesgo | Prob. | Impacto | Mitigación | Dueño |
| ---- | -------- | ------- | --------- | ------------ | ------- |
| R1 | La API `prices-history` da una **granularidad gruesa** en los mercados ya cerrados (pocos puntos por episodio) | Baja | Alta | **Mitigado por el spike DAT-01:** el endpoint CLOB con `startTs`/`endTs` da un punto por minuto. La Data API v2 del SDK devuelve vacío y no se usa ([spike](notas/spike_datos.md), ADR-007). | R2 |
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
| R13 | **Cambio de régimen por las comisiones:** train es casi todo sin comisiones, mientras que val y test son con comisiones. El comportamiento del mercado puede ser distinto. | Alta | Media | El simulador aplica el mismo esquema de comisiones a todos los splits (ADR-009). La EDA compara ambos regímenes y el informe lo discute. | R2, R3 |
| R14 | Los costos (spread más una comisión de hasta 3,5 % por compra) dejan sin ventaja a cualquier estrategia | Alta | Media | Medir en la EDA, antes de entrenar, si `p_fair - p_yes` supera los costos. Un resultado negativo bien medido es válido. | R2, R5 |
| R15 | El endpoint CLOB `/prices-history` no está cubierto por el SDK y puede cambiar sin aviso | Media | Media | Caché completa de las respuestas crudas en `data/raw/` y respaldo del dataset construido | R2 |

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

### ADR-004 — Familia de mercados inicial: "Bitcoin Up or Down" horario

- **Estado:** Aceptada el 30/10/2026, después del spike DAT-01.
- **Contexto:** Hacen falta muchos episodios homogéneos, con duración fija y una regla de
  resolución clara. El spike encontró series de 5m, 15m, 1h, 4h y diarias. Las de 5m y 15m
  resuelven con Chainlink, y la horaria con la vela 1h de Binance BTC/USDT.
- **Decisión:** Usar la serie *BTC Up or Down* horaria (Gamma `10114`, desde el 28/05/2025). ETH
  horario (`10117`) es una extensión si sobra tiempo (DAT-09); confirmado por R1 el 30/10/2026.
- **Consecuencias:** El spot de Binance reproduce exactamente el resultado, así que `spot_vs_open`
  es una feature exacta y no una aproximación. Hay del orden de 12 000 episodios. Ver
  [spike](notas/spike_datos.md).

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

### ADR-007 — Historial de precios desde el endpoint CLOB, no desde la Data API v2

- **Estado:** Aceptada
- **Contexto:** `list_price_history` del SDK (Data API `/v2/prices-history`) devuelve vacío en
  mercados cerrados. `GET https://clob.polymarket.com/prices-history` con `startTs`, `endTs` y
  `fidelity=1` devuelve un punto por minuto, incluso en mercados de mayo de 2025.
- **Decisión:** El pipeline consulta el endpoint CLOB directamente. El SDK se sigue usando para
  listar mercados y eventos.
- **Consecuencias:** `polym4v.PolymarketClient.get_price_history` no sirve para el dataset.
  El endpoint no está cubierto por el SDK, por eso se cachean todas las respuestas (riesgo R15).

### ADR-008 — Un episodio es la vela de 60 minutos, en una grilla de 1 minuto

- **Estado:** Aceptada
- **Contexto:** Cada mercado horario existe entre 24 y 48 horas, pero su precio queda cerca de 0,5
  hasta que empieza la vela. El campo `end_date` de Gamma no marca la ventana en los mercados
  antiguos.
- **Decisión:** El episodio va de `w0` (inicio de la vela) a `w1 = w0 + 3600`, con decisiones en
  `t_k = w0 + 60·k`, `k = 0..59`. La ventana se calcula desde el título, en `America/New_York`.
- **Consecuencias:** 60 pasos por episodio. La hora previa solo se usa como contexto para las
  features. Detalle en [08_datos_y_entrada_modelo.md](08_datos_y_entrada_modelo.md).

### ADR-009 — Comisión taker de Polymarket en el simulador

- **Estado:** Aceptada
- **Contexto:** Los mercados horarios cobran comisión taker desde 2026 (`crypto_fees_v2`,
  `rate = 0,07`, `exponent = 1`). Según el SDK, la comisión es
  `acciones × rate × (p × (1 - p))^exponent`: un 3,5 % del nocional con `p = 0,5`. Los mercados
  anteriores no cobraban.
- **Decisión:** El simulador aplica la fórmula con el esquema vigente a **todos** los mercados,
  porque es el costo real de operar hoy. El esquema original de cada mercado se guarda en
  `markets.parquet`. Correr sin comisiones es una ablación.
- **Consecuencias:** Operar es caro, sobre todo cerca de `p = 0,5`. La política sensata opera poco
  y mantiene hasta la resolución. Aumenta el riesgo de que el agente aprenda a no operar (R5, R14).

### ADR-010 — CI/CD fuera del alcance

- **Estado:** Reemplazada por ADR-014 el 30/10/2026
- **Contexto:** El equipo prioriza datos, entorno, agentes y evaluación.
- **Decisión:** Se omiten INF-03, INF-08, INF-09 y EVA-09 (GitHub Actions, nightly, release y
  despliegue de la demo). Los tests se siguen escribiendo y se corren localmente con `pytest`.
- **Consecuencias:** "CI en verde" deja de ser parte de la Definition of Done y se reemplaza por
  "tests pasando localmente". El criterio C6 de [01_idea_general.md](01_idea_general.md) se evalúa
  igual, pero de forma local.

### ADR-011 — Ejecutar la acción al precio del minuto siguiente

- **Estado:** En revisión. Depende de S3 y S4 de [09_sistema_simulacion.md](09_sistema_simulacion.md),
  que siguen pendientes.
- **Contexto:** La ventaja que se busca es que `p_yes` reaccione tarde al spot. Si la acción
  decidida con la observación de `t` se ejecuta al mismo precio de `t`, el simulador regala
  justamente ese retraso.
- **Evidencia (30/10/2026):** cada punto del historial refleja el spot de entre 0 y 15 s antes, y
  en la grilla de 1 minuto el precio llega con hasta 60 s de atraso. Con esa grilla, el cambio
  del valor justo "predice" el movimiento siguiente con una correlación de 0,90; alineando el spot
  al instante del precio, baja a 0,22. Ver la decisión D6 en
  [decisiones_previas_al_diseno.md](notas/decisiones_previas_al_diseno.md).
- **Decisión:** `execute_at: next` por defecto, y `current` como ablación. Además, el spot de la
  observación se toma en el instante del último punto de precio (D6).
- **Consecuencias:** Resultados más conservadores. En el último paso (`k = 59`) no se abren
  posiciones.

### ADR-012 — El paquete se llama `polym4v`

- **Estado:** Aceptada el 30/10/2026 (R1)
- **Contexto:** La documentación usaba el nombre provisional `polyrl` y el código existente vive en
  `rl_polymarket`. Hacía falta un nombre único para el paquete, el import y la CLI.
- **Decisión:** `polym4v`: "poly" de Polymarket más el numerónimo de *markov* (m + 4 letras + v),
  porque el problema se formula como un proceso de decisión de Markov.
- **Consecuencias:** `import polym4v`, CLI `polym4v` y carpeta `src/polym4v/`. El código de
  `rl_polymarket` se mueve allí. El nombre del proyecto sigue siendo PolyRL.

### ADR-013 — Comportamiento del simulador: decisiones aceptadas

- **Estado:** Aceptada el 30/10/2026 (R1), después de una revisión independiente.
- **Contexto:** El atraso del precio de Polymarket (D6) mostró que el simulador no tenía un modelo
  de tiempo definido. Las decisiones S1 a S11 de [09_sistema_simulacion.md](09_sistema_simulacion.md)
  lo definen siguiendo prácticas de backtesters y entornos de RL open source.
- **Decisión:**
  - S1: cada dato guarda `ts_event` y `ts_available`, definidos **por campo**. El `open` de una
    vela se conoce al abrir y el `close` al cerrar; `outcome` y `spot_close` solo existen en `w1`.
  - S2: decisiones en una grilla fija de 1 minuto (60 por episodio).
  - S5: la comisión vigente se aplica a todos los mercados, con la fórmula oficial redondeada a 5
    decimales. Un solo parámetro `half_spread` (0,01 base y 0,02 como sensibilidad). La fórmula se
    testea con los ejemplos de la documentación oficial.
  - S6: una acción inválida se ejecuta como `WAIT`, con `lambda_invalid = 0`. Se guardan la acción
    pedida y la ejecutada. PPO principal sin máscara; MaskablePPO queda como P2.
  - S7: `gymnasium.Env` propio, con versiones fijadas en `uv.lock`. NautilusTrader queda fuera del
    plan. La evaluación recorre cada mercado de test una vez y en orden fijo, y los baselines
    pasan por el mismo entorno que los agentes.
  - S8: el historial crudo de 1 minuto (tokens YES y NO) se captura ya, con metadatos de cada
    petición y hash. ETH se captura como respaldo aunque se use solo si sobra tiempo (D2).
  - S11: los mercados usados en los análisis previos se excluyen de test, y la configuración se
    congela antes de abrir test.
- **Pendiente:** S3 (qué ve el agente), S4 (ejecución y latencia), S9 (valoración de la posición) y
  S10 (fin de episodio). Restricción ya acordada: la tolerancia de ejecución no supera 60 s.
- **Consecuencias:** El contrato de datos (INF-06) suma `ts_available` y una tabla de precios
  crudos. Se agregan las tareas DAT-10 (captura) y ENV-10 (tests de no-fuga).

### ADR-014 — CI/CD vuelve al alcance

- **Estado:** Aceptada el 30/10/2026 (R1). Reemplaza al ADR-010.
- **Contexto:** El ADR-010 había dejado fuera la CI/CD para llegar a la entrega de avances. Con
  esa entrega enviada, el equipo tiene tiempo para retomarla.
- **Decisión:** Se reincorporan INF-03 (CI en cada push a `proyecto`), INF-08 (nightly), INF-09
  (release) y EVA-09 (despliegue de la demo), además de INF-02 (ruff, mypy y pre-commit). Las
  versiones de las herramientas se verificaron con Context7 y con las releases oficiales:
  `actions/checkout@v7`, `astral-sh/setup-uv` v10.3.3 fijado por hash (ya no publica una etiqueta
  `v10`), `actions/upload-artifact@v7`, ruff 0.17.3 y pre-commit-hooks v6.0.0.
- **Consecuencias:** "CI en verde" vuelve a la Definition of Done. Ruff y pre-commit excluyen
  `.skills/` y `.agents/`, que se versionan tal cual. Los tests corren en Python 3.11 y 3.12.

### ADR-015 — El tablero es el documento de tareas

- **Estado:** Aceptada el 31/10/2026 (R1).
- **Contexto:** INF-04 pedía un tablero en GitHub Projects con un issue por tarea. El estado del
  proyecto ya se lleva en `docs/04_tareas.md`, y mantener dos lugares los desincroniza.
- **Decisión:** No hay GitHub Projects ni issues. El tablero es la sección "Tablero" de
  `docs/04_tareas.md`, y cada tarea marca su estado en su fila.
- **Consecuencias:** Los commits y PR referencian el ID de la tarea (`[DAT-05]`), no un número de
  issue. Cada PR que se abre o se mezcla actualiza el tablero. Los bugs también se anotan ahí.

<!-- Plantilla para nuevas decisiones:
### ADR-00X — Título
- **Estado:** Propuesta | Aceptada | Reemplazada por ADR-XXX
- **Contexto:**
- **Decisión:**
- **Consecuencias:**
-->
