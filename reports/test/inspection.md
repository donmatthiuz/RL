# Inspección posterior de test

Descripción de las trayectorias que dejó la evaluación final en test (EVA-06), sin volver a correr
ninguna política ni cambiar ningún modelo (EVA-12). No es una prueba nueva ni cambia la conclusión
de test, que es la de [comparison.md](comparison.md).

## Qué hace cada política

| Política | Semillas | Operaciones | Por mercado | Minuto mediano de compra | Compra el favorito | Precio > 0.98 | Vendidas antes del final | Lado acertado | Con ganancia | PnL total (USDC) | Verificadas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc_pnl_risk | 5 | 24 | 0.0027 | 32 | 0.3750 | 0.0000 | 0.2917 | 0.2500 | 0.2917 | -243.50 | 0.7917 |
| cql_pnl_risk | 5 | 323 | 0.0369 | 47 | 0.0248 | 0.0000 | 0.6223 | 0.1331 | 0.1920 | -2214.79 | 0.4706 |
| dqn_pnl_risk | 5 | 2600 | 0.2970 | 48 | 0.9712 | 0.3481 | 0.1838 | 0.9342 | 0.8196 | -321.50 | 0.5835 |
| ppo_pnl_risk | 5 | 1006 | 0.1149 | 54 | 0.9861 | 0.8330 | 0.0855 | 0.9702 | 0.9245 | -83.81 | 0.5089 |
| fair_value | 1 | 456 | 0.2604 | 36 | 0.4320 | 0.0000 | 0.0000 | 0.4539 | 0.4539 | -750.54 | 0.5351 |
| favorite | 1 | 1721 | 0.9829 | 20 | 1.0000 | 0.0000 | 0.0000 | 0.6839 | 0.6839 | -1087.52 | 0.3992 |
| mean_reversion | 1 | 2972 | 1.6973 | 40 | 0.0784 | 0.0000 | 0.9845 | 0.2736 | 0.2813 | -10368.64 | 0.5047 |
| momentum | 1 | 2380 | 1.3592 | 38 | 0.9109 | 0.0134 | 0.7592 | 0.6962 | 0.5042 | -2992.24 | 0.5887 |
| random | 1 | 17491 | 9.9891 | 27 | 0.4988 | 0.0406 | 0.9624 | 0.5028 | 0.2653 | -52486.35 | 0.4342 |

- Una operación va de la compra a la venta o a la liquidación al final del mercado; su PnL es el
  cambio del valor de la cartera en ese tramo, después de costos, y suma las semillas.
- Lado acertado: el lado comprado fue el ganador. Con ganancia: la operación terminó con PnL
  positivo; una venta antes del final puede perder aunque el lado gane.
- Verificadas: ejecuciones respaldadas por trades reales (EVA-11).

## Precisión contra rentabilidad

| Agente | Precio del lado comprado | Operaciones | Lado acertado | IC 95 % inferior | IC 95 % superior | Con ganancia | Ganancia media (USDC) | Pérdida media (USDC) | Ganancias por pérdida | Neto (USDC) | Costo por acción |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bc_pnl_risk | 0-0.5 | 16 | 0.0000 | 0.0000 | 0.1936 | 0.0625 | 13.55 | -17.41 | 1.3 | -247.54 | 0.1086 |
| bc_pnl_risk | 0.5-0.8 | 5 | 0.6000 | 0.2307 | 0.8824 | 0.6000 | 11.22 | -16.41 | 1.5 | 0.83 | 0.6715 |
| bc_pnl_risk | 0.8-0.95 | 2 | 1.0000 | 0.3424 | 1.0000 | 1.0000 | 1.36 | — | — | 2.73 | 0.9369 |
| bc_pnl_risk | 0.95-0.98 | 1 | 1.0000 | 0.2065 | 1.0000 | 1.0000 | 0.48 | — | — | 0.48 | 0.9767 |
| cql_pnl_risk | 0-0.5 | 309 | 0.1133 | 0.0826 | 0.1535 | 0.1748 | 26.85 | -14.33 | 0.5 | -2204.78 | 0.1137 |
| cql_pnl_risk | 0.5-0.8 | 12 | 0.5000 | 0.2538 | 0.7462 | 0.5000 | 9.44 | -11.97 | 1.3 | -15.15 | 0.6784 |
| cql_pnl_risk | 0.8-0.95 | 2 | 1.0000 | 0.3424 | 1.0000 | 1.0000 | 2.57 | — | — | 5.14 | 0.8895 |
| dqn_pnl_risk | 0-0.5 | 55 | 0.4182 | 0.2974 | 0.5497 | 0.4182 | 16.94 | -9.08 | 0.5 | 99.02 | 0.2754 |
| dqn_pnl_risk | 0.5-0.8 | 116 | 0.8017 | 0.7200 | 0.8641 | 0.6034 | 6.65 | -8.74 | 1.3 | 63.45 | 0.7393 |
| dqn_pnl_risk | 0.8-0.95 | 1066 | 0.8996 | 0.8801 | 0.9163 | 0.8030 | 1.73 | -9.24 | 5.3 | -456.86 | 0.9170 |
| dqn_pnl_risk | 0.95-0.98 | 458 | 0.9869 | 0.9717 | 0.9940 | 0.9039 | 0.47 | -3.33 | 7.2 | 45.97 | 0.9772 |
| dqn_pnl_risk | 0.98-1 | 905 | 0.9967 | 0.9903 | 0.9989 | 0.8486 | 0.03 | -0.69 | 24.4 | -73.07 | 0.9986 |
| ppo_pnl_risk | 0-0.5 | 19 | 0.2632 | 0.1181 | 0.4879 | 0.4211 | 12.59 | -9.21 | 0.7 | -0.63 | 0.2804 |
| ppo_pnl_risk | 0.5-0.8 | 24 | 0.7083 | 0.5083 | 0.8509 | 0.5833 | 5.62 | -9.14 | 1.6 | -12.68 | 0.7460 |
| ppo_pnl_risk | 0.8-0.95 | 61 | 0.9180 | 0.8221 | 0.9645 | 0.6721 | 1.65 | -3.80 | 2.3 | -8.36 | 0.9186 |
| ppo_pnl_risk | 0.95-0.98 | 64 | 0.9688 | 0.8930 | 0.9914 | 0.7969 | 0.32 | -3.95 | 12.3 | -34.92 | 0.9822 |
| ppo_pnl_risk | 0.98-1 | 838 | 0.9976 | 0.9913 | 0.9993 | 0.9737 | 0.02 | -2.14 | 87.7 | -27.23 | 0.9988 |

