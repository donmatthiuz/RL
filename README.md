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

Las notas de trabajo están en [`docs/notas/`](docs/notas/): el
[spike de datos](docs/notas/spike_datos.md), las
[decisiones previas al diseño](docs/notas/decisiones_previas_al_diseno.md) y el
[uso de IA](docs/notas/uso_de_ia.md) (skills y subagentes del proyecto, y por qué se usa cada uno).

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

# Generar el PDF de una entrega
make entregable ENTREGA=2026-10-30 PDF="Entregable 30.pdf"
```

> Los comandos de dataset, entrenamiento, evaluación y demo se agregan al `Makefile` a medida que
> avanzan las tareas de [`docs/04_tareas.md`](docs/04_tareas.md).

## Mantenimiento de la documentación

- Los documentos son **vivos**: si cambia una decisión, el documento se actualiza en el mismo commit
  que introduce el cambio de código.
- Las decisiones importantes se registran como ADR en
  [`docs/07_riesgos_y_decisiones.md`](docs/07_riesgos_y_decisiones.md).
- La coherencia de `docs/` y de este README la mantiene el **Rol 1 — Líder técnico e integrador**.
