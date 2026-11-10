# 03 — Propuesta de solución

Parte del documento final. Los requisitos están en [docs/10_entrega_final.md](../../../docs/10_entrega_final.md).

**Estado:** borrador de R3 (03/11/2026), DOC-04. Falta la revisión de R1 como R4.

## Por qué aprendizaje por refuerzo

Operar un mercado horario de Polymarket no es una sola predicción, sino una secuencia de 60
decisiones, una por minuto, y cada una cambia lo que se puede hacer después:

- **Es secuencial.** Comprar ahora deja una posición abierta que hay que mantener o vender, y el
  saldo disponible condiciona las órdenes siguientes.
- **Cada operación cuesta.** Comprar y vender paga medio spread y la comisión taker. Por eso la
  pregunta no es solo "¿YES o NO?", sino si vale la pena operar y cuándo.
- **La recompensa llega tarde.** El resultado del mercado se conoce recién en `w1`, cuando la
  posición se liquida a 1 o a 0.

Las alternativas sin RL se incluyen en el proyecto como **baselines**, no como solución:

| Alternativa | Por qué no basta | Dónde aparece |
| --- | --- | --- |
| Reglas fijas | No se adaptan al tiempo que queda ni al costo de entrar y salir | `Favorite`, `Momentum` y `MeanReversion` |
| Predecir el resultado (supervisado) | Da una probabilidad, no una política: falta decidir umbrales, momento de entrada y salida con costos | `FairValue`, que opera según el `edge` del valor justo |
| No operar | Es la referencia que hay que superar (protocolo, E2) | `NoTrade` |

## El MDP

Especificación completa en [docs/notas/mdp.md](../../../docs/notas/mdp.md).

| Elemento | Definición | Decisión |
| --- | --- | --- |
| Episodio | Un mercado *Bitcoin Up or Down* horario: la vela `[w0, w1)` | ADR-004, ADR-008 |
| Instantes de decisión | `t_k = w0 + 60·k`, con `k = 0..59` | S2 |
| Estado | 16 valores: 13 features de mercado (precio, cambios recientes, antigüedad del precio, retorno del spot, volatilidad, tiempo restante, valor justo y `edge`) y 3 del agente (`pos_side`, `entry_price` y PnL no realizado). Solo datos con `ts_available ≤ t_k` | S1, S3 |
| Acciones | `Discrete(4)`: `WAIT`, `BUY_YES`, `BUY_NO` y `SELL`; 20 USDC por compra y una posición a la vez | ADR-005, S4b |
| Transición | La orden se ejecuta al primer precio real en `(t + 2 s, t + 60 s]`, con medio spread de 0,01 y la comisión taker de Polymarket. Si no hay precio, se cancela. El agente no mueve el precio y `p_no = 1 - p_yes` | S4, S5, ADR-003 |
| Acciones inválidas | Se ejecutan como `WAIT` y `action_masks()` las expone | S6 |
| Fin | No se abren posiciones en los últimos 2 minutos; en `w1` la posición paga 1 o 0, sin comisión | S10 |
| Descuento | `γ = 0,999`: un resultado 60 pasos después pesa 0,94 (con 0,99 pesaría 0,55) | S9 |

El estado no es del todo markoviano: el precio llega con atraso y el agente no ve el libro de
órdenes. La antigüedad del precio y los cambios recientes resumen esa historia.

## Recompensa

La cartera se valora con lo que se recibiría al vender ya (`p - medio spread`, menos la comisión de
venta). Así, el costo de salir aparece en el momento de comprar y no recién al final (S9). Con esa
valoración, la recompensa densa `pnl` es la recompensa terminal más un *shaping* por potencial (Ng,
Harada y Russell, 1999): las dos buscan casi la misma política óptima y difieren en cuánto ayudan a
aprender.

Antes de elegir, se revisó cómo diseñan la recompensa otros entornos y la literatura
([investigación](../../../docs/ia/investigaciones/recompensas_rl_trading.md)). La elección salió de
una **ablación con PPO en val**, en dos etapas y con 5 semillas por variante (ENV-08,
[tabla completa](../../../reports/val/ablation.md)):

