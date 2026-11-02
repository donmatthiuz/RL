# Catálogo de comandos del proyecto. `make help` lista todos.
# uv gestiona el entorno y las dependencias (ADR-006); este archivo cumple el rol de los
# "scripts" de un package.json: cada comando que se usa en el proyecto se ejecuta desde aquí,
# y la CI llama a los mismos targets.

UV ?= uv

# Configuración a validar: make config CONFIG=configs/data.yaml
CONFIG ?= configs/data.yaml

# Captura del crudo: make capture SERIES=10114 (BTC horario) o SERIES=10117 (ETH horario)
SERIES ?= 10114
RAW_DIR ?= data/raw
PAUSE ?= 0.2

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
	pre-commit config capture capture-spot dataset eda manifest entregable

help: ## Lista los comandos disponibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

## --- Entorno ---

setup: install hooks keys-init ## Prepara el entorno la primera vez (dependencias, hooks y claves)

install: ## Instala las versiones exactas de uv.lock (paquete y grupo dev)
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

test: ## Corre los tests rápidos (sin slow ni network)
	$(UV) run pytest

coverage: ## Corre los tests con cobertura (mínimo 70 %)
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=xml

check: lint typecheck coverage ## Lo mismo que corre la CI

pre-commit: ## Corre todos los hooks sobre todo el repositorio
	$(UV) run pre-commit run --all-files

## --- Datos ---

config: ## Valida un YAML de configuración y lo muestra resuelto (CONFIG)
	$(UV) run polym4v config $(CONFIG)

capture: ## Archiva el historial crudo de una serie (SERIES, RAW_DIR, PAUSE)
	$(UV) run polym4v capture --series $(SERIES) --out $(RAW_DIR) --pause $(PAUSE)

capture-spot: ## Archiva las klines de Binance del activo y fechas de la config (CONFIG, RAW_DIR)
	$(UV) run polym4v capture-spot --config $(CONFIG) --out $(RAW_DIR)

dataset: ## Construye markets, prices_raw y spot_1m desde el crudo (CONFIG, RAW_DIR)
	$(UV) run polym4v build-dataset --config $(CONFIG) --raw $(RAW_DIR)

eda: ## Ejecuta el notebook de EDA sobre el dataset procesado (antes: make dataset)
	$(UV) run --group notebooks jupyter execute --inplace notebooks/eda/01_eda_btc_horario.ipynb

manifest: ## Recalcula el manifest con el hash de cada archivo crudo (RAW_DIR)
	$(UV) run polym4v manifest --out $(RAW_DIR)

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
