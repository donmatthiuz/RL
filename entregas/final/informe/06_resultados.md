# 06 — Resultados (métricas)

Parte del documento final. Los requisitos están en [docs/10_entrega_final.md](../../../docs/10_entrega_final.md).

**Estado:** pendiente (DOC-07).

## Qué tiene que contener

- Retorno, Sharpe, drawdown, win rate, número de operaciones, costos pagados y porcentaje de acciones inválidas.
- La comparación de cada agente contra los baselines, con intervalos de confianza.
- Val para elegir modelos y test una sola vez, al final.
- La sensibilidad a los costos (medio spread de 0,01 y 0,02, y sin comisión).

## Material disponible

- Las tareas EVA de [04_tareas.md](../../../docs/04_tareas.md); las tablas y figuras saldrán en `reports/`
- La prueba del protocolo en val y test: [reports/val/comparison.md](../../../reports/val/comparison.md)
  y [reports/test/comparison.md](../../../reports/test/comparison.md).
- Qué aprendió cada agente (EVA-12, exploratorio):
  [reports/val/behavior.md](../../../reports/val/behavior.md) e
  [reports/test/inspection.md](../../../reports/test/inspection.md). Va aparte de la prueba del
  protocolo y con estos cuidados:
  - Que PPO decida con el spot no demuestra que prediga mejor que el precio: el precio ya está
    calibrado donde compra.
  - Las heurísticas aproximan comportamientos simples, no a personas: no permiten afirmar que un
    agente le gana a un principiante.
  - La calibración es evidencia limitada: un período, dos minutos y tramos de precio gruesos.
  - La caída de CQL de val a test es compatible con una estrategia de alta varianza elegida en val,
    pero no identifica la causa.
  - La importancia por permutación no es SHAP ni Integrated Gradients: mide qué información usa la
    política, no cuánto aporta cada feature a una decisión puntual.
