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

Primera versión, del 31/10/2026. La reemplaza la lista revisada de la evaluación de la respuesta.
Todas usan la misma valoración de S9 para `upnl`, el drawdown reportado y la evaluación; solo cambia
la señal de entrenamiento.

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

```md
A continuación separo lo que está documentado por fuentes verificables de lo que no pude confirmar. Para tu entorno —60 pasos, pago binario terminal, una posición, costos y \(\gamma\approx1\)— la implicación central es: una recompensa de *mark-to-market* mal construida puede penalizar la entrada aunque la operación sea rentable al vencimiento; eso no es un problema de PPO/DQN/CQL en sí, sino de la señal de recompensa.

## 1. Funciones de recompensa en RL para trading

### PnL absoluto

\[
r_t = V_{t+1}-V_t
\]

donde \(V_t\) es el valor de la cartera, idealmente incluyendo cash, posición y costos ya incurridos. Es la recompensa “natural” para maximizar riqueza terminal.

- **Referencia verificable:** Spooner et al., *Market Making via Reinforcement Learning*, arXiv:1804.04216, usan PnL incremental como línea base: [https://arxiv.org/abs/1804.04216](https://arxiv.org/abs/1804.04216). [arxiv](https://arxiv.org/html/1804.04216)
- **Qué resuelve:** alinea directamente el agente con la ganancia neta.
- **Riesgo en tu caso:** si valoras la posición a su precio de venta inmediato, comprar paga spread + comisión en \(t\), pero el pago binario llega en el paso 60. Con \(\gamma\approx1\) el valor final debería dominar; si no lo hace, la recompensa está mal normalizada o el horizonte/costo domina la señal.

### Retorno logarítmico

\[
r_t=\log\left(\frac{V_{t+1}}{V_t}\right)
\]

- **Referencia verificable:** un trabajo reciente de RL para gestión de carteras usa exactamente \(R_t=\log(1+w_t^\top r_t)-\kappa TC_t-\lambda w_t^\top\Sigma_t w_t\): [https://arxiv.org/abs/2510.06466](https://arxiv.org/abs/2510.06466). [arxiv](https://arxiv.org/html/2510.06466v1)
- **Qué resuelve:** hace aditivos los crecimientos porcentuales, penaliza proporcionalmente las pérdidas y es más estable cuando la escala del capital cambia.
- **Advertencia:** para un pago binario de 1 o 0, el log-return puede explotar si el valor de cartera pasa por cero o cerca de cero; conviene acotarlo o usar PnL normalizado.

### Sharpe diferencial

Moody y Saffell proponen optimizar en línea una aproximación local del Sharpe. Con retorno \(R_t\), media móvil \(A_t\) y segundo momento móvil \(B_t\):

\[
D_t=\frac{B_t\Delta A_t-\frac{1}{2}A_t\Delta B_t}{(B_t-A_t^2)^{3/2}}
\]

donde \(\Delta A_t=A_t-A_{t-1}\) y \(\Delta B_t=B_t-B_{t-1}\).

- **Paper original:** J. Moody y M. Saffell, “Learning to trade via direct reinforcement”, *IEEE Transactions on Neural Networks* 12(4):875–889, 2001. DOI: [https://doi.org/10.1109/72.935097](https://doi.org/10.1109/72.935097). [dl.acm](https://dl.acm.org/doi/10.1109/72.935097)
- **Qué resuelve:** sustituye “maximizar beneficio” por “maximizar retorno ajustado por riesgo”, con una señal actualizable paso a paso.
- **Evidencia:** los autores reportan que optimizar el Sharpe diferencial produce resultados más consistentes que maximizar beneficio. [semanticscholar](https://www.semanticscholar.org/paper/Learning-to-trade-via-direct-reinforcement-Moody-Saffell/1a4999c918c6206cd9804c48f7dce1bac6ec5b4a)
- **En tu caso:** con 60 pasos y pago binario, la estimación de momentos en ventana corta será ruidosa; es más adecuada para evaluación que como única recompensa de entrenamiento.

### Sortino

\[
\text{Sortino}=\frac{\mathbb{E}[R-R_f]}{\sigma_{\text{downside}}}
\]

donde \(\sigma_{\text{downside}}\) usa solo desviaciones negativas respecto de un objetivo.

- **Estado de la evidencia:** se usa como métrica de evaluación en RL financiero; por ejemplo, el estudio de arXiv:2510.06466 reporta Sharpe y Sortino después de costos. [arxiv](https://arxiv.org/html/2510.06466v1)
- **Paper original del ratio Sortino:** **no confirmado** en esta búsqueda; no debo atribuirte una referencia sin URL/DOI verificada.
- **Qué resuelve:** castiga asimétricamente la volatilidad negativa, relevante si tu objetivo es evitar pérdidas más que variabilidad total.

### Penalización por drawdown

Formas comunes:

\[
r_t = \text{PnL}_t-\lambda \max(0, \text{Peak}_t-V_t)
\]

o, al final del episodio,

\[
R = \text{PnL}_T-\lambda \cdot \text{MaxDrawdown}
\]

- **Evidencia verificable:** la revisión *Reinforcement Learning Applied to Trading Systems: A Survey* documenta estudios que usan drawdown, Sterling y Calmar como objetivos o recompensas: [https://arxiv.org/abs/2212.06064](https://arxiv.org/abs/2212.06064). [arxiv](https://arxiv.org/html/2212.06064v1)
- **Qué resuelve:** penaliza rachas adversas y puede reducir exposición.
- **Riesgo:** una penalización fuerte por drawdown puede inducir “no operar”, especialmente si el drawdown se calcula intraepisodio con mark-to-market.

### CVaR

\[
\text{CVaR}_\alpha(R) = \mathbb{E}[R \mid R \le \text{VaR}_\alpha(R)]
\]

En recompensa suele aparecer como:

\[
r_t = \text{PnL}_t-\lambda\,\text{CVaR}_\alpha(\text{pérdidas})
\]

- **Evidencia verificable reciente:** *Risk-Aware Reinforcement Learning Reward for Financial Trading* propone una recompensa compuesta con retorno anualizado, riesgo a la baja, retorno diferencial y Treynor: [https://arxiv.org/abs/2506.04358](https://arxiv.org/abs/2506.04358). No es exactamente CVaR, pero ilustra la tendencia a combinar retorno y penalización de riesgo. [arxiv](https://arxiv.org/html/2506.04358v1)
- **Evidencia CVaR específica:** un trabajo de 2026 usa una penalización CVaR dentro de una recompensa para gestión de volatilidad y la abla con cinco semillas: [https://arxiv.org/abs/2610.13126](https://arxiv.org/abs/2610.13126). [arxiv](https://arxiv.org/html/2610.13126)
- **Qué resuelve:** concentra la penalización en la cola de pérdidas, no en la volatilidad simétrica.

### Utilidad CARA o CRRA

- CARA exponencial: \(U(W)=-e^{-\eta W}\).
- CRRA: \(U(W)=\frac{W^{1-\rho}}{1-\rho}\), con \(\rho\neq1\); y \(U(W)=\log W\) cuando \(\rho=1\).

- **Estado:** son estándar en economía financiera y teoría de portafolios, pero **no confirmé** un paper de RL para trading que las use como recompensa principal con URL/DOI verificable en esta búsqueda. Márcalas como **no confirmado** para tu bibliografía.
- **Qué resuelven:** incorporan aversión al riesgo; CARA es aproximación local para riqueza casi constante, CRRA para aversión relativa al nivel de riqueza.

### Penalización por inventario

\[
r_t=\text{PnL}_t-\lambda q_t^2
\]

o una versión de control estocástico con penalización lineal/cuadrática del inventario \(q_t\).

- **Referencia verificable:** Spooner et al. comparan PnL puro contra PnL “dampened” con término de inventario, citando la línea de Cartea y Jaimungal: [https://arxiv.org/abs/1804.04216](https://arxiv.org/abs/1804.04216). [arxiv](https://arxiv.org/html/1804.04216)
- **Paper original de Cartea y Jaimungal:** **no confirmado** aquí con URL/DOI; no lo cites como verificado sin revisarlo directamente.
- **Qué resuelve:** desincentiva acumular exposición y favorece estrategias tipo market-making o rotación rápida.

## 2. Ablaciones empíricas de recompensas

La evidencia comparativa existe, pero suele ser limitada y dependiente del entorno.

| Estudio | Qué comparó | Semillas / robustez | Conclusión |
|---|---|---|---|
| Spooner et al., arXiv:1804.04216 | PnL puro, PnL simétricamente amortiguado y PnL asimétricamente amortiguado para market making | El paper reporta resultados sobre una canasta de valores; **no confirmé** un número único de semillas | El PnL puro no fue el mejor fuera de muestra; el amortiguamiento asimétrico del término especulativo mejoró estabilidad y desempeño ajustado por riesgo en la mayoría de casos.  [arxiv](https://arxiv.org/html/1804.04216) |
| Revisión arXiv:2212.06064 | Compila estudios que comparan retorno absoluto, Sharpe/differential Sharpe, drawdown, Sterling, Calmar, win rate, etc. | Depende de cada estudio revisado | No hay un ganador universal: unos encuentran ventaja del Sharpe diferencial, otros del drawdown o Calmar; los costos cambian el ranking.  [arxiv](https://arxiv.org/html/2212.06064v1) |
| arXiv:2610.13126 | Recompensa completa frente a eliminación de CVaR, eliminación de componente VRP y recompensa directa con PnL neto | Cinco semillas: {1, 3, 5, 7, 11} | Las cuatro especificaciones tuvieron desempeño similar; los términos de shaping afectaron principalmente el trade-off retorno-drawdown, no crearon por sí solos la ventaja principal.  [arxiv](https://arxiv.org/html/2610.13126) |
| arXiv:2510.06466 | RL con recompensa log-return menos costos y penalización de varianza frente a buy-and-hold y baselines RL | Reporta semilla 42; **no es una ablación multi-semilla de recompensas** | La recompensa compuesta produjo mejores métricas ajustadas por riesgo que los baselines, pero la evidencia sobre la elección de recompensa es limitada.  [arxiv](https://arxiv.org/html/2510.06466v1) |

**Lectura práctica:** para tu problema, una ablación mínima creíble sería comparar: (i) PnL terminal neto, (ii) PnL incremental neto, (iii) PnL incremental + potencial de mark-to-market, y (iv) PnL terminal + penalización de drawdown/CVaR, con al menos 10 semillas.

## 3. Reward shaping basado en potencial

Ng, Harada y Russell demostraron que añadir

\[
F(s,a,s')=\gamma\Phi(s')-\Phi(s)
\]

a la recompensa original preserva el conjunto de políticas óptimas del MDP, para cualquier función de potencial \(\Phi\). [dl.acm](https://dl.acm.org/doi/10.5555/645528.657613)

- **Paper:** A. Y. Ng, D. Harada y S. J. Russell, “Policy Invariance Under Reward Transformations: Theory and Application to Reward Shaping”, ICML 1999, pp. 278–287. DOI/registro ACM: [https://dl.acm.org/doi/10.5555/645528.657613](https://dl.acm.org/doi/10.5555/645528.657613). [dl.acm](https://dl.acm.org/doi/10.5555/645528.657613)
- **También disponible en:** [https://mlanthology.org/icml/1999/ng1999icml-policy/](https://mlanthology.org/icml/1999/ng1999icml-policy/). [mlanthology](https://mlanthology.org/icml/1999/ng1999icml-policy/)

### ¿Conserva la política óptima el mark-to-market?

**No automáticamente.** Una recompensa densa de mark-to-market solo es *policy-invariant* si tiene la forma telescópica anterior. Por ejemplo, si \(\Phi(s)=V_t^{\text{MTM}}\), entonces:

\[
F_t=\gamma V_{t+1}^{\text{MTM}}-V_t^{\text{MTM}}
\]

es segura. En cambio, \(r_t=V_{t+1}^{\text{MTM}}-V_t^{\text{MTM}}\) sin el factor \(\gamma\) **no** es exactamente potencial-based cuando \(\gamma<1\).

Con \(\gamma=1\), la suma de \(V_{t+1}-V_t\) telescópica y equivale, salvo constantes, al cambio total de valor; por eso puede ser inofensiva si el MTM está bien definido y no introduce costos fantasma.

Con \(\gamma<1\), la forma correcta es:

\[
r_t^{\text{shaped}}=r_t^{\text{original}}+\gamma\Phi(s_{t+1})-\Phi(s_t)
\]

Si usas \(F_t=\Phi(s_{t+1})-\Phi(s_t)\) con \(\gamma<1\), ya no está garantizada la invarianza. [people.cs.umass](https://people.cs.umass.edu/~pthomas/courses/CMPSCI_687_Fall2018/Barto12_4_2018.pdf)

**Para tu caso:** si tu recompensa actual es “cambio del valor de cartera valorando la posición a precio de venta inmediato”, no es un shaping potencial-based puro: incluye el costo de salida inmediato en cada paso. Eso puede hacer que comprar tenga recompensa negativa aunque la posición termine pagando 1. Una alternativa más limpia es recompensa terminal por PnL neto, más un shaping potencial basado en el valor esperado de la posición, no en su liquidación forzada.

## 4. Penalizaciones por drawdown

Hay dos diseños distintos:

1. **Incremental:**
   \[
   r_t=\text{PnL}_t-\lambda\max(0,\text{Peak}_t-V_t)
   \]
   Penaliza cada paso bajo el máximo histórico.

2. **Terminal / máximo del episodio:**
   \[
   R=\text{PnL}_T-\lambda\,\text{MaxDrawdown}_{0:T}
   \]
   Penaliza una sola vez al cierre.

- **Evidencia de uso:** la revisión arXiv:2212.06064 reporta trabajos que emplean drawdown como recompensa u objetivo, incluido un caso donde la mejor recompensa fue Max Drawdown. [arxiv](https://arxiv.org/html/2212.06064v1)
- **Evidencia de que castiguen la entrada o lleven a no operar:** **no confirmé** un estudio controlado que demuestre causalmente ese efecto para trading. Es un mecanismo plausible: si el drawdown se mide con MTM intraepisodio, entrar temprano crea drawdown contable antes del pago binario. Márcalo como hipótesis, no como resultado establecido.
- **Recomendación:** si usas drawdown, hazlo terminal o con coeficiente pequeño; nunca combines drawdown MTM agresivo con costos de entrada inmediatos.

## 5. RL en pagos binarios y horizonte fijo

### Mercados de predicción

- Turtel, Franklin y Skotheim, *Outcome-based Reinforcement Learning to Predict the Future*, arXiv:2505.17989: modelan predicción binaria con resultado \(y\in\{0,1\}\) y recompensa de episodio:
  \[
  R=-(\hat p-y)^2
  \]
  [https://arxiv.org/abs/2505.17989](https://arxiv.org/abs/2505.17989). [arxiv](https://arxiv.org/html/2505.17989v1)
- Levy, *Reinforcement Learning for LLM-based Event Forecasting*, arXiv:2606.15917, usa GRPO con recompensa de entropía cruzada negativa sobre preguntas binarias de Polymarket: [https://arxiv.org/abs/2606.15917](https://arxiv.org/abs/2606.15917). [arxiv](https://arxiv.org/html/2606.15917)

### Opciones y derivados

- *Applying Reinforcement Learning to Option Pricing and Hedging*, arXiv:2310.04336, revisa RL para pricing y hedging, incluido el enfoque Q-Learning Black-Scholes: [https://arxiv.org/abs/2310.04336](https://arxiv.org/abs/2310.04336). [arxiv](https://arxiv.org/html/2310.04336v1)
- **No confirmé** en esta búsqueda un paper revisado por pares específicamente sobre RL para **opciones binarias** con horizonte fijo de 60 pasos y repositorio oficial. Ese nicho parece poco cubierto; trata cualquier referencia adicional como no confirmada hasta verificar DOI, autores y código.

**Implicación:** en mercados de predicción, la recompensa suele ser una regla de scoring propia —Brier o cross-entropy—, no el PnL bruto. Para tu agente, el análogo natural es PnL neto terminal: \(1-\text{precio pagado}-\text{costos}\) si acierta, y \(-\text{precio pagado}-\text{costos}\) si falla.

## 6. Costos de transacción y colapso a “no operar”

Los papers evitan el colapso principalmente haciendo que la recompensa refleje el beneficio neto esperado, no el costo contable inmediato.

- En arXiv:2511.00190, la recompensa incluye ganancia por cambio de precio menos costo proporcional:
  \[
  R_t=I_{t+1}(S_{t+1}-S_t)-\lambda|q_t|
  \]
  Los autores muestran que existe una región donde el movimiento esperado no compensa el costo y, por tanto, no operar es óptimo: [https://arxiv.org/abs/2511.00190](https://arxiv.org/abs/2511.00190). [arxiv](https://arxiv.org/html/2511.00190)
- En market making, Spooner et al. modifican el término de inventario/especulación de la recompensa para que capturar spread pese más que especular; el amortiguamiento asimétrico mejoró estabilidad y desempeño: [https://arxiv.org/abs/1804.04216](https://arxiv.org/abs/1804.04216). [arxiv](https://arxiv.org/html/1804.04216)
- En arXiv:2510.06466, los costos se incluyen directamente en la recompensa como \(-\kappa TC_t\), junto con retorno logarítmico y penalización de varianza. [arxiv](https://arxiv.org/html/2510.06466v1)

### Métodos documentados o razonables

- **PnL neto terminal:** evita castigar la entrada si el trade es rentable al vencimiento.
- **Shaping potencial correcto:** usa \(\gamma\Phi(s')-\Phi(s)\), no un MTM de liquidación inmediata.
- **Entropía:** PPO tiene un coeficiente explícito `ent_coef`; la documentación de Stable-Baselines3 lo define como coeficiente de entropía en la función de pérdida. [https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html). [stable-baselines3.readthedocs](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html)
- **Currículo de costos:** **no confirmé** un paper de trading que lo use como mecanismo principal; es una práctica plausible pero no la presentes como evidenciada.
- **Escala de recompensa:** la normalización puede evitar que un costo grande domine el gradiente, pero no debe alterar el ranking económico de las acciones.

## 7. Escala y normalización en PPO y DQN

`VecNormalize` de Stable-Baselines3 normaliza observaciones y recompensas con estadísticas móviles:

\[
\tilde r_t=\operatorname{clip}\left(\frac{r_t}{\sqrt{\operatorname{Var}(R_t)+\epsilon}},-c,c\right)
\]

- Usa `gamma` para las estadísticas de retorno y permite `norm_reward`, `clip_reward`, `clip_obs` y `epsilon`. Fuente oficial: [https://stable-baselines3.readthedocs.io/en/master/_modules/stable_baselines3/common/vec_env/vec_normalize.html](https://stable-baselines3.readthedocs.io/en/master/_modules/stable_baselines3/common/vec_env/vec_normalize.html). [stable-baselines3.readthedocs](https://stable-baselines3.readthedocs.io/en/master/_modules/stable_baselines3/common/vec_env/vec_normalize.html)
- La documentación de ejemplos recomienda el wrapper para normalizar observaciones y recompensas: [https://stable-baselines3.readthedocs.io/en/master/guide/examples.html](https://stable-baselines3.readthedocs.io/en/master/guide/examples.html). [stable-baselines3.readthedocs](https://stable-baselines3.readthedocs.io/en/master/guide/examples.html)
- En PPO, la documentación advierte que el clipping depende de la escala de la recompensa: [https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html). [stable-baselines3.readthedocs](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html)

**Práctica recomendada para tu caso:**

- Normaliza **observaciones**; casi siempre ayuda.
- Normaliza la recompensa con cautela: puede estabilizar PPO, pero también distorsiona la comparación entre “no operar” y “operar” si los costos y pagos tienen escalas muy distintas.
- Para DQN, considera escalar la recompensa a un rango acotado, por ejemplo PnL neto dividido por la ganancia máxima posible, en lugar de normalización adaptativa.
- Guarda las estadísticas del wrapper y úsalas de forma consistente en evaluación.

## 8. Cómo reportar una ablación de recompensas

Un reporte defendible incluiría:

- **Semillas:** mínimo 5; idealmente 10 o más. El trabajo arXiv:2610.13126 reporta una ablación con cinco semillas comunes {1, 3, 5, 7, 11}. [arxiv](https://arxiv.org/html/2610.13126)
- **Métricas fuera de muestra:** PnL neto, Sharpe/Sortino después de costos, máximo drawdown, tasa de operaciones, turnover, proporción de episodios sin operar y distribución de retornos. Estos criterios aparecen en trabajos recientes de RL financiero. [arxiv](https://arxiv.org/html/2510.06466v1)
- **Separación train/validation/test:** walk-forward o purged walk-forward para evitar fuga temporal; arXiv:2510.06466 describe ese enfoque. [arxiv](https://arxiv.org/html/2510.06466v1)
- **Estadística:** media \(\pm\) desviación estándar, intervalos de confianza y una prueba de comparación entre configuraciones; el trabajo de forecasting RL reporta valores p e intervalos para comparar beneficios hipotéticos. [arxiv](https://arxiv.org/html/2505.17989v1)
- **Transparencia:** publicar fórmula exacta de recompensa, coeficientes, esquema de costos, número de semillas y código o semillas reproducibles.

## Tabla final

| Recompensa | Fórmula | Referencia | Evidencia empírica |
|---|---|---|---|
| PnL absoluto | \(r_t=V_{t+1}-V_t\) | Spooner et al., arXiv:1804.04216, [https://arxiv.org/abs/1804.04216](https://arxiv.org/abs/1804.04216)  [arxiv](https://arxiv.org/html/1804.04216) | Útil como base, pero no fue la mejor en market making; el PnL puro puede favorecer especulación e inestabilidad.  [arxiv](https://arxiv.org/html/1804.04216) |
| Retorno logarítmico | \(r_t=\log(V_{t+1}/V_t)\) | arXiv:2510.06466, [https://arxiv.org/abs/2510.06466](https://arxiv.org/abs/2510.06466)  [arxiv](https://arxiv.org/html/2510.06466v1) | Usada con costos y penalización de varianza; reporta mejores Sharpe/Sortino que buy-and-hold, con evidencia limitada a una semilla reportada.  [arxiv](https://arxiv.org/html/2510.06466v1) |
| Sharpe diferencial | \(D_t=\frac{B_t\Delta A_t-\frac12 A_t\Delta B_t}{(B_t-A_t^2)^{3/2}}\) | Moody y Saffell, DOI: [https://doi.org/10.1109/72.935097](https://doi.org/10.1109/72.935097)  [dl.acm](https://dl.acm.org/doi/10.1109/72.935097) | Los autores reportan resultados más consistentes que maximizar PnL; la revisión arXiv:2212.06064 también documenta su uso.  [semanticscholar](https://www.semanticscholar.org/paper/Learning-to-trade-via-direct-reinforcement-Moody-Saffell/1a4999c918c6206cd9804c48f7dce1bac6ec5b4a) |
| Sortino | \(\mathbb{E}[R-R_f]/\sigma_{\text{downside}}\) | **Paper original: no confirmado**; uso como métrica en arXiv:2510.06466  [arxiv](https://arxiv.org/html/2510.06466v1) | Métrica de evaluación frecuente; evidencia como recompensa de entrenamiento: no confirmada. |
| Drawdown | \(r_t=\text{PnL}_t-\lambda\max(0,\text{Peak}_t-V_t)\) o terminal | Revisión arXiv:2212.06064, [https://arxiv.org/abs/2212.06064](https://arxiv.org/abs/2212.06064)  [arxiv](https://arxiv.org/html/2212.06064v1) | Hay estudios que la usan y algunos la favorecen; evidencia de que cause “no operar”: no confirmada.  [arxiv](https://arxiv.org/html/2212.06064v1) |
| CVaR | \(r_t=\text{PnL}_t-\lambda\,\text{CVaR}_\alpha\) | Uso documentado en arXiv:2610.13126, [https://arxiv.org/abs/2610.13126](https://arxiv.org/abs/2610.13126)  [arxiv](https://arxiv.org/html/2610.13126) | En una ablación de 5 semillas, quitar CVaR mejoró levemente retorno/Sharpe pero empeoró drawdown medio.  [arxiv](https://arxiv.org/html/2610.13126) |
| CARA / CRRA | \(U(W)=-e^{-\eta W}\) o \(W^{1-\rho}/(1-\rho)\) | **No confirmado** para RL en trading con URL/DOI verificable | Sin evidencia empírica confirmada aquí. |
| Penalización por inventario | \(r_t=\text{PnL}_t-\lambda q_t^2\) | Spooner et al., arXiv:1804.04216, [https://arxiv.org/abs/1804.04216](https://arxiv.org/abs/1804.04216)  [arxiv](https://arxiv.org/html/1804.04216) | El amortiguamiento del término de inventario mejoró estabilidad y desempeño ajustado por riesgo; Cartea y Jaimungal: no confirmado aquí.  [arxiv](https://arxiv.org/html/1804.04216) |
| Shaping potencial | \(F=\gamma\Phi(s')-\Phi(s)\) | Ng, Harada y Russell, [https://dl.acm.org/doi/10.5555/645528.657613](https://dl.acm.org/doi/10.5555/645528.657613)  [dl.acm](https://dl.acm.org/doi/10.5555/645528.657613) | Garantía teórica de preservar políticas óptimas; no es evidencia empírica de mejor desempeño financiero.  [dl.acm](https://dl.acm.org/doi/10.5555/645528.657613) |
| Brier negativo | \(R=-(\hat p-y)^2\) | arXiv:2505.17989, [https://arxiv.org/abs/2505.17989](https://arxiv.org/abs/2505.17989)  [arxiv](https://arxiv.org/html/2505.17989v1) | Mejora calibración y beneficio hipotético frente a un baseline en mercados de predicción binarios.  [arxiv](https://arxiv.org/html/2505.17989v1) |

**Recomendación concreta para tu agente:** usa como recompensa primaria el **PnL neto terminal** —pago binario menos precio de entrada, spread y comisión—, y añade solo shaping potencial formal si necesitas señal densa:

\[
r_t=\mathbf{1}\{t=T\}\,\text{PnL}_T+\gamma\Phi(s_{t+1})-\Phi(s_t)
\]

Evita valorar la posición a “lo que recibirías al venderla ya” dentro de la recompensa periódica: eso convierte el costo de salida en un castigo recurrente por entrar, aunque la operación sea correcta al vencimiento.
```

