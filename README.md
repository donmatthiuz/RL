# PolyRL — Aprendizaje por Refuerzo en Polymarket

Proyecto del curso de **Aprendizaje por Refuerzo**. Un agente de RL (PPO, DQN y una variante
Offline RL) aprende, sobre mercados históricos de Polymarket relacionados con BTC/ETH reproducidos
en un simulador, cuándo comprar **YES**, comprar **NO**, **vender** o **esperar**, usando saldo
ficticio. Sus resultados se comparan contra estrategias simples.

> Polymarket solo se usa como fuente de datos. El agente **nunca** opera en vivo ni con dinero real.

## Documentación

La planificación está en [`docs/`](docs/). Conviene leerla en orden, porque cada documento asume
que se leyó el anterior.

| # | Documento | Qué contiene |
| --- | ----------- | -------------- |
| 01 | [Idea general](docs/01_idea_general.md) | Problema, objetivo, alcance, hipótesis y criterios de éxito |
| 02 | [Arquitectura](docs/02_arquitectura.md) | Módulos, flujo de datos, entorno, agentes, recompensa, estructura del repo y stack |
| 03 | [Roles](docs/03_roles.md) | Las 5 personas del equipo, responsabilidades y matriz RACI |
| 04 | [Tareas](docs/04_tareas.md) | Backlog por rol, fases, dependencias e hitos |
| 05 | [Testing y CI/CD](docs/05_testing.md) | Normas de testing, cobertura, GitHub Actions y despliegue |
| 06 | [Flujo de trabajo](docs/06_flujo_trabajo.md) | Trabajo en la rama `proyecto`, commits, tests por entrega y Definition of Done |
| 07 | [Riesgos y decisiones](docs/07_riesgos_y_decisiones.md) | Riesgos técnicos, mitigaciones y registro de decisiones (ADR) |
| 08 | [Datos y entrada del modelo](docs/08_datos_y_entrada_modelo.md) | Extracción, ETL, EDA, observación del agente, costos y supuestos verificados |
| 09 | [Sistema de simulación](docs/09_sistema_simulacion.md) | Modelo de tiempo, ejecución, costos y comportamiento del entorno, basado en prácticas open source |
| 10 | [Entrega final](docs/10_entrega_final.md) | Qué pide el curso, dónde vive cada entregable y si cumplimos |
| 11 | [Descarga de datos](docs/11_descarga_de_datos.md) | Cómo reproducir los datos desde cero, cuánto tarda y cómo verificarlo |

Las notas de trabajo están en [`docs/notas/`](docs/notas/): el
[spike de datos](docs/notas/spike_datos.md) y las
[decisiones previas al diseño](docs/notas/decisiones_previas_al_diseno.md). El uso de IA está en
[`docs/ia/`](docs/ia/): [herramientas y por qué](docs/ia/uso_de_ia.md),
[historial de prompts](docs/ia/historial_prompts.md) e [investigaciones](docs/ia/investigaciones/).
Las entregas al profesor están en [`entregas/`](entregas/).

## Inicio rápido

