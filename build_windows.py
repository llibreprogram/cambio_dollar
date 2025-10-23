#!/usr/bin/env python3
# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

"""
Script de construcción para Windows - cambio_dollar
Crea un ejecutable standalone y scripts de ayuda para Windows.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Verificar que las herramientas necesarias estén instaladas."""
    print("🔍 Verificando requisitos...")

    # Verificar Python
    if sys.version_info < (3, 10):
        print("❌ Se requiere Python 3.10 o superior")
        return False

    # Verificar PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} encontrado")
    except ImportError:
        print("❌ PyInstaller no está instalado. Instale con: pip install pyinstaller")
        return False

    # Verificar Inno Setup (opcional)
    inno_setup_path = None
    common_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]

    for path in common_paths:
        if os.path.exists(path):
            inno_setup_path = path
            break

    if inno_setup_path:
        print(f"✓ Inno Setup encontrado: {inno_setup_path}")
    else:
        print("⚠️ Inno Setup no encontrado. Puede descargar desde: https://jrsoftware.org/isinfo.php")

    return True

def create_spec_file(project_root):
    """Crear archivo .spec para PyInstaller."""
    print("📝 Creando archivo .spec para PyInstaller...")

    # Crear archivo .spec para PyInstaller
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Configuración del proyecto
project_root = Path('{project_root}')
cambio_dollar_dir = project_root / 'cambio_dollar'

# Archivos de datos a incluir
datas = [
    # Templates HTML
    (str(cambio_dollar_dir / 'src' / 'cambio_dollar' / 'web' / 'templates'), 'cambio_dollar/web/templates'),
    # Archivos estáticos
    (str(cambio_dollar_dir / 'src' / 'cambio_dollar' / 'web' / 'static'), 'cambio_dollar/web/static'),
    # Archivo de configuración de ejemplo
    (str(project_root / '.env.windows'), '.'),
    # Hooks de PyInstaller
    (str(cambio_dollar_dir / 'pyinstaller_hooks.py'), '.'),
]

# Dependencias ocultas
hiddenimports = [
    'fastapi',
    'uvicorn',
    'sqlalchemy',
    'alembic',
    'pydantic',
    'apscheduler',
    'plotly',
    'rich',
    'httpx',
    'selectolax',
    'jinja2',
    'cambio_dollar',
    'cambio_dollar.cli',
    'cambio_dollar.web',
    'cambio_dollar.analytics',
    'cambio_dollar.config',
    'cambio_dollar.data_provider',
    'cambio_dollar.forecast',
    'cambio_dollar.models',
    'cambio_dollar.repository',
    'cambio_dollar.strategy',
]

# Exclusiones para reducir tamaño
excludes = [
    'tkinter',
    'matplotlib',
    'PIL',
    'numpy.testing',
    'pandas.tests',
    'pytest',
    'setuptools',
    'pip',
]