## Evaluación de la respuesta

Evaluada el 01/11/2026 (R1). **Resultado: satisfactorio con reservas.** Las fuentes existen y casi
todo lo que se les atribuye está en ellas, pero el diagnóstico de nuestra recompensa es incorrecto
(ver "Revisión técnica"). Se resume en el [historial de prompts](../historial_prompts.md) (P13).

### Verificación de las fuentes

Se leyó el resumen y el PDF de cada artículo de arXiv, y el DOI de Moody y Saffell se comprobó en
Crossref.

| Fuente | Qué le atribuye la respuesta | Qué se encontró |
| --- | --- | --- |
| Spooner, Fearnley, Savani y Koukorinis (2018), arXiv:1804.04216 | Compara PnL puro, amortiguado simétrico y asimétrico; el asimétrico rinde mejor | Correcto (sección 5.3). La amortiguación asimétrica se aplica al término de inventario y mejora "en la mayoría de los casos", no en todos |
| Felizardo, Paiva, Costa y Del-Moral-Hernandez (2022), arXiv:2212.06064 | Revisión sin una recompensa ganadora | Correcto: en un estudio gana el drawdown máximo y en otro Calmar. Lo que la revisión llama "Sharpe diferencial" es la fórmula del Sharpe común |
| Xue y Ye (2025), arXiv:2510.06466 | `log(1 + w·r) - κ·TC - λ·w'Σw`, con una sola semilla | Correcto: la fórmula es idéntica (sección 4.4), con semilla 42 y walk-forward |
| Srivastava, Aryan y Singh (2025), arXiv:2506.04358 | Recompensa compuesta: retorno anualizado, riesgo a la baja, retorno diferencial y Treynor | Correcto |
| Wang, Ślepaczuk y Sakowski (2026), arXiv:2610.13126 | Ablación con 5 semillas; las cuatro recompensas rinden parecido | Correcto (sección 6.5). Sin CVaR, el retorno y el Sharpe suben un poco y el drawdown máximo medio pasa de 4,00 % a 4,16 %. El problema es cuándo cerrar *short straddles* sobre el SPX |
| Macrì, Jaimungal y Lillo (2025), arXiv:2511.00190 | `I·ΔS - λ·|q|` y una región donde no operar es óptimo | Parcial: la ecuación 14 es `I·ΔS - λ·q`, y las bandas sin operar son lo que aprenden las políticas (figura 6), no un resultado demostrado |
| Turtel, Franklin y Skotheim (2025), arXiv:2505.17989 | Brier negativo como recompensa en predicción binaria | Correcto, pero son cinco autores: faltan Hewitt y Schoenegger |
| Levy (2026), arXiv:2606.15917 | GRPO con entropía cruzada negativa sobre preguntas de Polymarket | Parcial: es una tesis de maestría que también usa error cuadrático negativo y una recompensa de formato; en parte de los experimentos la referencia es el precio del mercado, no el resultado |
| Moody y Saffell (2001), DOI 10.1109/72.935097 | Fórmula del Sharpe diferencial | El DOI es correcto, pero no se pudo abrir el texto. En la versión conocida la fórmula usa `A_t-1` y `B_t-1`, no `A_t` y `B_t` (no confirmado) |
| Ng, Harada y Russell (1999), ICML | `γ·Φ(s') - Φ(s)` conserva las políticas óptimas | ACM no dejó abrir el enlace. Es el resultado conocido del artículo; falta confirmar el título completo y las páginas para la bibliografía |

