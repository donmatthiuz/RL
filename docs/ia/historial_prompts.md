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
| P10 | 31/10/2026 | Perplexity | Comisión exacta de Polymarket | Pendiente |

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

- **Prompt:** completo en [investigaciones/comisiones_polymarket.md](investigaciones/comisiones_polymarket.md).
- **Resultado:** pendiente de la respuesta.

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
