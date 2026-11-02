# Historial de prompts

Registro que pide el curso para el documento final (sección 3 de
[10_entrega_final.md](../10_entrega_final.md)): los prompts más relevantes, si el resultado fue
satisfactorio, qué falló y por qué, cómo se evaluó la respuesta y cómo contribuyó la IA. Las
herramientas y sus reglas de uso están en [uso_de_ia.md](uso_de_ia.md).

**Cómo se lleva:** se agrega una entrada cuando un prompt cambia una decisión, produce un
artefacto que se entrega o falla de una forma que enseña algo. No se registra cada consulta. Los
prompts de investigación externa van completos en [investigaciones/](investigaciones/) y aquí solo
se resumen.

**Estado:** borrador inicial del 31/10/2026, armado por R1 a partir de las sesiones con Claude
Code. El equipo lo revisa y completa.

## Resumen

| # | Fecha | Herramienta | Para qué | Resultado |
| --- | --- | --- | --- | --- |
| P1 | 30/10/2026 | Claude Code | Spike de datos: granularidad de las APIs | Satisfactorio |
| P2 | 30/10/2026 | Claude Code | Agentes de apoyo para el proyecto | Falló: creó agentes en vez de reutilizar |
| P3 | 30/10/2026 | Claude Code | Decisiones previas al diseño | Parcial: faltaba el contexto |
| P4 | 30/10/2026 | Claude Code | Calibración del precio (Brier) | Falló: dato corrupto sin filtrar |
| P5 | 30/10/2026 | Claude Code | Relación entre el precio y el spot | Satisfactorio: detectó su propio artefacto |
| P6 | 30/10/2026 | Subagentes de revisión | Consecuencias de las decisiones S1 a S8 | Satisfactorio |
| P7 | 30/10/2026 | Claude Code y Context7 | Versiones de herramientas y CI | Satisfactorio |
| P8 | 31/10/2026 | Claude Code | Captura del crudo en segundo plano | Parcial: falló dos veces por causas distintas |
| P9 | 31/10/2026 | Claude Code | EDA sobre train | Satisfactorio |
| P10 | 31/10/2026 | Perplexity | Comisión exacta de Polymarket | Satisfactorio, con vacíos |
| P11 | 31/10/2026 | Subagente `academic-statistician` | Revisar el protocolo de evaluación | Satisfactorio: cuatro fallas graves |
| P12 | 31/10/2026 | Claude Code | ¿Es realista S4 en un CLOB? | Satisfactorio: cambió la pregunta de S4 |
| P14 | 01/11/2026 | Claude Code | Revisión de R3 de los PR del entorno | Satisfactorio: un hueco en la config de la ablación |
| P15 | 02/11/2026 | Claude Code | Mezclar la pila, entrenar y evaluar en test | Satisfactorio: cuatro fallas encontradas en el camino |

## Entradas

### P1 — Spike de datos

- **Prompt:** "quiero ver cómo integrar API, cómo jalar data, pasar por ETL si hace falta, explorar
  y dejar input y generar diseño para entrenar modelo".
- **Resultado:** satisfactorio. Midió que el CLOB entrega un punto por minuto en mercados cerrados
  y llevó a elegir la familia *Bitcoin Up or Down* horaria (ADR-004 y ADR-007).
- **Cómo se evaluó:** cada número de [spike_datos.md](../notas/spike_datos.md) sale de una consulta
  reproducible a la API.
- **Aporte:** ahorró días de exploración manual de tres APIs.

### P2 — Agentes de apoyo

- **Prompt:** "miremos qué skills nos pueden ayudar ... agency-agents ... usarla y saber con qué y
  por qué se usa".
- **Resultado:** falló. La IA escribió agentes nuevos en vez de copiar los existentes.
- **Por qué:** interpretó "usar" como "crear a partir de". La instrucción no decía explícitamente
  que no se creara nada.
- **Corrección:** se copiaron sin modificar los agentes de agency-agents y del catálogo de diseño
  (`.agents/`), y la regla quedó escrita: no se crean agentes ni skills.
- **Aporte:** una vez corregido, los agentes de revisión se usaron en P6.

### P3 — Decisiones previas al diseño

