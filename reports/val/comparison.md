## Prueba del protocolo en val

| Agente | Estricto | Comparación | Baseline | Semillas | Media de D | IC inferior | IC superior | Clasificación | Mercados con D ≠ 0 | Días con D ≠ 0 | P(D ≠ 0) | E[D \| D ≠ 0] | IC confiable | MDE | Depende de liquidez |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc_pnl_risk | no | principal | no_trade | 5 | 0.0029 | -0.0011 | 0.0550 | inconcluso | 35 | 28 | 0.0039 | 0.7490 | sí | 0.0129 | sí |
| cql_pnl_risk | no | principal | no_trade | 5 | 0.0109 | -0.0203 | 0.1304 | inconcluso | 196 | 66 | 0.0389 | 0.2790 | sí | 0.0737 | no |
| dqn_pnl_risk | no | principal | no_trade | 5 | -0.0015 | -0.0080 | 0.0033 | equivalente | 1556 | 79 | 0.2794 | -0.0053 | sí | 0.0061 | sí |
| ppo_pnl_risk | no | principal | no_trade | 5 | 0.0012 | 0.0002 | 0.0065 | mejor, pero no relevante | 673 | 79 | 0.1066 | 0.0111 | sí | 0.0021 | sí |
| bc_pnl_risk | sí | principal | no_trade | 5 | 0.0005 | -0.0015 | 0.0086 | equivalente | 21 | 19 | 0.0024 | 0.1961 | no | 0.0129 | sí |
| cql_pnl_risk | sí | principal | no_trade | 5 | 0.0147 | -0.0157 | 0.1446 | inconcluso | 139 | 54 | 0.0273 | 0.5373 | sí | 0.0737 | no |
| dqn_pnl_risk | sí | principal | no_trade | 5 | -0.0032 | -0.0121 | 0.0003 | inconcluso | 1517 | 79 | 0.2383 | -0.0134 | sí | 0.0061 | sí |
| ppo_pnl_risk | sí | principal | no_trade | 5 | 0.0006 | -0.0002 | 0.0022 | equivalente | 490 | 79 | 0.0709 | 0.0078 | sí | 0.0021 | sí |

bc_pnl_risk: la MDE (0.0129) es mayor que Δ_min (0.0100), así que test no puede detectar diferencias de ese tamaño.

cql_pnl_risk: la MDE (0.0737) es mayor que Δ_min (0.0100), así que test no puede detectar diferencias de ese tamaño.

Con menos de 30 mercados con D ≠ 0, el IC no es confiable.
