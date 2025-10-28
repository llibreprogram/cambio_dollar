VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(PYTHON) -m pip
APP := $(VENV)/bin/cambio-dollar
MARKER := $(VENV)/.bootstrap-complete

.PHONY: help bootstrap serve fetch analyze forecast compare providers history trade drift capture test migrate revision clean build-windows

help:
	@echo "Targets disponibles:"
	@echo "  make bootstrap      -> Crea el entorno virtual e instala dependencias"
	@echo "  make serve          -> Inicia la API y el dashboard web"
	@echo "  make fetch          -> Captura cotizaciones manualmente"
	@echo "  make analyze        -> Genera recomendación de estrategia"
	@echo "  make forecast       -> Proyecta la utilidad al cierre del día"
	@echo "  make compare        -> Compara la última captura entre proveedores"
	@echo "  make providers      -> Lista proveedores configurados"
	@echo "  make history        -> Muestra historial de operaciones"
	@echo "  make trade          -> Registra una operación manual (requiere: action, amount, rate)"
	@echo "  make drift          -> Muestra eventos de drift detectados"
	@echo "  make test           -> Ejecuta la suite de pruebas"
	@echo "  make migrate        -> Aplica las migraciones Alembic al SQLite configurado"
	@echo "  make revision       -> Crea una nueva migración Alembic (usa message=...)"
	@echo "  make build-windows  -> Construye instalador para Windows (requiere PyInstaller e Inno Setup)"
	@echo "  make clean          -> Borra artefactos temporales"

$(VENV)/bin/python:
	python3 -m venv $(VENV)

$(MARKER): $(VENV)/bin/python pyproject.toml
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	touch $(MARKER)

bootstrap: $(MARKER)
	@echo "Entorno listo en $(VENV)"

$(APP): $(MARKER)

serve: $(APP)
	$(APP) serve --host 0.0.0.0 --port 8000

fetch: $(APP)
	$(APP) fetch

analyze: $(APP)
	$(APP) analyze

forecast: $(APP)
	$(APP) forecast

compare: $(APP)
	$(APP) compare

providers: $(APP)
	$(APP) providers

history: $(APP)
	$(APP) history

trade: $(APP)
	@if [ -z "$(action)" ] || [ -z "$(amount)" ]; then \
		echo "Uso: make trade action=<buy|sell> amount=<USD> [rate=<DOP>] [fees=<DOP>]"; \
		echo "Ejemplo: make trade action=sell amount=500 rate=58.4 fees=50"; \
		exit 1; \
	fi
	@if [ -n "$(rate)" ] && [ -n "$(fees)" ]; then \
		$(APP) trade $(action) $(amount) --rate $(rate) --fees $(fees); \
	elif [ -n "$(rate)" ]; then \
		$(APP) trade $(action) $(amount) --rate $(rate); \
	elif [ -n "$(fees)" ]; then \
		$(APP) trade $(action) $(amount) --fees $(fees); \
	else \
		$(APP) trade $(action) $(amount); \
	fi

drift: $(APP)
	$(APP) drift

capture: fetch

test: $(MARKER)
	$(PYTHON) -m pytest

migrate: $(MARKER)
	$(PYTHON) -m cambio_dollar.db_migrations upgrade

revision: $(MARKER)
	@if [ -z "$(message)" ]; then \
		echo "Uso: make revision message=\"Agregar nueva migración\""; \
		exit 1; \
	fi
	$(PYTHON) -m cambio_dollar.db_migrations revision "$(message)"

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .coverage dist build *.spec installer.iss

build-windows: $(MARKER)
	@echo "Construyendo instalador para Windows..."
	$(PIP) install pyinstaller
	$(PYTHON) build_windows.py
	@echo ""
	@echo "Para crear el instalador completo:"
	@echo "1. Instala Inno Setup desde https://jrsoftware.org/isinfo.php"
	@echo "2. Ejecuta el archivo installer.iss con Inno Setup Compiler"
	@echo "3. El instalador se creará en la carpeta 'installer/'"
