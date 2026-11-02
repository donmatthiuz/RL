## Prueba del protocolo en test

| Agente | Estricto | Comparación | Baseline | Semillas | Media de D | IC inferior | IC superior | Clasificación | Mercados con D ≠ 0 | Días con D ≠ 0 | P(D ≠ 0) | E[D \| D ≠ 0] | IC confiable | MDE | Depende de liquidez |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc_pnl_risk | no | principal | no_trade | 5 | -0.0014 | -0.0050 | -0.0000 | peor, pero no relevante | 23 | 18 | 0.0027 | -0.5073 | no | 0.0129 | sí |
| cql_pnl_risk | no | principal | no_trade | 5 | -0.0126 | -0.0263 | -0.0027 | inferior | 144 | 56 | 0.0314 | -0.4027 | sí | 0.0737 | no |
| dqn_pnl_risk | no | principal | no_trade | 5 | -0.0018 | -0.0082 | 0.0036 | equivalente | 1466 | 76 | 0.2790 | -0.0066 | sí | 0.0061 | sí |
| ppo_pnl_risk | no | principal | no_trade | 5 | -0.0005 | -0.0029 | 0.0018 | equivalente | 664 | 76 | 0.1118 | -0.0043 | sí | 0.0021 | no |
| bc_pnl_risk | sí | principal | no_trade | 5 | -0.0012 | -0.0043 | 0.0000 | equivalente | 18 | 15 | 0.0022 | -0.5397 | no | 0.0129 | sí |
| cql_pnl_risk | sí | principal | no_trade | 5 | -0.0102 | -0.0197 | -0.0048 | inferior | 79 | 41 | 0.0169 | -0.6009 | sí | 0.0737 | no |
| dqn_pnl_risk | sí | principal | no_trade | 5 | -0.0033 | -0.0110 | 0.0002 | inconcluso | 1409 | 76 | 0.2273 | -0.0145 | sí | 0.0061 | sí |
| ppo_pnl_risk | sí | principal | no_trade | 5 | -0.0011 | -0.0037 | 0.0006 | equivalente | 479 | 76 | 0.0722 | -0.0149 | sí | 0.0021 | no |

bc_pnl_risk: la MDE (0.0129) es mayor que Δ_min (0.0100), así que test no puede detectar diferencias de ese tamaño.

cql_pnl_risk: la MDE (0.0737) es mayor que Δ_min (0.0100), así que test no puede detectar diferencias de ese tamaño.

Con menos de 30 mercados con D ≠ 0, el IC no es confiable.