Ninguna cita es inventada. Lo que la respuesta marcó como "no confirmado" no se usa como evidencia:

- el artículo original de Sortino;
- CARA y CRRA como recompensa de RL para trading;
- el artículo de Cartea y Jaimungal;
- el currículo de costos;
- que el drawdown lleve a no operar.

### Revisión técnica

- **Error de diagnóstico.** Según la respuesta, valorar a liquidación vuelve el costo de salida "un
  castigo recurrente por entrar". En nuestro `pnl` no se repite: la recompensa es el cambio del
  valor, así que el costo de salida resta una vez al entrar y vuelve al liquidar a 1 o 0. Lo
  comprueba el test de ENV-05, donde la suma del episodio es el PnL final. Solo se repetiría si la
  recompensa fuera el nivel del valor y no su cambio. El doble castigo real es el de `pnl_risk`, y
  ya estaba identificado.
- **Lo más útil: `pnl` ya es un shaping por potencial (punto 3).**
  - **El potencial:** `Φ(s) = (V - V_0) / V_0`, que vale 0 al terminar. Con esa `Φ`, la recompensa
    terminal `(V_T - V_0) / V_0` más el shaping exacto de Ng et al. da
    `(γ·(V_t+1 - V_0) - (V_t - V_0)) / V_0`.
  - **La diferencia con `pnl`:** `(1 - γ)·(V_t+1 - V_0) / V_0` por paso. Con `γ = 0,999` es muy
    chica: mantener 60 pasos una posición comprada a 0,5 suma unos −0,00013, el 6 % del costo de
    entrada. Con `γ = 1` la equivalencia es exacta, y se puede usar porque el horizonte es fijo.
  - **Qué significa para la ablación:** `terminal`, `pnl` y `pnl_mid` tienen, salvo ese término,
    la misma política óptima. Compararlas mide cuánto ayuda la señal densa a aprender, no cuál
    política es mejor.
