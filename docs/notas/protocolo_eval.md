# Protocolo de evaluación (EVA-01)

Documentación oficial de las herramientas: [scipy.stats.bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
y [statsmodels multipletests (Holm)](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html).

Cómo se va a decidir si los agentes funcionan, escrito **antes** de ver cualquier resultado para
no ajustar el análisis a lo que salga (*p-hacking*). Se aprueba en su PR y se congela al
mezclarlo: cambiarlo después exige un ADR que diga qué cambió y por qué.

- **Estado:** borrador para aprobar (31/10/2026). Las decisiones que tiene que tomar el equipo
  están en la sección 9.
- **Base:** la pregunta del proyecto (D1), el compromiso de reportar aunque nada gane (D4), el
  tamaño de los datos (D3), los splits (DAT-06 y S11) y el simulador ([09](../09_sistema_simulacion.md)).

## 1. Qué pregunta responde

¿Algún agente de RL (PPO, DQN, CQL o BC) **supera al mejor baseline con los mismos costos**? El
retorno absoluto puede ser negativo: lo que se mide es la diferencia contra estrategias simples
(D1). Si ningún agente gana, se reporta igual (D4).

## 2. Datos y splits

| Split | Mercados | Para qué se usa |
| --- | --- | --- |
| train | 8 683 | Entrenar, ajustar normalizaciones y generar el dataset offline |
| val | 1 860 | Elegir hiperparámetros, checkpoints, parámetros de los baselines y el mejor baseline |
| test | 1 752 | Una sola evaluación final (EVA-06), con todo congelado |

- Los mercados de los análisis previos ya están fuera de test (S11).
- Antes de abrir test se congela todo: commit, configs resueltas, hash del dataset y semillas.
  Se registran en `reports/test/`.
- Ninguna decisión usa test. Si alguien lo mira antes de tiempo, se declara en el informe.

## 3. Unidad de análisis y métrica principal

- **Unidad:** el mercado (un episodio).
- **Métrica principal:** retorno por mercado sobre el monto apostado,
  `R_i = PnL_i / stake`. El PnL incluye spread, comisión y liquidación. Un mercado en el que el
  agente no opera tiene `R_i = 0`.
- **Comparación principal:** la diferencia pareada por mercado
  `D_i = R_i(agente) - R_i(mejor baseline)`. Es pareada porque ambos juegan los mismos mercados,
  y eso quita la variación entre mercados.
- **Condiciones:** las de la configuración principal del simulador (S4, S5 y S6). Las variantes
  van a la sección 7 y no cambian la conclusión.

## 4. Baselines

- Los de [02_arquitectura.md](../02_arquitectura.md) (sección 2.5): `Random`, `NoTrade`,
  `Favorite`, `Momentum` y `MeanReversion`. También `FairValue` si S3 deja `edge` en la
  observación.
- Pasan por el mismo entorno que los agentes: misma observación, mismos costos y misma ejecución
  (revisión de S1 a S8, sección 4.2 de [09](../09_sistema_simulacion.md)).
- Sus parámetros (umbrales) se ajustan en val con una búsqueda pequeña y fija, igual que los
  hiperparámetros de los agentes.
- **Mejor baseline:** el de mayor retorno medio por mercado en val. Se fija antes de abrir test.

## 5. Semillas y selección de modelos

- Cada configuración final se entrena con **5 semillas**.
- El checkpoint de cada semilla se elige por su retorno medio en val.
- En test, cada mercado se juega una vez por semilla, en el mismo orden para todos (S7). El
  retorno del agente en un mercado es la media de sus 5 semillas, es decir, el rendimiento
  esperado del algoritmo. También se reporta la variación entre semillas.
- `Random` también se corre con 5 semillas.

## 6. Prueba estadística

- **Intervalo:** IC 95 % de la media de `D_i` por bootstrap **por bloques de un día** (UTC). Se
  remuestrean días completos, de unos 24 mercados, con 10 000 réplicas y el método del
  percentil. Se remuestrea por día porque los mercados del mismo día comparten el régimen de BTC
  y no son independientes. Agente y baseline usan los mismos días remuestreados.
- **Comparaciones múltiples:** son 4 comparaciones (PPO, DQN, CQL y BC contra el mejor
  baseline). Se corrigen con Holm sobre los valores p del bootstrap, y se reportan también los IC
  simultáneos al 98,75 % (Bonferroni).
- **Cuándo un agente "supera":** el límite inferior de su IC corregido es mayor que cero **y** la
  diferencia media es al menos la diferencia mínima relevante `Δ_min` (sección 9).
- **Potencia:** antes de abrir test se estima con val la diferencia mínima detectable con los
  días de test, usando la desviación de `D_i` por día. Si es mayor que `Δ_min`, el informe dice
  que test no puede detectar diferencias de ese tamaño.
- **Comparación secundaria:** cada agente contra `NoTrade` (¿gana dinero en absoluto?). Se
  reporta, pero no define si el agente supera a los baselines.

## 7. Métricas secundarias y sensibilidad

Se reportan para entender el resultado. No cambian la conclusión principal.

| Métrica | Definición |
| --- | --- |
| Retorno total y curva de capital | Suma de `PnL_i` en orden temporal |
| Sharpe por mercado | `media(R_i) / desviación(R_i)`, sin anualizar |
| Max drawdown | Sobre la curva de capital acumulada en test |
| Win rate | Fracción de mercados con `PnL_i > 0` entre los que operó |
| Actividad | Operaciones por mercado y fracción de mercados sin operar |
| Costos | Spread y comisión pagados |
| Acciones inválidas | Porcentaje de acciones pedidas que se ejecutaron como `WAIT` (S6) |
| Órdenes no ejecutadas | Porcentaje de órdenes sin precio dentro de la tolerancia (S4) |

**Sensibilidad:**

- Medio spread de 0,02 en lugar de 0,01 (S5).
- Sin comisión, como ablación (ADR-009).
- Latencia del feed más alta y más baja (S4).
- Primera y segunda mitad de test por separado.

## 8. Qué se reporta siempre

- Todas las comparaciones de este protocolo, también las negativas (D4). Ningún resultado
  planeado se omite.
- Lo que no esté en este protocolo se presenta como **exploratorio**.
- El tamaño del efecto con su IC, no solo si es significativo.

## 9. Decisiones del equipo en este PR

| # | Pregunta | Opciones | Recomendación |
| --- | --- | --- | --- |
| E1 | ¿Desde qué diferencia una mejora importa? (`Δ_min`, la pide D3) | Cualquier diferencia significativa; 1 % del stake por mercado; el costo de una operación (cerca del 5 %) | **1 % del stake por mercado.** Es menor que el costo de operar, pero sobre 1 752 mercados ya es una ventaja sostenida. Exigir el 5 % dejaría sin chance a ventajas reales y pequeñas |
| E2 | ¿Contra qué baseline se compara? | El mejor en val (1 comparación por agente); todos los baselines (6 por agente) | **El mejor en val.** Con todos, las comparaciones pasan de 4 a 24 y la corrección por multiplicidad le quita potencia a test |