- **Prompt:** "determinemos qué preguntas necesitan decisión antes de hacer un diseño".
- **Resultado:** parcial. La lista de decisiones era correcta, pero se pidió elegir sin explicar
  de dónde salía cada una.
- **Por qué:** la IA asumió el contexto de la propuesta como conocido.
- **Corrección:** cada decisión se explica desde el paso de la propuesta que la origina (sección 0
  de [decisiones_previas_al_diseno.md](../notas/decisiones_previas_al_diseno.md)).

### P4 — Calibración del precio

- **Prompt:** parte del análisis de P1, medir qué tan calibrado está el precio.
- **Resultado:** falló en el primer intento: el Brier dio 25 078, imposible para probabilidades.
- **Por qué:** un mercado tenía precios corruptos (5000,49) y no se filtraron los valores fuera
  de `[0, 1]`.
- **Cómo se detectó:** el valor no era posible y se revisó antes de usarlo.
- **Corrección:** se filtró el rango. Hoy el contrato de `prices_raw` rechaza esos precios y el
  dataset descarta el mercado (DAT-05).

### P5 — Relación entre el precio y el spot

- **Prompt:** parte del análisis de P1, medir si el precio reacciona tarde al spot.
- **Resultado:** satisfactorio. La correlación de 0,90 parecía una ventaja enorme; la IA la marcó
  como sospechosa y la verificó con klines de 1 segundo: alineando los relojes cae a 0,22.
- **Cómo se evaluó:** una segunda medición independiente, con otra resolución temporal.
- **Aporte:** reveló que el problema central era el modelo de tiempo y dio origen a las decisiones
  S1 a S11 del simulador. La EDA del 31/10/2026 lo confirmó con todo train.

### P6 — Consecuencias de las decisiones S1 a S8

- **Prompt:** "antes de responderte, que otro agente valide consecuencias de ponerle sí o más bien
  seguir tus sugerencias, qué perdemos y qué no por cada punto".
- **Herramienta:** subagentes `specialized-master-plan-architect` y `specialized-model-qa`, como
  revisores independientes.
- **Resultado:** satisfactorio. Encontraron una fuga de información por la tolerancia de 90 s, la
  contaminación del test por análisis previos (S11) y la "ventaja fantasma" de `edge`.
- **Cómo se evaluó:** cada hallazgo se contrastó con los datos. La ventaja fantasma se confirmó en
  la EDA (P9).
- **Aporte:** evitó un simulador que habría regalado ganancias falsas al agente.

### P7 — Versiones de herramientas y CI

- **Prompt:** "hagamos un MCP de Context7 para que pueda usarse ... y se haga código actualizado".
- **Resultado:** satisfactorio. Con documentación actual se detectó que `setup-uv` ya no publica la
  etiqueta `v10` (se fijó por hash) y que `from __future__ import annotations` está en desuso en
  Python 3.14.
- **Cómo se evaluó:** contra las releases oficiales de cada herramienta.

### P8 — Captura del crudo

- **Prompt:** continuar la captura del historial de todos los mercados (S8).
- **Resultado:** parcial. La captura se cortó dos veces. Primero, un `pkill -f` cerró la propia
  terminal del agente, porque el patrón coincidía con su comando. Después, una falla de red al
  listar los mercados cortó todo, porque el SDK solo reintenta los 429.
- **Corrección:** se reintenta la misma página ante fallas de red, con test (DAT-10). La captura
  terminó con 12 471 mercados y sin errores.
- **Aporte:** la captura es reanudable, y repetirla no vuelve a llamar a la red.

### P9 — EDA sobre train

- **Prompt:** "hagamos lo que está sin bloqueos".
- **Resultado:** satisfactorio. Notebook ejecutado solo con train y 8 figuras comentadas. Cada
  conclusión se apoya en una cifra del notebook.
- **Cómo se evaluó:** el notebook verifica con un `assert` que no carga val ni test, y la regla de
  `edge` se midió de dos formas (precio de `t` y precio siguiente) para separar la ventaja real
  del atraso de los datos.
- **Aporte:** dio evidencia para decidir S3 y S4.

### P10 — Comisión exacta de Polymarket