Todos los comandos del proyecto están en el `Makefile`; `make help` los lista. Requiere
[uv](https://docs.astral.sh/uv/) y `make`.

```bash
# Primera vez: dependencias exactas de uv.lock, hooks de pre-commit y archivos de claves
make setup

# Antes de subir: lo mismo que corre la CI (lint, tipos y tests con cobertura)
make check

# Validar la configuración del dataset (parámetros en configs/, rutas y claves en .env)
make config

# Archivar el historial crudo de precios (BTC horario por defecto; ETH con SERIES=10117)
make capture

# Archivar las klines de Binance (1m y 1h) del activo y las fechas de configs/data.yaml
make capture-spot
make manifest

# Construir markets, prices_raw y spot_1m desde el crudo (data/processed/<dataset_id>/)
make dataset

# Ejecutar la EDA (notebooks/eda/), solo con train; las figuras quedan en docs/images/eda/
make eda

# Baselines y entrenamiento (configs/<agente>.yaml, todas sus semillas)
make backtest POLICY=fair_value SPLIT=val
make collect-offline AGENT=cql
make train AGENT=ppo

# Evaluar una corrida en val y armar el reporte del split (reports/val/)
uv run polym4v evaluate --run models/ppo/<corrida> --split val
make report SPLIT=val

# Comportamiento de los agentes (EVA-12) y demo
make behavior
make demo

# Generar el PDF de una entrega
make entregable ENTREGA=2026-10-30 PDF="Entregable 30.pdf"

# Publicar los modelos y trayectorias en el Release de un tag (después del workflow release.yml)
make release-modelos TAG=v1.0
```

## Demo

`make demo` abre la demo de Streamlit. Empieza en test con el mejor agente del protocolo (PPO,
con su semilla mediana) frente a `NoTrade`, en el primer mercado donde operó; desde la barra
lateral se elige cualquier otra política, mercado o paso. Lee las trayectorias de
`reports/trajectories/` y, si no hay, la muestra de test de [`app/trayectorias/`](app/trayectorias/)
(PPO, `NoTrade` y `fair_value`).

**Versión publicada:** pendiente (EVA-09). Para publicarla en Streamlit Community Cloud:

1. Entrar a Community Cloud con la cuenta de GitHub dueña del repositorio y crear una app
   desde un repositorio existente.
2. Repositorio `donmatthiuz/RL`, rama `proyecto` y archivo principal `app/demo.py`.
3. En las opciones avanzadas, Python 3.12. Las dependencias salen de
   [`app/requirements.txt`](app/requirements.txt), que deja afuera torch y las librerías de RL.
4. Poner la URL en este apartado y marcar EVA-09 en el tablero.

## Reproducir un resultado

Guía de INF-10: alguien que no entrenó los agentes clona el repositorio y obtiene, con el modelo
publicado, el mismo resultado de PPO en val que el reporte. Toma unas 3 horas, casi todas de
descarga.

1. **Entorno:** clonar el repositorio en la rama `proyecto` y correr `make setup`.
2. **Datos:** seguir los pasos 1, 3, 4 y 5 de [docs/11_descarga_de_datos.md](docs/11_descarga_de_datos.md)
   (`make capture`, `make capture-spot`, `make manifest` y `make dataset`). Los trades y ETH no
   hacen falta. Al terminar, `data/processed/btc_updown_1h_v1/manifest.json` tiene que traer
   estos hashes:

   | Archivo | Filas | sha256 |
   | --- | --- | --- |
   | `markets.parquet` | 12 294 | `4a66bfea2ff0c776b664f685a294dc96ee6829b90f7419ca4d40c35888ad37e1` |
   | `prices_raw.parquet` | 2 945 766 | `954bd5d4546765c588e38ad4bbe3bcbb3cbd36313af263525ca8ef9bfe3a29e6` |
   | `spot_1m.parquet` | 750 000 | `e6cd2824b157b7d6300d22a49e787c4531cf4090ea56fbc481a1c2c6626cdbfe` |
   | `steps.parquet` | 737 640 | `d7153cf44875afaf33af16e50e908324513851aa3e71eec5f9fa7f5bbdd17c9b` |

3. **Modelo:** descargar `modelos-v1.0.zip` del Release `v1.0` del repositorio y descomprimirlo
   en `models/`. Queda, por ejemplo, `models/ppo/20261102-152322_ppo_pnl_risk_s0/`.
4. **Evaluar en val:**

   ```bash
   uv run polym4v evaluate --run models/ppo/20261102-152322_ppo_pnl_risk_s0 --split val
   ```

5. **Comparar:** el JSON que imprime tiene que dar `markets` 1861, `total_pnl` 77.99 y
   `mean_return` 0.002095, la fila de esa corrida en
   [reports/val/summary.csv](reports/val/summary.csv). Con los mismos hashes del paso 2 coincide
   exactamente; si algún hash difiere, se anota cuál y la diferencia del resultado.
6. **Registrar:** quién lo corrió, la fecha y lo obtenido, en la fila de INF-10 del
   [tablero](docs/04_tareas.md).

Test no se vuelve a evaluar (EVA-01): para reproducir se usa val.

## Mantenimiento de la documentación

- Los documentos son **vivos**: si cambia una decisión, el documento se actualiza en el mismo commit
  que introduce el cambio de código.
- Las decisiones importantes se registran como ADR en
  [`docs/07_riesgos_y_decisiones.md`](docs/07_riesgos_y_decisiones.md).
- La coherencia de `docs/` y de este README la mantiene el **Rol 1 — Líder técnico e integrador**.
