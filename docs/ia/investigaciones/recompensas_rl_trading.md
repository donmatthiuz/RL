# Investigación: recompensa del entorno (ENV-05 y ENV-08)

Código revisado: [Gym-Trading-Env](https://github.com/ClementPerroud/Gym-Trading-env),
[FinRL](https://github.com/AI4Finance-Foundation/FinRL),
[TensorTrade](https://github.com/tensortrade-org/tensortrade),
[gym-anytrading](https://github.com/AminHP/gym-anytrading) y
[mbt_gym](https://github.com/JJJerome/mbt_gym).

## Por qué se investiga

`docs/02` propone `pnl_risk` como recompensa principal: el cambio del valor de la cartera menos
`λ_dd` por el aumento del drawdown. Con la valoración de S9 (ADR-016), al comprar el valor cae lo
que costaría salir, y esa caída también cuenta como drawdown: la entrada se paga `1 + λ_dd` veces,
justo lo que S9 quería evitar. El 31/10/2026 R1 pidió no decidir todavía: primero ver cómo diseñan
la recompensa otros entornos de RL para trading y la literatura, y después comparar las
alternativas con una ablación en las mismas condiciones de evaluación.

## Lo que ya sabemos

- **El entorno** (PR #11): un mercado por episodio, 60 pasos, una posición de 20 USDC a la vez, y
  liquidación a 1 o 0 en `w1`. La posición se valora a liquidación (S9).
- **`pnl`:** `r_t = (V_t+1 - V_t) / V_0`. La suma del episodio es el PnL final sobre `V_0`, así que
  los costos cuentan una vez. Lo verifica un test.
- **Lo que cuesta entrar:** al comprar con `p = 0,5`, la recompensa del paso es de unos −0,0021: el
  spread de ida y vuelta y las dos comisiones, cerca del 10 % del monto. Con `pnl_risk` y
  `λ_dd = 0,5`, se suma otro −0,0010.
- **La métrica de evaluación** (EVA-01) es el retorno medio por mercado sobre el monto, neutral al
  riesgo. La recompensa de entrenamiento puede ser otra, pero la conclusión se saca siempre con esa
  métrica.
- **`γ`** tiene que quedar cerca de 1 (S9).
- **Lo que esperamos:** los baselines pierden en train después de costos (PR #12). El riesgo R5,
  que el agente aprenda a no operar, es real.

## Revisión de código (31/10/2026)

Se leyó la función de recompensa de cada proyecto, en el commit indicado.

| Proyecto (commit) | Recompensa por defecto | Valoración de la posición | Riesgo |
| --- | --- | --- | --- |
| Gym-Trading-Env (`a86fc03`), `environments.py` | `log(V_t / V_t-1)` por paso; se puede reemplazar por cualquier función del historial | Precio actual del activo; la comisión se descuenta al operar | No está en la recompensa |
| FinRL (`7e98df4`), `env_stocktrading.py` | `(V_t - V_t-1) × reward_scaling` (por ejemplo, 1e-4) | Caja más acciones al precio de cierre | Fuera de la recompensa: con turbulencia alta se liquida todo |
| FinRL, `env_stocktrading_cashpenalty.py` | `((V_t - max(0; 0,1·V_t - caja)) / V_0 - 1) / t`: retorno acumulado medio, con penalización si falta caja | Igual | Penalización por liquidez |
| FinRL, `env_stocktrading_stoploss.py` | Lo anterior menos penalizaciones por stop-loss y ventas con poca ganancia, más un bono por ventas con ganancia | Igual | Penalizaciones hechas a mano |
| FinRL, `env_portfolio_optimization.py` | `log(V_t / V_t-1) × scaling` | Precio de cierre | No está en la recompensa |
| TensorTrade (`d58afba`), `rewards.py` | `SimpleProfit`: `V_t / V_t-w - 1` | Valor neto del portafolio | `RiskAdjustedReturns`: Sharpe o Sortino de los retornos de una ventana |
| TensorTrade, `PBR` y `AdvancedPBR` | `(p_t - p_t-1) · x_t` según la posición, sin costos; la variante suma una penalización por cambiar de posición y un bono por mantener | Solo el precio | No |
| gym-anytrading (`1498ea7`), `stocks_env.py` | Solo al cerrar un largo: el cambio de precio desde la entrada | Sin valoración intermedia | No |
| mbt_gym (`1e1aa38`), `RewardFunctions.py` | `PnL`: cambio del valor mark-to-market | Caja más inventario al precio | `RunningInventoryPenalty` (Cartea y Jaimungal: PnL menos `φ·q²·dt`) y `ExponentialUtility` (`-exp(-a·V_T)`, solo al final) |

Lo que sale de la comparación:

- **Ninguno castiga el drawdown en la recompensa de cada paso.** El riesgo aparece como un cociente
  (Sharpe o Sortino en una ventana), como una penalización por inventario, como una utilidad cóncava
  al final del episodio, o como una regla fuera de la recompensa. La penalización por drawdown de
  `docs/02` es diseño propio.
- **Todos valoran a precio de mercado, no a liquidación.** El costo que el agente ve al entrar es
  solo lo que paga al entrar. S9 adelanta además el costo de salir, que se devuelve si mantiene
  hasta la liquidación.
- **Casi todos suman el cambio de valor, o su logaritmo, en cada paso.** Sin descuento, la suma es
  el resultado final, igual que nuestro `pnl`.
- **La escala importa:** FinRL multiplica por 1e-4. Nuestras recompensas, sobre `V_0 = 1 000` con
  órdenes de 20 USDC, quedan del orden de 1e-3; sobre el monto quedarían del orden de 1.
- **Ninguno modela pagos binarios con horizonte fijo.** Lo más cercano es mbt_gym: horizonte fijo y
  penalización terminal del inventario.

## Variantes candidatas para la ablación (propuesta)

Se confirman o se ajustan con la respuesta de Perplexity. Todas usan la misma valoración de S9 para
`upnl`, el drawdown reportado y la evaluación; solo cambia la señal de entrenamiento.

| Variante | Recompensa | De dónde sale | Qué prueba |
| --- | --- | --- | --- |
| `pnl` (actual) | Cambio del valor a liquidación sobre `V_0` | S9; FinRL y mbt_gym con otra valoración | Línea base |
| `pnl_mid` | Cambio del valor con la posición a precio medio | Gym-Trading-Env, FinRL y mbt_gym | Si adelantar el costo de salida desanima la entrada. Suma lo mismo en el episodio |
| `pnl_risk` | `pnl` menos `λ_dd` por el aumento del drawdown | `docs/02` (propio) | La propuesta original, con la entrada castigada dos veces |
| `pnl_risk_post` | Igual, con el drawdown medido desde el valor después de entrar | Propio | Aversión al riesgo sin castigar la entrada |
| `pnl_hold` | `pnl` menos `φ` por cada paso con posición | mbt_gym (`RunningInventoryPenalty`) y `λ_hold` de `docs/02` | Si conviene castigar el tiempo expuesto |
| `utility` | Solo al final: `-exp(-a · PnL / monto)` | mbt_gym (`ExponentialUtility`) | Aversión al riesgo sin señal en la entrada |
| `terminal` | Solo al final: PnL sobre `V_0` | `docs/02`; gym-anytrading (solo al cerrar) | Recompensa escasa |

Además, la escala: sobre `V_0` (actual) o sobre el monto apostado.

Cómo se compara (ENV-08 y protocolo de EVA-01): PPO con la misma config, al menos 3 semillas por
variante y selección en val con la métrica principal (retorno sobre el monto), más las operaciones
por mercado para vigilar R5. Test no se usa para elegir la recompensa.

## Prompt para Perplexity

Copiar tal cual:

```text
Necesito literatura académica y referencias verificables sobre el diseño de la función de
recompensa en aprendizaje por refuerzo aplicado a trading. Prioriza papers con revisión por pares,
arXiv con autores identificables y repositorios oficiales de GitHub. Cita la URL o el DOI de cada
dato y marca como "no confirmado" lo que no tenga fuente.

Contexto: un agente (PPO, DQN y CQL) opera mercados binarios de 60 pasos que pagan 1 o 0 al final,
con una posición a la vez, costos de transacción (spread y comisión) y descuento gamma cercano a 1.
Hoy la recompensa es el cambio del valor de la cartera en cada paso, con la posición valorada a lo
que se recibiría al venderla ya, así que comprar da una recompensa negativa inmediata.

Responde cada punto por separado:

1. Funciones de recompensa usadas en RL para trading: PnL absoluto, retorno logarítmico, Sharpe
   diferencial (Moody y Saffell), Sortino, penalizaciones por drawdown, CVaR, utilidad CARA o CRRA y
   penalizaciones por inventario (Cartea y Jaimungal). Para cada una: fórmula, paper original con
   enlace y qué problema resuelve.
2. Estudios que comparen empíricamente varias recompensas en el mismo entorno (ablaciones): qué
   compararon, con cuántas semillas y qué concluyeron.
3. Reward shaping basado en potencial (Ng, Harada y Russell, 1999): ¿una recompensa densa de
   mark-to-market conserva la política óptima respecto de la recompensa terminal? ¿Qué cambia con
   gamma menor que 1?
4. Penalizaciones por drawdown en la recompensa: cómo se definen (incremento por paso o máximo del
   episodio) y si hay evidencia de que castiguen la entrada o lleven a no operar.
5. RL en apuestas o derivados con pago binario y horizonte fijo (opciones binarias, mercados de
   predicción, apuestas deportivas): papers o repositorios y qué recompensa usan.
6. Costos de transacción y el colapso a "no operar": cómo lo evitan los papers (escala de la
   recompensa, entropía, currículo de costos u otros).
7. Escala y normalización de la recompensa en PPO y DQN (por ejemplo, VecNormalize de
   stable-baselines3): práctica recomendada y su efecto.
8. Cómo se reporta una ablación de recompensas en papers de RL para trading: semillas, métricas y
   pruebas estadísticas.

Termina con una tabla: recompensa, fórmula, referencia y evidencia empírica a favor o en contra.
```

## Respuesta de Perplexity

Pendiente: pegar aquí la respuesta completa, con sus enlaces.

## Evaluación de la respuesta

Pendiente. Al pegar la respuesta se revisa:

- Que cada paper citado exista y diga lo que la respuesta le atribuye.
- Que las fórmulas coincidan con las del paper o del repositorio.
- Qué puntos quedaron sin fuente o como "no confirmado".

## Cómo se usa

- Define qué variantes se implementan en `reward.py` (ENV-05) y la lista final de la ablación
  (ENV-08).
- Hasta entonces, `configs/env.yaml` usa `pnl` como recompensa provisional.
- R1 decide la recompensa principal con el resultado de la ablación en val, y queda como ADR.