- Precio del lado comprado: al ejecutarse la orden, sin costos.
- Costo por acción: lo pagado por cada acción, con medio spread y comisión. La acción ganadora paga
  1, así que manteniendo hasta el final hay que acertar al menos esa proporción para no perder.
- Ganancias por pérdida: cuántas ganancias medias hacen falta para cubrir una pérdida media.
- IC de Wilson al 95 % del lado acertado. Las semillas operan en los mismos mercados, así que las
  operaciones no son independientes y el intervalo es optimista.

## Pérdidas grandes en compras a más de 0,98

| Agente | Semilla | Mercado | Minuto de compra | Lado | Precio | Salida | PnL (USDC) | BTC contra la apertura al comprar | BTC contra la apertura al final | Precio mínimo del lado después de comprar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dqn_pnl_risk | 0 | 0x06147f3d | 52 | NO | 0.9955 | liquidación | -20.00 | -0.109% | +0.025% | 0.9170 |
| dqn_pnl_risk | 0 | 0x3e5b7a05 | 53 | NO | 0.9860 | venta en 57 | -2.59 | -0.105% | -0.069% | 0.9860 |
| dqn_pnl_risk | 0 | 0x73f44df1 | 57 | NO | 0.9850 | venta en 58 | -6.95 | -0.107% | +0.112% | 0.9050 |
| dqn_pnl_risk | 1 | 0x06147f3d | 52 | NO | 0.9955 | venta en 59 | -18.44 | -0.109% | +0.025% | 0.9170 |
| dqn_pnl_risk | 3 | 0xf18cc2be | 56 | NO | 0.9925 | venta en 59 | -10.33 | -0.188% | -0.003% | 0.9730 |
| ppo_pnl_risk | 0 | 0x915222a8 | 36 | YES | 0.9805 | venta en 40 | -1.56 | +0.943% | +1.199% | 0.9460 |
| ppo_pnl_risk | 1 | 0x06147f3d | 50 | NO | 0.9885 | liquidación | -20.00 | -0.109% | +0.025% | 0.9170 |
| ppo_pnl_risk | 1 | 0xf2f9169b | 54 | NO | 0.9850 | venta en 56 | -1.17 | -0.728% | -0.406% | 0.8750 |
| ppo_pnl_risk | 4 | 0x06147f3d | 50 | NO | 0.9885 | venta en 59 | -18.43 | -0.109% | +0.025% | 0.9170 |

- Compras a más de 0,98 que perdieron más de 1 USDC.
- BTC contra la apertura: variación del spot de Binance respecto del de la apertura del mercado, al
  comprar y en el último paso. El mercado se resuelve UP si BTC cierra por encima de la apertura.
- Precio mínimo del lado: el más bajo que tuvo el lado comprado en los pasos de la grilla, de
  minuto en minuto, mientras se mantuvo la posición. Una venta se ejecuta al precio siguiente, así
  que puede ser mucho peor.
