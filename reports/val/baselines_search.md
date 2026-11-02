## Búsqueda de umbrales de los baselines

Cada punto se corrió en modo normal; se elige el de mayor retorno medio por mercado.

| Baseline | Parámetros | Retorno medio | Operaciones por mercado | Mercados sin operar |
| --- | --- | --- | --- | --- |
| favorite | `{"entry_k": 10}` | -0.0424 | 1.00 | 0.00 |
| favorite (elegido) | `{"entry_k": 20}` | -0.0199 | 1.00 | 0.00 |
| favorite | `{"entry_k": 30}` | -0.0248 | 1.00 | 0.00 |
| favorite | `{"entry_k": 40}` | -0.0209 | 1.00 | 0.00 |
| favorite | `{"entry_k": 50}` | -0.0206 | 1.00 | 0.00 |
| momentum | `{"threshold": 0.5, "take_profit": 0.1, "stop_loss": 0.1}` | -0.7770 | 17.02 | 0.00 |
| momentum | `{"threshold": 0.5, "take_profit": 0.2, "stop_loss": 0.2}` | -0.3973 | 9.36 | 0.00 |
| momentum | `{"threshold": 1.0, "take_profit": 0.1, "stop_loss": 0.1}` | -0.4449 | 10.59 | 0.00 |
| momentum | `{"threshold": 1.0, "take_profit": 0.2, "stop_loss": 0.2}` | -0.2851 | 7.09 | 0.00 |
| momentum | `{"threshold": 2.0, "take_profit": 0.1, "stop_loss": 0.1}` | -0.1072 | 2.82 | 0.27 |
| momentum (elegido) | `{"threshold": 2.0, "take_profit": 0.2, "stop_loss": 0.2}` | -0.0848 | 2.37 | 0.27 |
| mean_reversion | `{"threshold": 0.5, "take_profit": 0.1, "stop_loss": 0.1}` | -2.6708 | 28.10 | 0.00 |
| mean_reversion | `{"threshold": 0.5, "take_profit": 0.2, "stop_loss": 0.2}` | -1.8904 | 17.45 | 0.00 |
| mean_reversion | `{"threshold": 1.0, "take_profit": 0.1, "stop_loss": 0.1}` | -1.5308 | 16.33 | 0.00 |
| mean_reversion | `{"threshold": 1.0, "take_profit": 0.2, "stop_loss": 0.2}` | -1.1811 | 11.65 | 0.00 |
| mean_reversion | `{"threshold": 2.0, "take_profit": 0.1, "stop_loss": 0.1}` | -0.4322 | 4.13 | 0.27 |
| mean_reversion (elegido) | `{"threshold": 2.0, "take_profit": 0.2, "stop_loss": 0.2}` | -0.3485 | 3.45 | 0.27 |
| fair_value | `{"margin": 0.0}` | -0.0533 | 1.00 | 0.00 |
| fair_value | `{"margin": 0.02}` | -0.0770 | 0.97 | 0.03 |
| fair_value | `{"margin": 0.05}` | -0.0609 | 0.70 | 0.30 |
| fair_value (elegido) | `{"margin": 0.1}` | -0.0189 | 0.21 | 0.79 |