- **Prompt:** completo en [investigaciones/comisiones_polymarket.md](investigaciones/comisiones_polymarket.md),
  con la respuesta y su evaluación.
- **Resultado:** satisfactorio, con vacíos. Confirmó la fórmula, el redondeo a 5 decimales y la
  tabla oficial de ejemplos, y marcó como "no confirmado" lo que no tenía fuente. No confirmó el
  esquema `crypto_fees` ni el tick.
- **Por qué los vacíos:** no relacionó el "1,56 % en 50 %" del changelog con `rate 0,25` y
  `exponent 2`, y citó una frase técnica que contradice la fórmula sin advertirlo.
- **Cómo se evaluó:** cada punto se contrastó con su fuente y con el crudo. Las fechas de creación
  de los mercados de cada esquema y el tick de los 12 471 mercados cubrieron los vacíos.
- **Corrección:** la respuesta reveló un error del código: una comisión por debajo de 0,00001 se
  cobra como cero, no como el mínimo. Se corrigió en ENV-03.
- **Aporte:** los ejemplos oficiales pasaron a ser tests de ENV-03.

### P11 — Revisión del protocolo de evaluación

- **Prompt:** revisar críticamente el borrador de EVA-01 (unidad de análisis, dependencia entre
  días, semillas, mejor baseline, correcciones y diferencias iguales a cero) y proponer cambios
  concretos.
- **Herramienta:** subagente `academic-statistician`, como revisor independiente.
- **Resultado:** satisfactorio. Encontró cuatro fallas graves del primer borrador: el "mejor
  baseline" sería casi seguro `NoTrade`, el IC ignoraba la variación entre semillas, el umbral del
  1 % no era detectable y faltaba distinguir "no supera" de "no se pudo saber".
- **Cómo se evaluó:** cada hallazgo se contrastó con D1, D3 y D4 y con los tamaños reales de los
  splits antes de aceptarlo.
- **Aporte:** el protocolo del PR #8 incorpora todos los cambios (sección 11 del protocolo).

### P12 — ¿Es realista la ejecución de S4 en un CLOB?

- **Prompt:** "¿Es correcto nuestro modelo de ejecución S4 considerando que Polymarket utiliza un
  CLOB? ... Revisa qué datos históricos tenemos disponibles y determina si el modelo actual es
  realista o introduce ganancias artificiales ... sin inventar liquidez que no podemos verificar".
- **Resultado:** satisfactorio. Con los trades taker públicos de 60 mercados se midió que el
  historial se parece más a un punto medio que al último trade, que el modelo es conservador en
  promedio y que la liquidez no alcanza siempre para 100 USDC.
- **Cómo se evaluó:** contra precios realmente pagados, también en los minutos en que la
  estrategia operaría. El script queda en `notebooks/s4_ejecucion_clob/`.
- **Aporte:** S4 pasó de una pregunta sobre latencia a dos (S4a y S4b), con la liquidez como
  factor nuevo. La condición que puso R1 (validar cada ejecución, no solo el promedio) mostró que
  solo el 58 % de las ejecuciones simuladas está respaldado por un trade real, y de ahí salieron
  el modo estricto de evaluación, DAT-11 y EVA-11.

### P13 — Recompensa del entorno

- **Prompt:** completo en
  [investigaciones/recompensas_rl_trading.md](investigaciones/recompensas_rl_trading.md). R1 pidió
  investigar cómo diseñan la recompensa FinRL, TensorTrade, Gym-Trading-Env y la literatura sobre
  PnL, drawdown y riesgo antes de decidir entre `pnl` y `pnl_risk`, y comparar con ablaciones.
- **Herramienta:** Claude Code para el código de los repositorios; Perplexity para la literatura.
- **Resultado:** satisfactorio con reservas.
- **Por qué:** las 8 citas de arXiv existen, y casi todo lo que se les atribuye está en ellas. La
  respuesta interpretó mal nuestra recompensa: dijo que el costo de salida castiga la entrada en
  cada paso, y en `pnl` se descuenta una sola vez. Tuvo errores menores en autores, en una fórmula
  y en el alcance de dos artículos.