| Variante | Retorno por mercado sobre el stake | Mercados sin operar |
| --- | --- | --- |
| `pnl_risk` (base `pnl_mid`, `λ_dd = 1`) | **+0,0012** (IC 95 %: +0,0001 a +0,0023) | 89 % |
| `pnl_risk` (base `pnl_mid`, `λ_dd = 0,5`) | +0,0001 | 77 % |
| `utility` (`a = 1`) | −0,0307 | 11 % |
| `pnl_mid` | −0,0348 | 5 % |
| `pnl` | −0,0358 | 2 % |
| `pnl_hold` (base `pnl_mid`) | −0,0373 | 6 % |
| `terminal` | −0,0673 | 3 % |

- **Etapa A:** `pnl`, `pnl_mid` y `terminal`. La recompensa solo terminal fue la peor, como se
  esperaba de una señal que llega una vez cada 60 pasos. `pnl_mid` y `pnl` quedaron casi iguales.
- **Etapa B, sobre `pnl_mid`:** penalizar el aumento del drawdown, cobrar por mantener la posición
  y una utilidad cóncava (CARA). Ganó `pnl_risk` con `λ_dd = 1`, que es la recompensa de
  `configs/env.yaml`.

**Lectura crítica:** `pnl_risk` no gana porque opere mejor, sino porque opera mucho menos: no toca el
89 % de los mercados. Las variantes que operan en casi todos pierden alrededor de 3,5 % del stake
por mercado, del orden de lo que cuestan el spread y la comisión. La ablación ya anticipaba lo que
confirmó test: con estos costos, la mejor política aprendida se parece a no operar.

## Algoritmos

Se usan implementaciones probadas, para que el esfuerzo vaya al entorno y a la evaluación (ADR-001):
`stable-baselines3` para PPO y DQN, y `d3rlpy` para CQL y BC.

| Algoritmo | Tipo | Por qué |
| --- | --- | --- |
| **PPO** | *On-policy*, actor-crítico | Agente principal: estable con recompensas ruidosas y fácil de ajustar |
| **DQN** | *Off-policy*, basado en valor | Comparación natural con 4 acciones discretas: aprende `Q(s, a)` |
| **CQL** | Offline RL | Aprende de un dataset fijo de transiciones de los baselines, sin interactuar; penaliza las acciones que el dataset no respalda |
| **BC** | Imitación | Referencia para CQL: muestra si CQL aporta algo más que copiar a los baselines |

Entrenar PPO o DQN sobre datos históricos reproducidos sigue siendo RL *online*: el agente elige
qué experiencias ve. CQL y BC son los únicos que aprenden de datos fijos.

## Alternativas descartadas

| Alternativa | Por qué se descartó | Decisión |
| --- | --- | --- |
| Ejecutar al precio del mismo instante `t` | El precio llega hasta 60 s tarde respecto del spot; ejecutar en `t` regalaba ese retraso (correlación de 0,90 con el movimiento siguiente, frente a 0,22 alineando los tiempos) | ADR-011, S4 |
| Simular el libro de órdenes | Polymarket no publica su historia; se usa spread fijo y se validan las ejecuciones con trades reales en el modo estricto | ADR-003, EVA-11 |
| Elegir el tamaño de la orden | Multiplica el espacio de acción y DQN y CQL necesitan acciones discretas | ADR-005 |
| Recompensa solo terminal | Fue la peor de la ablación | ENV-08 |

## Cómo se sabe si funciona

- Los baselines pasan por **el mismo entorno**, con la misma observación, los mismos costos y la
  misma ejecución.
- El protocolo se fijó antes de ver resultados ([protocolo](../../../docs/notas/protocolo_eval.md)):
  la unidad es el mercado, se compara la diferencia pareada contra `NoTrade`, una mejora importa
  desde el 1 % del stake por mercado y test se evalúa una sola vez.
- Los resultados están en [06_resultados.md](06_resultados.md).
