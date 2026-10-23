# 01 — Idea general

## 1. Contexto

[Polymarket](https://polymarket.com) es un mercado de predicción. Cada mercado es una pregunta
binaria (por ejemplo, *"¿Bitcoin cerrará por encima de su precio de apertura en esta hora?"*) con dos
tokens, **YES** y **NO**. Los precios están entre `0` y `1` y se pueden leer como probabilidades
implícitas. Cuando el mercado se resuelve, el token ganador paga `1` y el perdedor paga `0`.

Esto lo convierte en un buen banco de pruebas para RL:

- Los **episodios son naturales**: cada mercado tiene inicio, evolución y una resolución conocida.
- La **recompensa final es objetiva**: al resolverse se sabe exactamente cuánto se ganó o perdió.
- Hay **muchos episodios homogéneos**: los mercados recurrentes de BTC/ETH (por ejemplo,
  *"Bitcoin Up or Down"* por hora o por día) generan cientos de episodios parecidos.

## 2. Problema

Dado el estado de un mercado en el instante `t` (precio YES/NO, su historia reciente, tiempo hasta
la resolución, precio spot de BTC/ETH y la posición actual del agente), decidir una acción:

| Acción | Significado |
|--------|-------------|
| `WAIT` | No hacer nada (mantener la posición actual, o seguir sin posición) |
| `BUY_YES` | Abrir una posición en YES con un monto fijo del saldo |
| `BUY_NO` | Abrir una posición en NO con un monto fijo del saldo |
| `SELL` | Cerrar la posición abierta al precio actual del mercado |

**Todo ocurre en simulación** y con **saldo ficticio**. Polymarket solo se usa como fuente de datos
históricos. El agente nunca opera en vivo.

## 3. Objetivo

> Comprobar si un agente de RL puede aprender una política de decisión que aproveche la
> información del mercado **mejor que estrategias básicas**, medida fuera de muestra
> (en mercados que el agente nunca vio durante el entrenamiento).

### Objetivos específicos

1. Construir un **pipeline de datos** reproducible que descargue, limpie y guarde mercados
   históricos de Polymarket sobre BTC/ETH.
2. Implementar un **entorno simulado** compatible con Gymnasium que reproduzca esos mercados paso a
   paso.
3. Diseñar y justificar una **función de recompensa** que tome en cuenta beneficio, pérdidas, riesgo
   y el momento de entrada y salida.
4. Entrenar y comparar tres familias de agentes: **PPO**, **DQN** y **Offline RL** (Discrete CQL o
   Behavior Cloning).
5. Hacer un **backtesting** con estrategias base (aleatoria, no operar, momentum, reversión a la
   media, "favorito").
6. Entregar una **demo** que reproduzca un mercado histórico y muestre, instante a instante, la
   acción del agente, su posición y la evolución del saldo simulado.

## 4. Técnicas

| Técnica | Rol en el proyecto |
|---------|--------------------|
| **PPO** (on-policy, actor-crítico) | Agente principal. Aprende la política directamente y es estable. |
| **DQN** (off-policy, basado en valor) | Punto de comparación. Aprende `Q(s, a)` para cada acción discreta. |
| **Offline RL** (Discrete CQL / BC) | Aprende a partir de un dataset fijo de transiciones, sin interactuar con el entorno. |
| **Backtesting** | Reproduce mercados pasados para medir el PnL y el riesgo de cada estrategia. |
| **Reward shaping** | Define qué significa "hacerlo bien" y es una de las variables que se estudian. |

> **Nota conceptual (importante para el informe):** entrenar PPO o DQN en un simulador que
> *reproduce* datos históricos sigue siendo RL **online**, porque el agente interactúa con el
> entorno y elige qué experiencias ve. **Offline RL** significa aprender de un dataset de
> transiciones **fijo**, recolectado antes por otras políticas, sin volver a interactuar. El
> proyecto implementa ambos enfoques y los compara.

## 5. Alcance

### Dentro del alcance

- Mercados binarios de Polymarket sobre **BTC** (y **ETH** si da el tiempo), ya resueltos.
- Precios históricos con granularidad de minutos u horas, según lo que entregue la API.
- Un simulador **price-taker**: las acciones del agente no mueven el precio.
- Costos simulados configurables: *spread*, *slippage* y comisión.
- Una sola posición abierta a la vez y tamaño de apuesta fijo.
- Evaluación con varias semillas e intervalos de confianza.
- Demo local (Streamlit) y un informe final.

### Fuera del alcance

- Operar con dinero real o conectarse a una wallet.
- Simular el libro de órdenes completo (profundidad, impacto de mercado). Polymarket no publica
  historia del order book, así que se aproxima con un spread fijo.
- Mercados multi-resultado (más de dos outcomes).
- Modelos de lenguaje o análisis de noticias.
- Infraestructura de producción (Kubernetes, bases de datos distribuidas, etc.).

## 6. Hipótesis

- **H1:** Un agente PPO entrenado con la recompensa propuesta obtiene un retorno medio fuera de
  muestra mayor que el de la mejor estrategia base, con un intervalo de confianza del 95 % que no
  incluye la diferencia cero.
- **H2:** Una penalización de riesgo (drawdown) en la recompensa reduce el drawdown máximo sin
  reducir el retorno de forma significativa.
- **H3:** Offline RL entrenado con transiciones de políticas heurísticas iguala o supera a la mejor
  política que generó el dataset.

Si las hipótesis **no** se cumplen, el proyecto igual es exitoso siempre que la evaluación sea
rigurosa y el resultado negativo esté bien explicado. Un mercado eficiente es una conclusión
válida.

## 7. Criterios de éxito (entregables evaluables)

| # | Criterio | Cómo se verifica |
|---|----------|------------------|
| C1 | Dataset reproducible | `polyrl data build` genera el mismo dataset (hash) a partir de la configuración |
| C2 | Entorno validado | Pasa `gymnasium.utils.env_checker.check_env` y los tests de conservación del dinero |
| C3 | 3 agentes entrenados | PPO, DQN y Offline RL con checkpoints guardados y curvas de entrenamiento |
| C4 | Comparación rigurosa | Tabla de métricas en el conjunto de test, con ≥ 5 semillas e IC 95 % |
| C5 | Demo funcional | La app reproduce un mercado de test y muestra acción, posición y saldo en cada paso |
| C6 | Calidad de software | La CI pasa en la rama `proyecto`, la cobertura es ≥ 70 % en `src/` y hay README de instalación |
| C7 | Informe final | Metodología, resultados, ablación de la recompensa, limitaciones y trabajo futuro |

## 8. Resultado esperado

Una demo donde se elige un mercado histórico del conjunto de test y se reproduce paso a paso:

```
t = 14:32   p(YES) = 0.61   BTC = 67 412   Acción: BUY_YES   Posición: 16.4 YES   Saldo: 990.00
t = 14:33   p(YES) = 0.64   BTC = 67 455   Acción: WAIT      Posición: 16.4 YES   Valor: 1000.49
...
t = 15:00   RESUELTO: YES   Liquidación: 16.4 × 1.00          Saldo final: 1006.40
```

Junto con gráficos del precio con marcas de entrada y salida, la curva de capital del agente frente
a las estrategias base, y una tabla de métricas.
