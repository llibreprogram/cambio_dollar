# Makefile para Cambio Dollar

.PHONY: help install dev-install test lint format clean build build-windows docs

# Variables
PYTHON := python
PIP := pip
PROJECT_NAME := cambio_dollar

# Colores para output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Target por defecto
help:
	@echo "$(GREEN)Cambio Dollar - Comandos disponibles:$(NC)"
	@echo ""
	@echo "$(YELLOW)Instalación:$(NC)"
	@echo "  install       Instalar dependencias de producción"
	@echo "  dev-install   Instalar dependencias de desarrollo"
	@echo ""
	@echo "$(YELLOW)Desarrollo:$(NC)"
	@echo "  test          Ejecutar tests"
	@echo "  lint          Ejecutar linter (flake8)"
	@echo "  format        Formatear código (black)"
	@echo ""
	@echo "$(YELLOW)Construcción:$(NC)"
	@echo "  build         Construir paquete Python"
	@echo "  build-windows Crear ejecutable e instalador para Windows"
	@echo ""
	@echo "$(YELLOW)Utilidades:$(NC)"
	@echo "  clean         Limpiar archivos temporales"
	@echo "  docs          Generar documentación"
	@echo "  help          Mostrar esta ayuda"

# Instalación
install:
	@echo "$(GREEN)Instalando dependencias de producción...$(NC)"
	$(PIP) install -r requirements.txt

dev-install: install
	@echo "$(GREEN)Instalando dependencias de desarrollo...$(NC)"
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .

# Desarrollo
test:
	@echo "$(GREEN)Ejecutando tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v --cov=$(PROJECT_NAME) --cov-report=html

lint:
	@echo "$(GREEN)Ejecutando linter...$(NC)"
	$(PYTHON) -m flake8 $(PROJECT_NAME) tests/
	$(PYTHON) -m black --check $(PROJECT_NAME) tests/

format:
	@echo "$(GREEN)Formateando código...$(NC)"
	$(PYTHON) -m black $(PROJECT_NAME) tests/

# Construcción
build:
	@echo "$(GREEN)Construyendo paquete Python...$(NC)"
	$(PYTHON) setup.py sdist bdist_wheel

build-windows:
	@echo "$(GREEN)Construyendo ejecutable e instalador para Windows...$(NC)"
	@echo "$(YELLOW)Asegúrese de tener PyInstaller instalado:$(NC)"
	@echo "  pip install pyinstaller"
	@echo ""
	@echo "$(YELLOW)Para crear el instalador MSI, también necesita Inno Setup:$(NC)"
	@echo "  https://jrsoftware.org/isinfo.php"
	@echo ""
	$(PYTHON) build_windows.py

validate-windows: build-windows
	@echo "$(GREEN)Validando construcción de Windows...$(NC)"
	$(PYTHON) validate_windows_build.py

# Utilidades
clean:
	@echo "$(GREEN)Limpiando archivos temporales...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf */__pycache__/
	rm -rf *.spec
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +

docs:
	@echo "$(GREEN)Generando documentación...$(NC)"
	@echo "$(YELLOW)Documentación básica disponible en README.md$(NC)"
	@echo "$(YELLOW)Para documentación técnica, ejecute:$(NC)"
	@echo "  pip install sphinx"
	@echo "  sphinx-build docs/ docs/_build/html"

# Targets específicos de Windows
windows-setup: build-windows
	@echo "$(GREEN)Setup completado para Windows$(NC)"
	@echo "$(YELLOW)Archivos generados:$(NC)"
	@echo "  • dist/cambio-dollar.exe (ejecutable)"
	@echo "  • dist/run_server.bat (script simple)"
	@echo "  • dist/run_server.ps1 (script avanzado)"
	@echo "  • installer.iss (script para Inno Setup)"
	@echo ""
	@echo "$(YELLOW)Para crear el instalador MSI:$(NC)"
	@echo "  1. Instale Inno Setup"
	@echo "  2. Ejecute: ISCC.exe installer.iss"

# Verificación del entorno
check-env:
	@echo "$(GREEN)Verificando entorno...$(NC)"
	$(PYTHON) --version
	$(PIP) --version
	@echo ""
	@echo "$(YELLOW)Dependencias críticas:$(NC)"
	@python -c "import fastapi, uvicorn, sqlalchemy, plotly; print('✓ FastAPI, Uvicorn, SQLAlchemy, Plotly OK')" 2>/dev/null || echo "❌ Faltan dependencias críticas"

# Target para desarrollo local
dev: dev-install
	@echo "$(GREEN)Entorno de desarrollo configurado$(NC)"
	@echo "$(YELLOW)Para ejecutar la aplicación:$(NC)"
	@echo "  python -m cambio_dollar.cli web"