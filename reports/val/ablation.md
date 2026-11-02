## Ablación de la recompensa en val

Cada semilla aporta el retorno de su mejor checkpoint en este split. El IC es de la media
entre semillas (t de Student), así que solo mide la variación entre semillas.

| Variante | Semillas | Retorno del mejor checkpoint | DE entre semillas | IC 95 % inferior | IC 95 % superior | Retorno medio de la curva | Operaciones por mercado | Mercados sin operar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ppo_pnl_risk (base=pnl_mid, λ_dd=1) | 5 | 0.0012 | 0.0009 | 0.0001 | 0.0023 | -0.0070 | 0.1208 | 0.8934 |
| ppo_pnl_risk (base=pnl_mid, λ_dd=0.5) | 5 | 0.0001 | 0.0014 | -0.0016 | 0.0018 | -0.0105 | 0.2702 | 0.7684 |
| ppo_utility (a=1) | 5 | -0.0307 | 0.0142 | -0.0483 | -0.0131 | -0.1141 | 1.2543 | 0.1085 |
| ppo_pnl_mid | 5 | -0.0348 | 0.0031 | -0.0386 | -0.0309 | -0.0584 | 1.2711 | 0.0478 |
| ppo_pnl | 5 | -0.0358 | 0.0075 | -0.0451 | -0.0264 | -0.0589 | 1.1367 | 0.0183 |
| ppo_pnl_hold (base=pnl_mid, λ_hold=2.5e-05) | 5 | -0.0373 | 0.0145 | -0.0553 | -0.0194 | -0.0655 | 1.3425 | 0.0552 |
| ppo_terminal | 5 | -0.0673 | 0.0236 | -0.0965 | -0.0381 | -0.1436 | 1.6935 | 0.0342 |
