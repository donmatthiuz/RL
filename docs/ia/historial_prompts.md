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
| P13 | 01/11/2026 | Claude Code y Perplexity | Recompensa del entorno | Satisfactorio con reservas |
| P14 | 01/11/2026 | Claude Code | Revisión de R3 de los PR del entorno | Satisfactorio: un hueco en la config de la ablación |
| P15 | 02/11/2026 | Claude Code | Mezclar la pila, entrenar y evaluar en test | Satisfactorio: cuatro fallas encontradas en el camino |
| P16 | 02/11/2026 | Claude Code | Qué aprendió cada agente (XAI) | Parcial: dos cifras y cinco afirmaciones corregidas |
| P17 | 02/11/2026 | Claude Code | Explicar el agente y el avance del 02/11 | Parcial: corregidos el minuto 59, los redondeos y el signo del PDF |
| P18 | 02/11/2026 | Claude Code | Cierre técnico | Satisfactorio |
| P19 | 08/11/2026 | Claude Code | Diseño de la demo | Satisfactorio |
| P20 | 09/11/2026 | Claude Code y MCP de Chrome | Ajustes de la demo con la skill de Streamlit | Satisfactorio |
| P21 | 09/11/2026 | OpenCode (DeepSeek V4.1 Flash Free) | Diseño de la presentación final | Satisfactorio: corrigió la sección 9 tras la nota de R1 |
| P22 | 09/11/2026 | OpenCode (DeepSeek V4.1 Flash Free) | Fuentes, referencias y registro de IA del diseño | Satisfactorio |
| P23 | 09/11/2026 | OpenCode (DeepSeek V4.1 Flash Free) | Base de `index.html` y slides 1 a 3 | Satisfactorio: composición y accesibilidad corregidas |
| P24 | 09/11/2026 | Claude Code y Context7 | Publicar la demo en Cloud Run | Satisfactorio: imagen probada en local antes de desplegar |

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

### P16 — Qué aprendió cada agente (XAI)

- **Prompt:** R1 preguntó qué dice el resultado, qué funcionó y qué no, si se puede hacer XAI y
  cómo prepararse para las preguntas de la presentación, y pidió dejar el análisis como evidencia en
  los reportes.
- **Resultado:** parcial.
- **Por qué:** la primera respuesta se apoyó en un conteo rápido sobre las trayectorias que daba por
  hecho que cada compra se mantenía hasta el final. Con las operaciones reales, con sus ventas, PPO
  pierde −27,23 USDC en test en las compras a más de 0,98, no −19,1, y las dos pérdidas grandes
  resultaron ser el mismo mercado en dos semillas. Además afirmó de más: que PPO predice cuándo el
  resultado está decidido, que le gana a alguien que no sabe operar y que CQL sobreajustó.
- **Cómo se evaluó:** una revisión externa pegada por R1 marcó cinco afirmaciones sin demostrar, y
  cada una se contrastó con una medición: la importancia por permutación (PPO decide con el spot),
  la calibración del precio (el precio ya cubre lo que PPO aprovecha) y las operaciones de CQL (sus
  10 mejores apuestas de val suman más que su ganancia total). Antes de permutar, se comprobó que
  volver a correr cada agente en val da las mismas acciones que sus trayectorias.
- **Corrección:** el informe usa las operaciones reales, y cada afirmación lleva su límite:
  exploratorio, fuera del protocolo, en val, y test solo descrito, sin volver a evaluar.
- **Aporte:** EVA-12, `polym4v behavior` y `make behavior`, con `reports/val/behavior.md` y
  `reports/test/inspection.md`.

### P17 — Explicar el agente y el avance del 02/11

- **Prompt:** R1 pidió explicar de forma simple qué haría el agente si se pusiera a operar hoy (con
  qué monto empieza, cuál es la primera transacción) con una animación para quien no conoce el
  proyecto, y después actualizar el reporte de avance al 02/11/2026.
- **Resultado:** parcial.
- **Por qué:** la primera versión de la animación mostraba en el minuto 59 la cuenta ya liquidada y
  decía que el agente "ya no puede comprar" mientras seguía con la posición, y redondeaba precios
  como 0,9885 a 0,989, justo la diferencia que explica por qué pierde. En el PDF, la fuente no tiene
  el signo menos (U+2212) y los resultados negativos de test salían sin signo.
