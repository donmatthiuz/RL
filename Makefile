# Catálogo de comandos del proyecto. `make help` lista todos.
# uv gestiona el entorno y las dependencias (ADR-006); este archivo cumple el rol de los
# "scripts" de un package.json: cada comando que se usa en el proyecto se ejecuta desde aquí,
# y la CI llama a los mismos targets.

UV ?= uv

# Configuración a validar: make config CONFIG=configs/data.yaml
CONFIG ?= configs/data.yaml

# Entrenamiento: make train AGENT=ppo SEED=0
AGENT ?= ppo
SEED ?=

# Backtest de un baseline: make backtest POLICY=fair_value SPLIT=train
POLICY ?= no_trade
SPLIT ?= train

# Captura del crudo: make capture SERIES=10114 (BTC horario) o SERIES=10117 (ETH horario)
SERIES ?= 10114
RAW_DIR ?= data/raw
PAUSE ?= 0.2

# Release (INF-09): make release-reportes TAG=v1.0 (la CI) y make release-modelos TAG=v1.0 (R1)
TAG ?= v1.0
MODELS_FINAL ?= models/final

# Entregables en PDF: make entregable ENTREGA=2026-10-30 PDF="Entregable 30.pdf"
ENTREGA ?= 2026-10-30
PDF ?= Entregable.pdf
# El PDF corre en un entorno aislado con las versiones fijas de la skill (no entra en uv.lock).
PDF_REQS := .skills/entregable-pdf/scripts/requirements.txt
FONT_DIR ?= .fonts-entregable
NOTO_DIR ?= /usr/share/fonts/truetype/noto
DEJAVU_DIR ?= /usr/share/fonts/truetype/dejavu

# Claves locales en keys/<nombre>.key. Para un servicio nuevo, agregar su nombre aquí.
KEYS := context7

.DEFAULT_GOAL := help
.PHONY: help setup install hooks keys-init lint format typecheck test coverage check \
	pre-commit config capture capture-spot capture-trades dataset backtest collect-offline train report behavior demo manifest entregable eda \
	release-reportes release-modelos

help: ## Lista los comandos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

## --- Entorno ---

setup: install hooks keys-init ## Prepara el entorno la primera vez (dependencias, hooks y claves)

install: ## Instala las versiones exactas de uv.lock (paquete y grupos dev y demo)
	$(UV) sync --locked

hooks: ## Activa los hooks de pre-commit en este clon
	$(UV) run pre-commit install

keys-init: ## Crea los archivos de claves vacíos en keys/ sin sobrescribir los existentes
	@mkdir -p keys
	@for k in $(KEYS); do \
		f="keys/$$k.key"; \
		if [ -e "$$f" ]; then \
			echo "$$f ya existe, no se modifica"; \
		else \
			: > "$$f"; chmod 600 "$$f"; \
			echo "$$f creado: pega la clave en una sola línea"; \
		fi; \
	done

## --- Calidad y tests ---

lint: ## Revisa estilo y formato sin modificar archivos
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Corrige estilo y formato
	$(UV) run ruff check . --fix
	$(UV) run ruff format .

typecheck: ## Revisa tipos con mypy
	$(UV) run mypy src/polym4v

test: ## Corre los tests rápidos (sin slow, network ni smoke)
	$(UV) run pytest

coverage: ## Corre los tests con cobertura (mínimo 70 %)
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=xml

.PHONY: smoke nightly
smoke: ## Entrena unos 2 000 pasos con cada config real de agente (job smoke-train de la CI)
	$(UV) run pytest -m smoke

nightly: ## Tests lentos y de las APIs reales (workflow nightly)
	$(UV) run pytest -m "slow or network"

check: lint typecheck coverage smoke ## Lo mismo que corre la CI

pre-commit: ## Corre todos los hooks sobre todo el repositorio
	$(UV) run pre-commit run --all-files

## --- Datos ---

config: ## Valida un YAML de configuración y lo muestra resuelto (CONFIG)
	$(UV) run polym4v config $(CONFIG)

capture: ## Archiva el historial crudo de una serie (SERIES, RAW_DIR, PAUSE)
	$(UV) run polym4v capture --series $(SERIES) --out $(RAW_DIR) --pause $(PAUSE)