# Configuración del ejecutable
a = Analysis(
    ['cambio_dollar/src/cambio_dollar/cli.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cambio-dollar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''

    spec_file = project_root / 'cambio_dollar.spec'
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print(f"✓ Archivo .spec creado: {spec_file}")

def build_executable(project_root):
    """Construir el ejecutable con PyInstaller."""
    print("🔨 Construyendo ejecutable con PyInstaller...")

    # Ejecutar PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'cambio_dollar.spec'
    ]

    try:
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Ejecutable creado exitosamente")
            print(f"   Ubicación: {project_root / 'dist' / 'cambio-dollar.exe'}")
            return True
        else:
            print("❌ Error al crear el ejecutable:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error ejecutando PyInstaller: {e}")
        return False

def create_batch_script(project_root):
    """Crear script batch para ejecutar el servidor."""
    print("📄 Creando script batch...")

    batch_content = '''@echo off
REM Script para ejecutar el servidor cambio_dollar en Windows
REM Este script inicia el servidor web en segundo plano

echo ========================================
echo   CAMBIO DOLLAR - Servidor Web
echo ========================================
echo.

REM Verificar si el ejecutable existe
if not exist "cambio-dollar.exe" (
    echo ERROR: No se encuentra cambio-dollar.exe
    echo Ejecute primero: python build_windows.py
    pause
    exit /b 1
)

echo Iniciando servidor...
echo Presione Ctrl+C para detener el servidor
echo.

REM Ejecutar el servidor
cambio-dollar.exe web --host 0.0.0.0 --port 8000

pause
'''

    batch_file = project_root / 'dist' / 'run_server.bat'
    with open(batch_file, 'w', encoding='utf-8') as f:
        f.write(batch_content)

    print(f"✓ Script batch creado: {batch_file}")

def create_powershell_script(project_root):
    """Crear script PowerShell para ejecutar el servidor."""
    print("📄 Creando script PowerShell...")

    ps_content = '''# Script para ejecutar el servidor cambio_dollar en Windows
# Este script inicia el servidor web con opciones avanzadas

param(
    [int]$Port = 8000,
    [string]$Host = "0.0.0.0",
    [switch]$NoBrowser,
    [switch]$Verbose
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CAMBIO DOLLAR - Servidor Web" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si el ejecutable existe
$exePath = Join-Path $PSScriptRoot "cambio-dollar.exe"
if (-not (Test-Path $exePath)) {{
    Write-Host "ERROR: No se encuentra cambio-dollar.exe" -ForegroundColor Red
    Write-Host "Ejecute primero: python build_windows.py" -ForegroundColor Yellow
    Read-Host "Presione Enter para continuar"
    exit 1
}}

# Construir comando
$cmd = @($exePath, "web", "--host", $Host, "--port", $Port.ToString())

if ($Verbose) {{
    $cmd += "--verbose"
}}

Write-Host "Iniciando servidor en http://$Host`:$Port" -ForegroundColor Green
Write-Host "Presione Ctrl+C para detener el servidor" -ForegroundColor Yellow
Write-Host ""

try {{
    # Ejecutar el servidor
    & $cmd[0] $cmd[1..($cmd.Length-1)]

    # Abrir navegador si no se especificó -NoBrowser
    if (-not $NoBrowser) {{
        Start-Process "http://localhost:$Port"
    }}
}} catch {{
    Write-Host "Error al ejecutar el servidor: $($_.Exception.Message)" -ForegroundColor Red
}} finally {{
    Write-Host ""
    Write-Host "Servidor detenido." -ForegroundColor Yellow
    Read-Host "Presione Enter para continuar"
}}
'''

    ps_file = project_root / 'dist' / 'run_server.ps1'
    with open(ps_file, 'w', encoding='utf-8') as f:
        f.write(ps_content)

    print(f"✓ Script PowerShell creado: {ps_file}")

def create_inno_setup_script(project_root):
    """Crear script para Inno Setup."""
    print("📦 Creando script de Inno Setup...")

    inno_content = f'''#define MyAppName "Cambio Dollar"
#define MyAppVersion "1.0"
#define MyAppPublisher "Tu Nombre"
#define MyAppURL "https://github.com/tu-usuario/cambio-dollar"
#define MyAppExeName "cambio-dollar.exe"

[Setup]
AppId={{{{#MyAppName}}}}
AppName={{{{#MyAppName}}}}
AppVersion={{{{#MyAppVersion}}}}
AppPublisher={{{{#MyAppPublisher}}}}
AppPublisherURL={{{{#MyAppURL}}}}
AppSupportURL={{{{#MyAppURL}}}}
AppUpdatesURL={{{{#MyAppURL}}}}
DefaultDirName={{pf}}\\{{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir={project_root}\\installer
OutputBaseFilename=cambio-dollar-setup
SetupIconFile=
Compression=lzma
SolidCompression=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{project_root}\\dist\\cambio-dollar.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{project_root}\\dist\\run_server.bat"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{project_root}\\dist\\run_server.ps1"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{project_root}\\.env.windows"; DestDir: "{{app}}"; DestName: ".env"; Flags: ignoreversion

[Icons]
Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
'''

    inno_file = project_root / 'installer.iss'
    with open(inno_file, 'w', encoding='utf-8') as f:
        f.write(inno_content)

    print(f"✓ Script Inno Setup creado: {inno_file}")
    print("   Para crear el instalador, ejecute: ISCC.exe installer.iss")

def copy_config_file(project_root):
    """Copiar archivo de configuración de ejemplo."""
    print("⚙️ Copiando archivo de configuración...")

    src = project_root / '.env'
    dst = project_root / '.env.windows'

    if src.exists():
        shutil.copy2(src, dst)
        print(f"✓ Archivo de configuración copiado: {dst}")
    else:
        # Crear archivo básico si no existe
        config_content = '''# Configuración para Windows
# Copie este archivo como .env y ajuste los valores según sea necesario

# Puerto del servidor web
PORT=8000

# Host del servidor (0.0.0.0 para todas las interfaces)
HOST=0.0.0.0

# Nivel de logging
LOG_LEVEL=INFO

# Base de datos SQLite
DATABASE_URL=sqlite:///cambio_dollar.db

# Configuración de scraping
SCRAPE_INTERVAL_MINUTES=30

# Configuración de forecast
FORECAST_DAYS=7
'''
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"✓ Archivo de configuración creado: {dst}")

def main():
    """Función principal."""
    print("🚀 Iniciando construcción para Windows...")
    print("=" * 50)

    project_root = Path(__file__).parent

    # Verificar requisitos
    if not check_requirements():
        return 1

    try:
        # Copiar configuración
        copy_config_file(project_root)

        # Crear archivo .spec
        create_spec_file(project_root)

        # Construir ejecutable
        if not build_executable(project_root):
            return 1

        # Crear scripts de ayuda
        create_batch_script(project_root)
        create_powershell_script(project_root)

        # Crear script de Inno Setup
        create_inno_setup_script(project_root)

        print("\n" + "=" * 50)
        print("✅ ¡Construcción completada exitosamente!")
        print("=" * 50)
        print("\nArchivos generados:")
        print(f"  • Ejecutable: {project_root / 'dist' / 'cambio-dollar.exe'}")
        print(f"  • Script Batch: {project_root / 'dist' / 'run_server.bat'}")
        print(f"  • Script PowerShell: {project_root / 'dist' / 'run_server.ps1'}")
        print(f"  • Script Inno Setup: {project_root / 'installer.iss'}")
        print("\nPara crear el instalador MSI:")
        print("  1. Instale Inno Setup desde https://jrsoftware.org/isinfo.php")
        print("  2. Ejecute: ISCC.exe installer.iss")
        print("\nPara ejecutar la aplicación:")
        print("  • Doble clic en run_server.bat")
        print("  • O ejecute: .\\run_server.ps1")

        return 0

    except Exception as e:
        print(f"❌ Error durante la construcción: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