- **Cómo se evaluó:** las cifras de la animación se sacaron de las trayectorias reales (un mercado
  que gana, uno que espera y uno que pierde, y el día del 15/08/2026) y se compararon con
  `reports/`. El PDF se revisó página por página como imagen y con su texto extraído.
- **Corrección:** el minuto 59 muestra la posición del minuto 58 hasta el cierre, los precios van
  con cuatro decimales y el PDF usa el guion como signo.
- **Aporte:** una explicación visual para la presentación y el video, y el avance del 02/11 en
  `entregas/2026-11-02/`.

### P18 — Cierre técnico

- **Prompt:** R1 pidió hacer todo lo que falta salvo el documento, las slides, el video, el ensayo y
  la entrega en Canvas, y dejar lo demás listo para seguir. Decidió con R1 el contenido del Release,
  que Mathew corra la reproducción y despliegue la demo, y que los PR los mezcle R1.
- **Resultado:** satisfactorio.
- **Por qué:** al revisar EVA-08 apareció que la demo proponía la mejor corrida suelta de test
  (DQN s4), no el mejor agente del protocolo; se cambió por el agente con mayor media de D,
  mostrado con su semilla mediana (PPO s0). El release no podía recalcular el reporte en la CI,
  porque los datos y los modelos no se versionan.
- **Cómo se evaluó:** la demo se probó con las trayectorias reales y en un entorno que simula
  Streamlit Community Cloud (solo `app/requirements.txt`, sin torch ni el paquete instalado). La
  guía de reproducción se ensayó en un clon limpio y dio exactamente el PnL de PPO s0 en val del
  reporte.