- **Cómo se evaluó:** se leyó el resumen y el PDF de cada artículo citado, y el DOI de Moody y
  Saffell se comprobó en Crossref. Los argumentos sobre nuestro caso se contrastaron con el código
  de `reward.py` y su test.
- **Corrección:** ninguna en el código. Para próximos prompts, conviene incluir la fórmula exacta
  de la recompensa actual, no solo describirla.
- **Aporte:**
  - Ninguno de los cinco proyectos revisados castiga el drawdown en cada paso, y todos valoran a
    precio de mercado. La penalización de `docs/02` es diseño propio, y con la valoración de S9
    castiga dos veces la entrada.
  - Con la teoría de shaping por potencial de Ng et al., `pnl` resulta casi equivalente a la
    recompensa terminal. La ablación compara entonces la velocidad de aprendizaje y no la política
    óptima.
  - Salió una lista revisada de seis variantes en dos etapas, con 5 semillas. R1 la aprobó el
    01/11/2026 y está implementada en el PR #23.

### P14 — Revisión de R3 de los PR del entorno

- **Prompt:** R3 pidió revisar la documentación y el proyecto, usar el grafo de graphify para
  ubicarse y empezar con lo que le toca a su rol: la revisión de #1, #6, #11, #15, #17 y #23.
- **Resultado:** satisfactorio.
- **Por qué:** se revisó el código de `env/` y la configuración de la recompensa contra el MDP de
  `docs/notas/mdp.md` y las decisiones S4, S6, S9 y S10. Apareció un hueco: `pnl_risk` sin
  `lambda_dd` y `pnl_hold` sin `lambda_hold` se aceptaban y recompensaban igual que su base.
- **Cómo se evaluó:** la suite completa en la cima de la pila (`feat/env-05-variantes`, 269 tests
  y mypy), más una corrida aleatoria por variante para comprobar que la suma de recompensas cuadra
  con la caja final. El hueco se confirmó primero con un test que fallaba.
- **Corrección:** ninguna sobre la respuesta.
- **Aporte:** commit `fix(env)` en #23: la config exige la penalización en esas dos variantes, y
  las estrategias de `hypothesis` ya no generan una lambda de 0.

### P15 — Mezclar la pila, entrenar y evaluar en test

- **Prompt:** R1 pidió verificar si se podían mezclar los PR y empezar a entrenar, asumir los roles
  sin dueño para terminar y usar la GPU para entrenar.
- **Resultado:** satisfactorio.
- **Por qué:** se mezclaron los 34 PR, cada uno con la razón escrita cuando faltaba su revisor, y se
  siguió el protocolo de EVA-01 hasta test: ablación, umbrales de los baselines, búsqueda de
  hiperparámetros, entrenamiento final, reporte de val y una sola evaluación en test. Cada decisión
  de diseño (clasificación simétrica, modo de entrenamiento, valores de la etapa B, grilla de
  AGT-09 y abrir test) la tomó R1 con una recomendación y sus razones.
- **Cómo se evaluó:** la suite completa y el smoke después de cada merge, un ensayo de punta a punta
  de la evaluación en val con modelos de la ablación antes de usar los finales, y la medición de
  CPU contra GPU antes de decidir dónde entrenar.
- **Corrección:** la GPU que pidió R1 no se usó: medida en la RTX 5070, fue entre 3 y 7 veces más
  lenta que la CPU con estas redes de 64 × 64 (tabla en `docs/04_tareas.md`).
- **Aporte:** cuatro fallas encontradas en el camino: el dataset offline podía reusar recompensas
  viejas, a la demo le faltaba el componente `hold`, la tabla del protocolo se rompía en Markdown y
  faltaba el ajuste de umbrales de los baselines que pide el protocolo.

## Plantilla

```markdown
### PN — Título

- **Prompt:** el texto o un resumen fiel, con enlace si está completo en otro archivo.
- **Herramienta:** si no es Claude Code.
- **Resultado:** satisfactorio, parcial o falló.
- **Por qué:** sobre todo si falló o fue parcial.
- **Cómo se evaluó:** contra qué se verificó la respuesta.
- **Corrección:** qué se hizo después, si hizo falta.
- **Aporte:** qué cambió en el proyecto.
```
