# 11 — Descarga de datos

Documentación oficial: [API de Polymarket](https://docs.polymarket.com) y
[API de Binance, klines](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints).

Cómo reproducir desde cero los datos del proyecto. Todo se hace con `make`. Los datos no se
versionan: cada integrante los descarga y comprueba con el manifest que obtuvo lo mismo. El
diseño del ETL está en [08_datos_y_entrada_modelo.md](08_datos_y_entrada_modelo.md).

## 1. Requisitos

- `uv` y `make`. La primera vez, `make setup`.
- Internet. Las APIs son públicas y no hace falta ninguna clave.
- Unos 300 MB de disco para el crudo de BTC y ETH, y unos 55 MB para el dataset procesado.
- La carpeta de datos es `data/` por defecto. Se cambia con `POLYM4V_DATA_DIR` en `.env`, o con
  `RAW_DIR=<carpeta>` en cada comando de `make`.

## 2. Pasos y tiempos

Tiempos medidos el 30 y 31/10/2026 en una sola máquina (WSL2), con la pausa por defecto de 0,2 s
entre peticiones: unos **77 mercados por minuto**.

| Paso | Comando | Qué hace | Tiempo medido | Resultado |
| --- | --- | --- | --- | --- |
| 1 | `make capture` | Metadatos y precios YES y NO de cada mercado BTC horario cerrado (serie 10114) | 2 h 45 min | 12 471 mercados, 0 errores |
| 2 | `make capture SERIES=10117` | Lo mismo para ETH horario, respaldo de ADR-013 | Unas 2 h 40 min (estimado) | Unos 12 000 mercados |
| 3 | `make capture-spot` | Klines de Binance de 1 minuto y de 1 hora, con el activo y las fechas de `configs/data.yaml` | 8 min | 1 044 bloques de 1 m y 522 de 1 h, 0 errores |
| 4 | `make manifest` | Recalcula el hash de cada archivo del crudo | Segundos | `data/raw/manifest.json` |
| 5 | `make dataset` | Construye `markets`, `prices_raw` y `spot_1m` | Unos 15 s | 12 295 mercados (8 683 en train, 1 860 en val y 1 752 en test) |
| 6 | `make eda` (opcional) | Ejecuta el notebook de EDA, solo con train | Unos 10 s | Notebook y figuras en `docs/images/eda/` |

Los pasos 3, 5 y 6 llegan a `proyecto` con los PR #2, #5 y #7 (sección "Tablero" de
[04_tareas.md](04_tareas.md)). Hasta que se mezclen, se corren desde la rama de esos PR.

Las capturas largas se pueden dejar corriendo en segundo plano. El resumen sale por la salida
estándar y el progreso, cada 250 mercados, por la de errores:

```bash
nohup make -s capture > data/raw/capture_btc.json 2> data/raw/capture_btc.log &
tail -f data/raw/capture_btc.log
```

## 3. Si se corta

- **Volver a correr el mismo comando.** Lo que ya está en `data/raw/` no se vuelve a pedir, así
  que la captura sigue donde quedó.
- **Fallas de red y límites de la API:** se reintenta con espera exponencial, también al listar
  los mercados en Gamma.
- **Bloques de Binance todavía abiertos** (los del día en curso): se reportan como `pending` y no
  se guardan. Se completan corriendo `make capture-spot` más tarde.

## 4. Cómo verificar

- **Resumen de la captura:** `errors` tiene que quedar vacío y `limit_reached` en `false`. Si hay
  errores, se vuelve a correr el comando: solo pide lo que falta.
- **Dataset:** su `manifest.json` trae el conteo por split, los mercados descartados con su motivo
  y el hash de cada Parquet. Con el mismo crudo, `make dataset` da siempre los mismos hashes.
- **Entre máquinas:** cada archivo del crudo guarda la fecha en que se descargó, así que sus
  hashes no coinciden entre personas. Lo que tiene que coincidir son los Parquet del dataset.

## 5. Dónde queda cada cosa

Solo se versiona la estructura de carpetas: `data/raw/.gitkeep` y `data/processed/.gitkeep`.

| Carpeta | Contenido |
| --- | --- |
| `data/raw/gamma/events/<serie>/` | Un evento de Gamma por archivo, tal cual lo devuelve el SDK |
| `data/raw/clob/prices-history/` | El historial de precios de cada token, con la petición que lo produjo |
| `data/raw/binance/klines/<símbolo>/<intervalo>/` | Un bloque de klines por archivo |
| `data/raw/manifest.json` | Tamaño y hash de cada archivo del crudo |
| `data/processed/<dataset_id>/` | `markets.parquet`, `prices_raw.parquet`, `spot_1m.parquet` y `manifest.json` |
