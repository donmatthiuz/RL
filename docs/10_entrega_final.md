# 10 — Entrega final

Fuente: instrucciones del proyecto del curso de Aprendizaje por Refuerzo (Canvas, UVG). Este
documento no las copia: selecciona lo que hay que entregar, dice dónde vive cada cosa en el
repositorio y revisa si el proyecto cumple. Las tareas que salen de aquí son las `DOC-*` de
[04_tareas.md](04_tareas.md).

## 1. Qué se entrega y cuánto vale

| Entregable | Qué se pide | Dónde vive | Puntos | Estado |
| --- | --- | --- | --- | --- |
| Aprobación del tema | Propuesta y correo de aprobación | [propuesta](../entregas/propuesta/), [evidencias](images/evidencias/) | 3 | Hecho |
| Documento | PDF con las secciones de la sección 2 y el enlace al repositorio | [entregas/final/informe/](../entregas/final/informe/) | 5 | Estructura lista |
| Repositorio | Público, con todo el código y el documento | `github.com/donmatthiuz/RL`, rama `proyecto` | 1 | Público (verificado el 31/10/2026) |
| Video | Funcionamiento, implementación y hallazgos principales | [entregas/final/video/](../entregas/final/video/) | 1 | Pendiente |
| Slides | Máximo 10, en HTML, con su versión PDF | [entregas/final/presentacion/](../entregas/final/presentacion/) | 5 | Pendiente (al final) |
| Presentación | Exposición en clase y respuestas a las preguntas | En clase | 10 | Pendiente |
| Calidad de la solución | Implementación funcional y verificada | `src/`, `tests/`, CI | 5 | En curso |

En Canvas se suben dos archivos: el **PDF del documento**, que incluye el enlace al repositorio, y
el **PDF de las slides**.

## 2. Secciones del documento

Cada sección es un archivo en [entregas/final/informe/](../entregas/final/informe/) que dice qué
tiene que contener y de dónde sale el material.

| Sección | Qué tiene que mostrar | Material en el repositorio | Tarea |
| --- | --- | --- | --- |
| Descripción del problema | El problema real y por qué importa | [01_idea_general.md](01_idea_general.md), propuesta | DOC-02 |
| Análisis | Datos, EDA, supuestos y riesgos | [08](08_datos_y_entrada_modelo.md), [EDA](../notebooks/eda/) (PR #7), [spike](notas/spike_datos.md), [decisiones previas](notas/decisiones_previas_al_diseno.md) | DOC-03 |
| Propuesta de solución | Por qué RL, el MDP y las alternativas | [02](02_arquitectura.md), [09](09_sistema_simulacion.md) | DOC-04 |
| Descripción de la solución | Datos, entorno, agentes, evaluación e ingeniería | [02](02_arquitectura.md), [08](08_datos_y_entrada_modelo.md), [09](09_sistema_simulacion.md), `src/` | DOC-05 |
| Herramientas aplicadas | Las no vistas en clase, en detalle; los prompts de IA y la evolución de la idea | [ia/](ia/), [07](07_riesgos_y_decisiones.md) | DOC-06 |
| Resultados (métricas) | Métricas contra los baselines, con intervalos | `reports/` (cuando existan) | DOC-07 |
| Conclusión | Qué se aprendió y qué funcionó o no | Resultados | DOC-08 |
| Bibliografía | Fuentes citadas y verificadas | [ia/investigaciones/](ia/investigaciones/) y las de cada sección | DOC-09 |

El documento también tiene que dejar ver el **proceso iterativo**: las decisiones (ADR y S1 a
S11), lo que se descartó y por qué, y cómo cambió la idea desde la propuesta.

## 3. Uso de IA

El curso pide usar la IA de forma crítica y documentarlo en el documento. Lo que tiene que estar:

- El historial de los prompts más relevantes.
- Cuáles dieron un resultado satisfactorio y cuáles fallaron o no respondieron lo pedido, y por qué.
- Cómo se evaluó cada respuesta y cómo contribuyó la IA al trabajo.

Dónde se lleva, **durante todo el proyecto** y no al final:

- [ia/historial_prompts.md](ia/historial_prompts.md): el historial con la evaluación de cada
  prompt.
- [ia/investigaciones/](ia/investigaciones/): los prompts de investigación externa (Perplexity),
  con la respuesta pegada y cómo se usó. Sirven también como referencias.
- [ia/uso_de_ia.md](ia/uso_de_ia.md): qué agentes, skills y herramientas se usan y por qué.

## 4. Slides y presentación

Las **slides** (5 puntos) son el HTML; la **presentación** (10 puntos) es la exposición en clase.

- **Formato:** HTML propio, sin PowerPoint ni Canva.
- **Controles:** flechas para avanzar y retroceder, `p` para pantalla completa y `o` para la vista
  general de las slides.
- **Transiciones:** entre slides.
- **Versión PDF:** un script `.sh` la genera para subirla a Canvas.
- **Extensión y contenido:** máximo 10 slides, siguiendo las secciones del documento.
- **Diseño:** se define al final, con un `DESIGN.md` y referencias que hoy no existen. Hasta
  entonces no se construye.

## 5. Video

Muestra la solución funcionando (la demo), cómo está implementada y los hallazgos principales.
El guion y el enlace van en [entregas/final/video/](../entregas/final/video/).

## 6. ¿Cumplimos?

Revisión del 31/10/2026:

| Requisito | Estado | Nota |
| --- | --- | --- |
| Tema de RL con aplicación real | Cumple | Mercados de predicción reales, con datos históricos y costos reales |
| Más allá de lo que resuelve un prompt | Cumple | Pipeline de datos, simulador propio, tres familias de agentes y evaluación estadística |
| Proceso iterativo demostrable | Cumple; falta contarlo | ADR, decisiones S1 a S11, PR y entregas parciales. Va en el documento (sección 2) |
| Técnicas del curso | En curso | PPO, DQN y Offline RL (CQL y BC) |
| Corroborar si funciona o no | En curso | Comparación contra baselines con los mismos costos (D1); si nada gana, se reporta (D4) |
| Repositorio público | Cumple | Verificado el 31/10/2026 |
| Secciones del documento | **Corregido hoy** | Las tareas `DOC-*` seguían otra estructura (introducción, metodología, discusión). Se alinearon con las secciones exigidas |
| Herramientas no vistas en clase, en detalle | Pendiente | Candidatas, a confirmar con las anotaciones del curso: APIs de Polymarket y Binance, Gymnasium, Stable-Baselines3, d3rlpy, pandera, uv y GitHub Actions |
| Historial de prompts con evaluación | **Faltaba; iniciado hoy** | [ia/historial_prompts.md](ia/historial_prompts.md) |
| Video | **No estaba en el plan; agregado** | DOC-11 |
| Slides en HTML con PDF | **No estaba definido; agregado** | DOC-10 |
| Bibliografía | **No era una sección; agregada** | DOC-09 |
