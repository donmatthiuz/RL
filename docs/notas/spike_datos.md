# Spike de datos (DAT-01)

Documentación oficial de las fuentes: [Polymarket](https://docs.polymarket.com) y
[Binance Spot API](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints).

- **Fecha de la medición:** 30/10/2026
- **SDK:** `polymarket-client==0.14.0` (el mismo de `pyproject.toml`)
- **Pregunta:** ¿hay datos históricos suficientes, con buena granularidad, para entrenar y evaluar
  un agente sobre mercados cerrados de BTC? ¿Qué familia de mercados conviene usar?
- **Conclusión corta:** sí. La familia elegida es **BTC Up or Down horario**, con precio cada
  minuto desde el endpoint CLOB `/prices-history`. Hay dos sorpresas que cambian el diseño: la
  Data API v2 que usa el SDK devuelve el historial **vacío** en mercados cerrados, y estos mercados
  cobran **comisión taker** desde 2026. Las decisiones están en
  [07_riesgos_y_decisiones.md](../07_riesgos_y_decisiones.md) (ADR-004, ADR-007 a ADR-009) y el
  diseño resultante en [08_datos_y_entrada_modelo.md](../08_datos_y_entrada_modelo.md).

## 1. Familias de mercados disponibles

Cada mercado "Up or Down" pertenece a una **serie** de Gamma. Las series de BTC y ETH encontradas:

| Serie (id) | Slug | Desde | Fuente de resolución |
| ------------ | ------ | ------- | ---------------------- |
| 10114 | `btc-up-or-down-hourly` | 2025-05-27 | Vela 1h de Binance BTC/USDT |
| 10192 | `btc-up-or-down-15m` | 2025-08-09 | Chainlink BTC/USD |
| 10684 | `btc-up-or-down-5m` | 2025-11-21 | Chainlink BTC/USD |
| 10331 | `btc-up-or-down-4h` | 2025-09-24 | No verificada |
| 41 | `btc-up-or-down-daily` | 2023-03-14 | No verificada |
| 10117, 10191, 10683, 10332, 40 | Equivalentes de ETH (horario, 15m, 5m, 4h, diario) | 2023 a 2025 | No verificada |

- El mercado horario resuelve con la vela de 1 hora de **Binance BTC/USDT**: "Up" si
  `close >= open`. El spot de Binance **reproduce exactamente** el resultado. Se comprobó con el
  mercado del 23/02/2026 a las 12 PM ET: open 65 364,66, close 64 813,26, resultado DOWN, igual que
  el mercado.
- Los mercados de 5 y 15 minutos resuelven con **Chainlink**, no con Binance. El spot de Binance
  solo sería una aproximación de la fuente de resolución.
- Mercados horarios cerrados: del 28/05/2025 al 30/10/2026. A 24 por día son del orden de
  **12 000 episodios**. Es una estimación: no se contaron uno por uno.

## 2. Historial de precios

| Vía | Resultado en mercados cerrados |
| ----- | -------------------------------- |
| SDK `list_price_history` (Data API `/v2/prices-history`) con `start`/`end` | **Vacío** en los 3 mercados probados (5m, 15m y horario) |
| SDK con `interval="max"` o `"all"` | Exige `bucket_seconds >= 600` (10 min) |
| `GET https://clob.polymarket.com/prices-history?market=<token_id>&startTs=&endTs=&fidelity=1` | **Funciona**, con un punto por minuto |
| El mismo endpoint con `interval=max` | Vacío: hay que pasar `startTs` y `endTs` |

Granularidad medida con el endpoint CLOB:

| Mercado horario | Puntos | Hueco mediano | Hueco máximo |
| ----------------- | -------- | --------------- | -------------- |
| 28/05/2025, 1 AM ET (el más antiguo) | 875 en toda su vida | 60 s | 88 s |
| 23/02/2026, 12 PM ET | 2 914 en toda su vida | 60 s | 1 408 s |
| 30/10/2026, 8 PM ET | 2 885 en toda su vida | 60 s | 293 s |

Muestra de **40 mercados horarios** cerrados de octubre de 2026:

- Puntos dentro de la ventana de 60 minutos: mediana **60** y mínimo **48**.
- `p(YES)` justo antes de que empiece la ventana: media 0,509, rango 0,455 a 0,545. El mercado
  existe unas 24 a 48 horas antes, pero su precio no se mueve de 0,5 hasta que empieza la vela.
- Resultado: UP ganó en 17 de los 40.

Calibración del mercado en esa muestra (el "favorito" es el lado con `p > 0,5`):

| Minuto de la ventana | Acierto del favorito | Brier | `abs(p - 0,5)` medio |
| ---------------------- | ---------------------- | ------- | ---------------------- |
| 0 | 57 % | 0,246 | 0,025 |
| 15 | 82 % | 0,179 | 0,174 |
| 30 | 85 % | 0,142 | 0,245 |
| 45 | 88 % | 0,102 | 0,322 |
| 55 | 90 % | 0,056 | 0,390 |

El precio incorpora información rápido. Una ventaja del agente solo puede venir de **reaccionar
antes que el mercado al movimiento del spot**, no de un mercado mal calibrado en general. La EDA
(DAT-08) lo tiene que medir con todos los mercados.

## 3. Comisiones

El campo `trading` de cada mercado trae su esquema de comisiones:

| Mercados horarios con cierre en | `fees_enabled` | Esquema |
|---------------------------------|----------------|---------|
| 05/2025, 08/2025, 12/2025, 02/2026 | `false` | Sin comisión |
| 05/2026, 08/2026, 10/2026 | `true` | `crypto_fees_v2`: `rate=0,07`, `exponent=1`, solo taker |

- Los mercados de 15 minutos ya cobraban en 02/2026 (`crypto_15_min`: `rate=0,25`, `exponent=2`).
- La fórmula sale del código del SDK (`polymarket/_internal/actions/orders/market.py`):
  `comisión = acciones × rate × (p × (1 - p))^exponent`.
- En un mercado horario con `p = 0,5`, comprar cuesta 0,0175 por acción, un **3,5 % del nocional**.
  Con `p = 0,9` baja a 0,0063 por acción, un 0,7 %.
- El cambio de régimen ocurrió entre marzo y mayo de 2026. No se buscó la fecha exacta.

## 4. Otros supuestos verificados

| Supuesto | Medición |
| ---------- | ---------- |
| `p_no = 1 - p_yes` | En 53 minutos comunes de un mercado: `abs(p_yes + p_no - 1)` medio 0,006 y máximo 0,045. Los dos tokens no siempre tienen punto en el mismo minuto. |
| Spread | 0,01 a 0,02 en 5 mercados horarios abiertos. No existe un histórico del spread. |
| `end_date` de Gamma marca el fin de la ventana | **Falso en mercados antiguos.** El de 28/05/2025 dice 12:00 UTC, pero la vela es de 05:00 a 06:00 UTC. En los recientes sí coincide. |
| Formato del título | Hay dos: `Bitcoin Up or Down – May 28 (1 AM ET Candle)` (2025) y `Bitcoin Up or Down - October 30, 8PM ET` (2026). La hora está en ET, con horario de verano. |
| Metadatos de resolución | Los mercados recientes traen `metadata.priceToBeat` y `metadata.finalPrice`. Los antiguos no. |
| Datos después del cierre | Hay precios y trades después del fin de la ventana (por ejemplo, compras a 0,001). Hay que cortar en el fin de la ventana. |
| Trades (`list_trades` por `condition_id`) | Responde, pero no se midió si devuelve la historia completa. No hace falta para la versión 1. |
| Binance | `api.binance.com` y `data-api.binance.vision` responden sin autenticación. |

## 5. Cómo se midió

Todas las consultas fueron públicas y de solo lectura, con el `PublicClient` del SDK y `httpx`:

- Mercados: `PublicClient.search`, `get_event`, `get_series` y
  `list_events(series_ids=10114, closed=True, order="endDate")`.
- Precios: el endpoint CLOB de la sección 2 con `fidelity=1`.
- Spot: `GET /api/v3/klines?symbol=BTCUSDT&interval=1h|1m`.
- Spread actual: `PublicClient.get_spread`.

Los scripts fueron exploratorios y no se versionaron. Los números de este documento se pueden
volver a medir con el pipeline de [08_datos_y_entrada_modelo.md](../08_datos_y_entrada_modelo.md).

## 6. Impacto en el código actual

`polym4v.PolymarketClient.get_price_history` (antes en `rl_polymarket`) usa la Data API v2 del
SDK, así que **devuelve vacío para mercados cerrados**. La documentación oficial lo explica: en la
v2, cualquier resolución menor a 3 horas cubre solo los últimos 30 días. El pipeline de datos tiene que llamar al endpoint CLOB
directamente. El resto del cliente (consulta de mercados y eventos) sí sirve para la extracción.
