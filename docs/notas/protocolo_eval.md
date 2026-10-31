# Protocolo de evaluación (EVA-01)

Documentación oficial de las herramientas: [scipy.stats.bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
y [arch, bootstrap estacionario y largo de bloque](https://arch.readthedocs.io/en/latest/bootstrap/timeseries-bootstraps.html).

Cómo se va a decidir si los agentes funcionan, escrito **antes** de ver cualquier resultado para
no ajustar el análisis a lo que salga (*p-hacking*). Se aprueba en su PR y se congela al
mezclarlo: cambiarlo después exige un ADR que diga qué cambió y por qué.

- **Estado:** borrador para aprobar (31/10/2026). Las decisiones del equipo están en la sección 10.
- **Revisión:** el agente `academic-statistician` revisó el primer borrador. Sus hallazgos y lo
  que se cambió están en la sección 11.
- **Base:** la pregunta del proyecto (D1), el compromiso de reportar aunque nada gane (D4), el
  tamaño de los datos (D3), los splits (DAT-06 y S11) y el simulador ([09](../09_sistema_simulacion.md)).

## 1. Qué pregunta responde

¿Algún agente de RL (PPO, DQN, CQL o BC) **supera al mejor baseline con los mismos costos**? Es la
opción B de D1: el retorno absoluto puede ser negativo, y aprender a no operar es un resultado
válido si está bien medido. Si ningún agente gana, se reporta igual (D4).

## 2. Datos y splits

| Split | Mercados | Para qué se usa |
| --- | --- | --- |
| train | 8 683 | Entrenar, ajustar normalizaciones y generar el dataset offline |
| val | 1 860 | Elegir hiperparámetros, checkpoints y baselines, y estimar la potencia |
| test | 1 752 (unos 73 días) | Una sola evaluación final (EVA-06), con todo congelado |

- Los mercados de los análisis previos ya están fuera de test (S11). Las reglas que descartan
  mercados (datos faltantes o resultado distinto del de Binance) son las de DAT-05, iguales para
  todos los agentes y fijadas antes de abrir test.
- **Antes de abrir test:**
  - Se congela todo: commit, configs resueltas, hash del dataset y semillas. Se registran en
    `reports/test/`.
  - El análisis completo se corre sobre val con ese mismo código.
- Ninguna decisión usa test. Si alguien lo mira antes de tiempo, se declara en el informe.
- **Si aparece un bug después de abrir test:** se corrige, se vuelve a correr y se reportan las dos
  corridas.

## 3. Unidad de análisis y métrica principal

- **Unidad:** el mercado (un episodio). El saldo se reinicia en cada mercado.
- **Métrica principal:** retorno por mercado sobre el monto apostado, `R_i = PnL_i / stake`.
  - `stake` es fijo (`stake_fraction × initial_cash`, en `docs/02`), no el monto que se operó.
  - El PnL incluye spread, comisión y liquidación.
  - Un mercado en el que no se opera tiene `R_i = 0`.
- **Comparación principal:** la diferencia pareada por mercado
  `D_i = R_i(agente) - R_i(mejor baseline)`. Es pareada porque ambos juegan los mismos mercados.
- **Condiciones:** las de la configuración principal del simulador (S3 a S10). Las variantes van a
  la sección 8 y no cambian la conclusión.

## 4. Baselines

- Los de [02_arquitectura.md](../02_arquitectura.md) (sección 2.5): `Random`, `NoTrade`,
  `Favorite`, `Momentum` y `MeanReversion`, más `FairValue`, que usa el `edge` medido en el
  instante del precio (S3b).
- Pasan por el mismo entorno que los agentes: misma observación, mismos costos y misma ejecución.
- Sus parámetros (umbrales) se ajustan en val con una búsqueda pequeña y fija, igual que los
  hiperparámetros de los agentes.
- **Mejor baseline:** es `NoTrade`, salvo que una heurística le gane en val con el IC 95 % de la
  sección 6 por encima de cero. En un empate gana `NoTrade`. Se fija antes de abrir test. Si queda
  `NoTrade`, la comparación principal y la secundaria (sección 6) son la misma, y el informe lo
  dice.
- En test se reportan todos los baselines, como descriptivos.

## 5. Semillas y selección de modelos

- Cada configuración final se entrena con **5 semillas**.
- Cada semilla guarda un conjunto fijo de 10 checkpoints a intervalos iguales, igual para todos los
  algoritmos. Se elige el de mayor retorno medio en val.
- Se registra cuántas configuraciones se probaron para cada agente y cada baseline, y cuánto baja
  el resultado de val a test.
- En test, cada mercado se juega una vez por semilla, en el mismo orden para todos (S7).
- `Random` también se corre con 5 semillas.

## 6. Prueba estadística

**Intervalo de confianza (bootstrap de dos niveles):**

- Se remuestrean los días de test con un **bootstrap estacionario**: bloques de días consecutivos
  de largo aleatorio, porque la volatilidad de BTC dura días y los días no son independientes. El
  largo medio de bloque se fija antes de abrir test con el método de Politis y White, usando las
  medias diarias de `D` en val.
- En cada réplica también se remuestrean, con reemplazo, las 5 semillas del agente. Así el
  intervalo habla del algoritmo y no de estas 5 redes.
- 10 000 réplicas, intervalo BCa. La media es la suma de `D_i` dividida por el número de mercados,
  por si hay días incompletos.
- Agente y baseline usan los mismos índices remuestreados.

**Comparaciones múltiples:**

- La familia son las 4 comparaciones principales: PPO, DQN, CQL y BC contra el mejor baseline.
  MaskablePPO, ETH y las sensibilidades son exploratorias.
- Se corrige con Bonferroni: IC bilateral al 98,75 %, que equivale a una prueba unilateral con
  `α = 0,025 / 4`.

**Clasificación de cada agente.** Se fija antes de abrir test, con el IC al 98,75 %:

| Resultado | Condición |
| --- | --- |
| Supera | Límite inferior > 0 y media ≥ `Δ_min` |
| Mejor, pero no relevante | Límite inferior > 0 y media < `Δ_min` |
| Equivalente | El IC cae entero dentro de `(-Δ_min, +Δ_min)` (prueba TOST) |
| Inferior | Límite superior < 0 |
| Inconcluso | Cualquier otro caso |

Un agente que aprende a no operar tiene `D = 0` contra `NoTrade` y queda "equivalente". Según D1,
es un resultado válido.

**Diferencias iguales a cero:** si ni el agente ni el baseline operan en un mercado, `D_i = 0`. La
potencia depende de los mercados con `D_i ≠ 0`.

- Se reportan cuántos mercados y días tienen `D_i ≠ 0`.
- La media se descompone en `E[D] = P(opera) × E[D | opera]`.
- No se cambia a Wilcoxon ni a la prueba del signo: descartan los ceros y cambian lo que se mide.
- Con menos de unos 30 mercados con `D_i ≠ 0`, el informe dice que el IC no es confiable.

**Comparación secundaria:** cada agente contra `NoTrade` (¿gana dinero en absoluto?). Se reporta,
pero no define la clasificación.

## 7. Potencia: diferencia mínima detectable

Se calcula por agente después de entrenar y antes de abrir test, en val:

- `d̄_k`: media diaria de `D`, con las semillas promediadas.
- `σ²_LR = γ̂₀ + 2 × Σ_{h=1..3} (1 - h/4) × γ̂_h`, donde `γ̂_h` es la autocovarianza de `d̄_k`
  con desfase `h` (Newey-West).
- `s²_sem`: varianza entre semillas de la media de `D` en val.
- `SE = √(σ²_LR / 73 + s²_sem / 5)`.
- `MDE = (z_{1-0,025/4} + z_{0,80}) × SE ≈ 3,34 × SE`.

Antes de entrenar se puede aproximar con `FairValue` contra `NoTrade`. Como referencia: si cada
mercado operado tiene una desviación cercana a 1 (comprar cerca de 0,5 y esperar la liquidación) y
el agente opera en una fracción `f` de los mercados, `MDE ≈ 8 % × √f` por mercado antes de contar
la dependencia entre días. Eso da 8 % si opera siempre y 2,5 % si opera en uno de cada diez.

Si la MDE es mayor que `Δ_min`, el informe dice que test no puede detectar diferencias de ese
tamaño. Más mercados solo se consiguen con ETH (D2).

## 8. Métricas secundarias y sensibilidad

Se reportan para entender el resultado. No cambian la clasificación.

| Métrica | Definición |
| --- | --- |
| Retorno total y curva de capital | Suma de `PnL_i` en orden temporal |
| Sharpe por mercado | `media(R_i) / desviación(R_i)`, sin anualizar. Con muchos ceros engaña, así que va junto a la actividad |
| Max drawdown | Sobre la curva de capital acumulada en test |
| Win rate | Fracción de mercados con `PnL_i > 0` entre los que operó |
| Actividad | Operaciones por mercado y fracción de mercados sin operar |
| Costos | Spread y comisión pagados |
| Acciones inválidas | Porcentaje de acciones pedidas que se ejecutaron como `WAIT` (S6) |
| Órdenes no ejecutadas | Porcentaje de órdenes sin precio dentro de la tolerancia (S4) |

**Sensibilidad (exploratoria):**

- Medio spread de 0,02 en lugar de 0,01 (S5).
- Sin comisión, reentrenando con la configuración final (D1-C): separa "RL no aprende" de "los
  costos se comen todo".
- Latencia de ejecución más alta y más baja (S4).
- Bloques de bootstrap fijos de 1 y de 7 días, y una prueba t de Newey-West sobre las medias
  diarias.
- Primera y segunda mitad de test por separado.

## 9. Qué se reporta siempre

- Todas las comparaciones de este protocolo, también las negativas (D4). Ningún resultado
  planeado se omite.
- Lo que no esté en este protocolo se presenta como **exploratorio**.
- El tamaño del efecto con su IC y la clasificación de la sección 6, no solo si es significativo.
- **Validez externa:** test son unos 73 días de un solo régimen. Separarlo en dos mitades no lo
  resuelve, y el informe lo declara como limitación.

## 10. Decisiones del equipo en este PR

| # | Pregunta clave | Opciones | Recomendación |
| --- | --- | --- | --- |
| E1 | ¿Desde qué diferencia por mercado una mejora importa? (`Δ_min`, la pide D3) | 0,5 %, 1 % o 2 % del stake por mercado, promediado sobre todos los mercados de test (también los que no opera) | **1 %.** Con `stake_fraction = 0,10`, son unos +175 % del saldo inicial sumados sobre los 1 752 mercados: una ventaja grande y sostenida. La MDE probablemente sea mayor (sección 7), así que lo más probable es un resultado "inconcluso" o "equivalente", y se dirá |
| E2 | ¿Quién es el baseline de referencia? | `NoTrade` salvo que una heurística le gane en val; la heurística con mayor media en val | **`NoTrade` salvo que una heurística le gane en val.** Si ninguna heurística es rentable, la de mayor media en val sería una que casi no opera y ganó por azar |

## 11. Revisión estadística del primer borrador

| Hallazgo | Gravedad | Qué se cambió |
| --- | --- | --- |
| El "mejor baseline en val" casi seguro sería `NoTrade` o una heurística que ganó por azar | Alta | Regla de la sección 4 |
| El IC no incluía la variación entre semillas | Alta | Bootstrap de dos niveles (sección 6) |
| `Δ_min = 1 %` comparaba unidades distintas y probablemente no es detectable | Alta | Definición por mercado y potencia explícita (secciones 7 y 10) |
| El criterio no separaba "no supera" de "no se pudo saber" | Alta | Clasificación en cinco resultados (sección 6) |
| Bloques de un día suponían días independientes | Media | Bootstrap estacionario con largo de bloque de Politis y White |
| Holm y Bonferroni podían contradecirse | Media | Solo Bonferroni |
| Muchas diferencias iguales a cero | Media | Conteo y descomposición de la media |
| Elegir el checkpoint en val con poca señal | Baja | 10 checkpoints fijos y registro de lo probado |
| Faltaban reglas de exclusión, bugs tardíos y validez externa | Media | Secciones 2 y 9 |