- **La recomendación final** (PnL terminal más shaping con el valor esperado de la posición) es en
  la práctica `pnl_mid`, porque el precio medio es la estimación del mercado de ese valor. Una
  extensión posible es usar como potencial el valor de la posición a `p_fair`, la estimación de
  nuestro modelo.
- **Riesgo.** La evidencia verificada (Spooner et al. y Wang et al.) indica que los términos de
  riesgo cambian el balance entre retorno y drawdown, pero rara vez crean la ventaja. La métrica
  principal de EVA-01 es neutral al riesgo, así que una variante con riesgo solo puede ganar si
  regulariza el aprendizaje. Por eso se prueban pocas.
- **Descartadas como recompensa de entrenamiento:**
  - **Retorno logarítmico:** con órdenes del 2 % de `V_0` es casi igual a `pnl`.
  - **Sharpe diferencial y Sortino:** con 60 pasos y una sola posición, los momentos son muy
    ruidosos (lo reconoce la misma respuesta). Quedan como métricas.
  - **CVaR:** es una propiedad de la distribución entre episodios, no de un episodio con una sola
    apuesta.
  - **Brier:** sirve para predecir probabilidades, y nuestro agente no emite una probabilidad.
- **Escala:** coincide con la revisión de repositorios. Para DQN, la respuesta recomienda una
  escala fija (por ejemplo, sobre el monto) antes que normalizar la recompensa con `VecNormalize`.
  Las observaciones ya se normalizan con el z-score de train (DAT-07).