capture-spot: ## Archiva las klines de Binance del activo y fechas de la config (CONFIG, RAW_DIR)
	$(UV) run polym4v capture-spot --config $(CONFIG) --out $(RAW_DIR)

capture-trades: ## Archiva los trades taker de val y test del dataset (CONFIG, RAW_DIR, PAUSE)
	$(UV) run polym4v capture-trades --config $(CONFIG) --out $(RAW_DIR) --pause $(PAUSE)

dataset: ## Construye markets, prices_raw y spot_1m desde el crudo (CONFIG, RAW_DIR)
	$(UV) run polym4v build-dataset --config $(CONFIG) --raw $(RAW_DIR)

backtest: ## Corre un baseline sobre un split y guarda sus trayectorias (POLICY, SPLIT)
	$(UV) run polym4v backtest --policy $(POLICY) --split $(SPLIT)

collect-offline: ## Recolecta el dataset offline de CQL y BC sobre train (AGENT=cql|bc)
	$(UV) run polym4v collect-offline --config configs/$(AGENT).yaml

train: ## Entrena un agente con todas las semillas de su config (AGENT=ppo|dqn|cql|bc, SEED)
	$(UV) run polym4v train --config configs/$(AGENT).yaml $(if $(SEED),--seed $(SEED))

report: ## Tabla y figuras de un split con las trayectorias y corridas ya calculadas (SPLIT)
	$(UV) run polym4v report --split $(SPLIT)

behavior: ## Comportamiento de los agentes en val y descripción de test, sin volver a evaluar test (EVA-12)
	OMP_NUM_THREADS=1 $(UV) run polym4v behavior --split val
	$(UV) run polym4v behavior --split test --allow-test

demo: ## Abre la demo de Streamlit con las trayectorias de reports/trajectories
	$(UV) run streamlit run app/demo.py

eda: ## Ejecuta el notebook de EDA sobre el dataset procesado (antes: make dataset)
	$(UV) run --group notebooks jupyter execute --inplace notebooks/eda/01_eda_btc_horario.ipynb

manifest: ## Recalcula el manifest con el hash de cada archivo crudo (RAW_DIR)
	$(UV) run polym4v manifest --out $(RAW_DIR)

## --- Release ---

release-reportes: ## Empaqueta reports/ y arma las notas del Release en dist/ (TAG)
	rm -rf dist && mkdir -p dist
	zip -qr dist/reportes-$(TAG).zip reports -x 'reports/trajectories/*'
	{ printf '%s\n\n' 'Tablas y figuras de val y test. Los modelos finales y las trayectorias se adjuntan con make release-modelos; cómo reproducir un resultado está en el README.'; \
	  cat reports/test/comparison.md; } > dist/notas-$(TAG).md

release-modelos: ## Sube al Release del tag los modelos finales y las trayectorias (TAG, MODELS_FINAL)
	gh release view $(TAG) > /dev/null
	mkdir -p dist
	rm -f dist/modelos-$(TAG).zip dist/trayectorias-$(TAG).zip
	cd $(MODELS_FINAL) && zip -qr $(CURDIR)/dist/modelos-$(TAG).zip */*/best.* */*/config.yaml */*/metrics.json
	zip -qj dist/trayectorias-$(TAG).zip reports/trajectories/*.parquet
	gh release upload $(TAG) dist/modelos-$(TAG).zip dist/trayectorias-$(TAG).zip --clobber

## --- Entregas ---

$(FONT_DIR)/.listo:
	mkdir -p $(FONT_DIR)
	ln -sf $(NOTO_DIR)/NotoSans-Regular.ttf $(NOTO_DIR)/NotoSans-Bold.ttf $(NOTO_DIR)/NotoSans-Italic.ttf $(DEJAVU_DIR)/DejaVuSansMono.ttf $(FONT_DIR)/
	touch $@

entregable: $(FONT_DIR)/.listo ## Genera el PDF de una entrega (ENTREGA, PDF)
	$(UV) run --no-project --with-requirements $(PDF_REQS) \
		python .skills/entregable-pdf/scripts/generar_pdf.py --root . \
		--content entregas/$(ENTREGA)/contenido.json --font-dir $(FONT_DIR) \
		--output "entregas/$(ENTREGA)/$(PDF)"