- **Aporte:** EVA-08 (#36), la demo lista para publicar (EVA-09), `release.yml` y
  `make release-modelos` (INF-09) y la guía de INF-10 en el README (#37).

### P19 — Diseño de la demo

- **Prompt:** R1 pidió una demo más visual e interactiva dentro de los límites de Streamlit, con
  marca, la simulación de la hora con BTC, el reloj y el precio, secciones separadas para comparar
  y para explicar las políticas, el mercado y las trayectorias, botones en lugar del toggle, y que
  los agentes de diseño orientaran el trabajo.
- **Resultado:** satisfactorio.
- **Por qué:** dos agentes de `.agents/` dieron la base. UX Architect propuso las cuatro páginas, el
  reproductor con `st.fragment` y la narración de cada minuto. UI Designer propuso el sistema
  visual. Su paleta cambiaba el azul y el ámbar del `DESIGN.md` que R1 estaba escribiendo para la
  presentación; se mantuvo el `DESIGN.md` como fuente común y de su propuesta solo se tomó lo que
  no choca (el color dice el lado y la forma, la acción; BTC en gris neutro).
- **Cómo se evaluó:** tests con AppTest sobre mercados sintéticos (reproducir, pausar, cierre,
  narración, elección del protocolo), capturas reales en Chrome con Playwright de cada página y
  del reproductor, y una copia del repositorio con solo `app/requirements.txt` que simula
  Streamlit Community Cloud. Las capturas mostraron métricas cortadas, un registro saturado de
  pedidos inválidos y un gráfico que no llenaba su tarjeta; se corrigieron. La copia mostró que
  las páginas no se encontraban con una ruta relativa al script.
- **Aporte:** EVA-13: `app/views/`, `app/core.py`, `app/charts.py`, `app/selection.py`, el tema en
  `.streamlit/config.toml` y la muestra de mercados de `make demo-muestra`.

### P20 — Ajustes de la demo con la skill de Streamlit

- **Prompt:** R1 pidió barra lateral también en el inicio, quitar el aviso del pie por
  sobreexplicado, arreglar la falta de simetría, poner "[DEMO]" en el nombre, validar con el MCP de
  Chrome, aplicar el DESIGN.md y usar la skill `developing-with-streamlit` que instaló.
- **Resultado:** satisfactorio.
- **Por qué:** la skill marcó prácticas que la primera versión no seguía: páginas en `app_pages/`,
  margen con `paddingTop` del tema en vez de CSS, `st.switch_page` en lugar de `st.page_link`,
  `title=` en las alertas, `alt=` en gráficos y tablas, límites de caché y métricas con
  `height="stretch"`. El CSS que queda es el que pide el DESIGN.md (superficie blanca de las
  tarjetas y etiquetas en mono), apuntado a claves `card_*` como recomienda la skill.
- **Cómo se evaluó:** con el MCP de Chrome se midió el alto de cada tarjeta y métrica: todas las
  de una fila coinciden. Tests de la demo, suite completa y la copia que simula Community Cloud.
- **Aporte:** EVA-13, PR #41.

### P21 — Diseño de la presentación final

- **Prompt:** "quiero que usando esos agentes de diseño creemos un design md para la presentacion y
  ademas relacionado con la web, sera 1 html la capacidad de que se convierta a pdf para enviar,
  tomemos los agentes y usemoslo para diseño y toma de referencia como hice una presentacion
  `Sentinel_Fase4_final.html` ... esta tiene otro branding otros integrantes asi que fijo cambiaraia,
  es solo de referencia".
- **Herramienta:** OpenCode con el modelo DeepSeek V4.1 Flash Free, sobre la rama `proyecto`.
- **Resultado:** satisfactorio, con una corrección de fondo.
- **Por qué:** los agentes de `.agents/` dieron los marcos que faltaban (Brand Guardian para la
  identidad, UI Designer para los tokens, UX Architect para la retícula, Visual Storyteller para el
  arco y UI Finish-Gate Reviewer para la compuerta). La referencia de Sentinel aportó la estructura
  (lienzo 16:9, navegación por pasos, `?pdf`, `?guion` y el script de exportación), no su marca.
  La primera versión describió la demo como si no tuviera diseño final; R1 corrigió esa premisa.
- **Cómo se evaluó:** cada cifra se contrastó con un archivo del repositorio; la identidad se
  revisó contra el tema real de `.streamlit/config.toml`; el Markdown se revisó con el skill
  `markdown-style` y las tablas con su ancho.
- **Corrección:** la sección 9 pasó de "propuesta de diseño" a "cómo quedó", con las cuatro páginas
  reales, el tema en la raíz, los gráficos Altair y el CSS mínimo. Se corrigió el ejemplo falso de
  la línea 57 sobre PPO en test.
- **Aporte:** `entregas/final/presentacion/DESIGN.md` y la actualización de su `README.md`.

### P22 — Fuentes, referencias y registro de IA del diseño

- **Prompt:** dejar listo el diseño sin construir `index.html`: corregir la sección 9 con la demo
  real, poner la ubicación exacta de cada referencia, agregar la tabla "Fuentes de cada slide",
  definir la captura de la slide 10 y la regla de formato decimal, indicar el origen de los WOFF2,
  actualizar los documentos de IA, pasar Ruff y la compuerta del UI Finish-Gate Reviewer.
- **Herramienta:** OpenCode con el modelo DeepSeek V4.1 Flash Free, en la rama `docs/doc-10-design`.
- **Resultado:** satisfactorio.
- **Por qué:** la tarea obligó a leer el código real de la demo y los reportes, no a confiar en la
  memoria. Aparecieron dos datos que la versión anterior tenía mal: el tema vive en la raíz y no en
  `app/.streamlit/`, y los gráficos son Altair, no matplotlib. También se aclaró que
  `Sentinel_Fase4_final.html` es del proyecto Sentinel del mismo autor, no de otro equipo.
- **Cómo se evaluó:** se leyeron `app/demo.py`, `app/core.py`, `app/charts.py`, `app/selection.py`,
  las cuatro páginas y `.streamlit/config.toml`; las cifras se sacaron de `manifest.json`,
  `reports/val/comparison.csv`, `reports/test/comparison.csv`, `reports/test/summary.csv` y
  `reports/test/inspection_payoff.csv`; se comprobó que el mercado 13/08/2026 12:00 UTC existe en
  la trayectoria de PPO s0 en test y que el minuto 57 ejecuta la compra de YES.
- **Corrección:** se reemplazó "pregúntale a R1 la ruta" por la ruta exacta del archivo y se corrigió
  "entrega de otro equipo" por "proyecto Sentinel del mismo autor".
- **Aporte:** `DESIGN.md` con la sección 9 real, la tabla de fuentes por slide, las referencias
  ubicadas y los pendientes marcados; `README.md` de la presentación y este registro.

### P23 — Base de `index.html` y slides 1 a 3

- **Prompt:** construir la base de `entregas/final/presentacion/index.html` según el `DESIGN.md`:
  tokens, fuentes WOFF2, navegación, modos `?pdf` y `?guion`, las siete plantillas de la sección
  5.2 y las slides 1 a 3 con contenido real y pie de fuente. Verificar en Chrome a 1920 $\times$
  1080, 1280 $\times$ 720 y 1024 $\times$ 768, pasar el UI Finish-Gate Reviewer solo por esas tres
  slides y abrir un PR hacia `proyecto`. No construir las slides 4 a 10 ni tocar `app/`, `src/`,
  `tests/` o `reports/`.
- **Herramienta:** OpenCode con el modelo DeepSeek V4.1 Flash Free, en la rama
  `feat/doc-10-slides`.
- **Resultado:** satisfactorio.
- **Por qué:** el `DESIGN.md` ya tenía los tokens, la retícula, las plantillas y las fuentes de
  cada cifra, así que la implementación no inventó contenido. Los fallos fueron de composición y
  accesibilidad: a 1280 px el lienzo quedaba descentrado y se salía del viewport, la caja de
  resolución de la slide 2 tapaba la marca del `1`, la barra 70/15/15 recortaba la etiqueta de
  validación, la barra de controles desaparecía con foco y la vista general desbordaba a
  1024 $\times$ 768.
- **Cómo se evaluó:** capturas de las tres slides a 1920 $\times$ 1080, 1280 $\times$ 720 y
  1024 $\times$ 768 con Chrome/Playwright; cero errores de consola y cero peticiones de red;
  navegación con flechas, `Home`, `End`, `o` y `n`; `?pdf` y `?guion` exportados a tres páginas de
  1600 $\times$ 900 px; ratios de contraste calculados sobre los tokens; fuentes en estado
  `loaded`; prueba de foco con `Tab` y `Shift+Tab` en la vista general y en la barra de controles.
- **Corrección:** el lienzo se centra con `translate(-50%, -50%) scale(s)`; la caja de resolución
  se movió arriba del eje; la barra usa nombres sobre cada segmento y porcentajes dentro; los
  controles se ocultan en `?estatico` pero no con `prefers-reduced-motion`; la barra permanece
  visible con foco; la vista general atrapa el foco, inertiza el fondo y pasa a dos columnas por
  debajo de 1156 px; el campo de la portada solo se anima en la primera carga o con `r`.
- **Aporte:** `index.html` con la base, las siete plantillas y las slides 1 a 3; `fonts/` con los
  WOFF2 y las licencias OFL; el `README.md` de la presentación actualizado.

### P24 — Publicar la demo en Cloud Run

- **Prompt:** "este proyecto lo subiremos a google cloud, ¿qué necesitamos?" y, con el proyecto de
  gcloud ya iniciado, "dame lo que se necesita para poder desplegar la página y los artefactos
  necesarios para su funcionamiento".
- **Herramienta:** Claude Code, con la documentación de Cloud Run consultada en Context7.
- **Resultado:** satisfactorio.
- **Por qué:** la documentación oficial marcó tres requisitos que no son obvios: Cloud Run corta
  los websockets de Streamlit al llegar al timeout, la afinidad de sesión evita que un usuario
  cambie de instancia, y en proyectos nuevos la cuenta de Cloud Build necesita
  `roles/run.builder` para construir desde el código. Leer `app/core.py` mostró que la demo también
  lee `configs/` y los reportes versionados, no solo `app/`.
- **Cómo se evaluó:** `make demo-imagen` construyó la imagen y la abrió en local; Playwright
  recorrió las cuatro páginas sin excepciones ni errores. Se revisó por dentro que la imagen no
  tuviera `keys/`, `.env`, `data/` ni `models/`, y `gcloud meta list-files-for-upload` confirmó
  que solo se suben 147 archivos (6,3 MB) de `app/`, `src/`, `configs/`, `reports/` y `.streamlit/`.
- **Corrección:** ninguna en el resultado. La CLI de Context7 falló por la clave y se usó su MCP.
- **Aporte:** `Dockerfile`, `.dockerignore` y `.gcloudignore` como listas blancas, `make
  demo-imagen` y `make deploy-gcp`, el ADR-018 y los pasos del README.

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