### Lista revisada para ENV-05 y ENV-08

R1 la aprobó el 01/11/2026 y está implementada en el PR #23. Reemplaza la tabla de variantes
candidatas. Se compara en dos etapas para no multiplicar las corridas:

| Etapa | Variante | Recompensa | Qué prueba |
| --- | --- | --- | --- |
| A | `terminal` | Solo al final: PnL sobre `V_0` | Línea base, sin shaping |
| A | `pnl` (actual) | Cambio del valor a liquidación (S9) sobre `V_0` | Si la señal densa ayuda a aprender |
| A | `pnl_mid` | Cambio del valor con la posición a precio medio, sobre `V_0` | Si adelantar el costo de salida desanima la entrada |
| B | `pnl_risk` | La ganadora de A menos `λ_dd` por el aumento del drawdown, con 2 valores de `λ_dd` | La propuesta original de `docs/02` |
| B | `pnl_hold` | La ganadora de A menos `φ` por cada paso con posición | Penalización por inventario (Spooner et al.; mbt_gym) |
| B | `utility` | Solo al final: `-exp(-a · PnL / monto)` | Aversión al riesgo sin señal en la entrada (mbt_gym) |

- **Fuera de la lista:** `pnl_risk_post`, porque ninguna referencia castiga el drawdown en cada
  paso, y las recompensas descartadas arriba.
- **Escala** (sobre `V_0` o sobre el monto): se prueba solo con la ganadora.
- **Semillas:** 5 por variante, como en EVA-01 y en Wang et al., en lugar de las 3 que pide la tabla
  de ENV-08. Si el tiempo de PPO en train no alcanza, se usan 3 y se dice en el reporte. Son 15
  corridas en A y 20 en B.
- **Igual para todas:** `γ`, la config de PPO, la valoración de S9 para `upnl` y para el drawdown
  reportado, y la selección en val con la métrica principal. También se reportan las operaciones
  por mercado, el porcentaje de mercados sin operar (riesgo R5) y el drawdown máximo.

## Cómo se usa

- La lista revisada define las variantes de `reward.py` (ENV-05, PR #23) y la ablación de ENV-08,
  que espera a que se abra val.
- Hasta entonces, `configs/env.yaml` usa `pnl` como recompensa provisional.
- R1 decide la recompensa principal con el resultado de la ablación en val, y queda como ADR.
