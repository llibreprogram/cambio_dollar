#!/usr/bin/env python3
"""
Script para empaquetar la aplicación Cambio Dollar para Windows usando PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Ejecuta un comando y retorna True si fue exitoso."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando comando: {cmd}")
        print(f"Salida de error: {e.stderr}")
        return False

def create_spec_file():
    """Crea el archivo .spec para PyInstaller."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Obtener el directorio base del proyecto
base_dir = Path(__file__).parent

# Configurar rutas para archivos estáticos y templates
static_dir = base_dir / "src" / "cambio_dollar" / "web" / "static"
templates_dir = base_dir / "src" / "cambio_dollar" / "web" / "templates"

a = Analysis(
    ['src/cambio_dollar/cli.py'],
    pathex=[str(base_dir)],
    binaries=[],
    datas=[
        (str(static_dir), 'cambio_dollar/web/static'),
        (str(templates_dir), 'cambio_dollar/web/templates'),
    ],
    hiddenimports=[
        'cambio_dollar.web.app',
        'cambio_dollar.web.routes',
        'cambio_dollar.analytics',
        'cambio_dollar.config',
        'cambio_dollar.data_provider',
        'cambio_dollar.forecast',
        'cambio_dollar.logging_utils',
        'cambio_dollar.models',
        'cambio_dollar.repository',
        'cambio_dollar.strategy',
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'apscheduler.schedulers.asyncio',
        'apscheduler.jobstores.memory',
        'apscheduler.executors.asyncio',
        'sqlalchemy.ext.declarative',
        'pydantic.v1',
        'pydantic.v1.fields',
        'pydantic.v1.main',
        'pydantic.v1.types',
        'plotly.graph_objects',
        'plotly.subplots',
        'plotly.offline',
        'selectolax.parser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'numpy.testing',
        'pandas.tests',
        'pytest',
        'setuptools',
        'pip',
        'wheel',
        'distutils',
    ],
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
    icon=None,  # Puedes agregar un ícono aquí si tienes uno
)
'''

    with open('cambio_dollar.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print("Archivo cambio_dollar.spec creado.")

def build_executable():
    """Construye el ejecutable usando PyInstaller."""
    print("Construyendo ejecutable con PyInstaller...")

    # Crear el archivo .spec
    create_spec_file()

    # Ejecutar PyInstaller
    if run_command('pyinstaller --clean cambio_dollar.spec'):
        print("Ejecutable construido exitosamente.")
        return True
    else:
        print("Error al construir el ejecutable.")
        return False

def create_installer_script():
    """Crea el script de Inno Setup para el instalador."""
    installer_script = '''#define MyAppName "Cambio Dollar"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Tu Nombre"
#define MyAppURL "https://github.com/llibreprogram/cambio_dollar"
#define MyAppExeName "cambio-dollar.exe"

[Setup]
AppId={{12345678-1234-1234-1234-123456789ABC}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=cambio-dollar-setup-{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\cambio-dollar.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    // Crear acceso directo en el escritorio si fue seleccionado
    if WizardForm.TasksList.Checked[1] then begin
      CreateShellLink(
        ExpandConstant('{commondesktop}\{#MyAppName}.lnk'),
        '{#MyAppName}',
        ExpandConstant('{app}\{#MyAppExeName}'),
        '',
        ExpandConstant('{app}'),
        '',
        SW_SHOWNORMAL,
        'icon.ico'
      );
    end;
  end;
end;
'''

    with open('installer.iss', 'w', encoding='utf-8') as f:
        f.write(installer_script)

    print("Script de instalador Inno Setup creado (installer.iss).")

def create_batch_scripts():
    """Crea scripts batch para facilitar el uso en Windows."""
    # Script para ejecutar el servidor
    run_server = '''@echo off
echo Iniciando Cambio Dollar...
echo.
echo El servidor web se iniciara en http://localhost:8000
echo Presiona Ctrl+C para detener el servidor
echo.
"cambio-dollar.exe" serve
pause
'''

    # Script para ejecutar comandos CLI
    cli_help = '''@echo off
echo Cambio Dollar - Comandos disponibles:
echo.
echo cambio-dollar fetch          - Capturar datos del mercado
echo cambio-dollar analyze        - Generar recomendacion de trading
echo cambio-dollar forecast       - Pronosticar ganancia del dia
echo cambio-dollar trade ACTION USD_AMOUNT - Registrar operacion
echo cambio-dollar history        - Ver historial de operaciones
echo cambio-dollar providers      - Listar proveedores configurados
echo cambio-dollar serve          - Iniciar servidor web
echo.
echo Ejemplos:
echo cambio-dollar fetch --repetitions 3 --interval 60
echo cambio-dollar trade buy 500 --rate 58.50
echo.
pause
'''

    with open('dist/run_server.bat', 'w', encoding='utf-8') as f:
        f.write(run_server)

    with open('dist/cli_help.bat', 'w', encoding='utf-8') as f:
        f.write(cli_help)

    print("Scripts batch creados en dist/")

def create_powershell_scripts():
    """Crea scripts de PowerShell para Windows."""
    # Copiar el archivo run_server.ps1 al directorio dist
    import shutil
    if Path('run_server.ps1').exists():
        shutil.copy('run_server.ps1', 'dist/run_server.ps1')
        print("Script de PowerShell copiado a dist/")

    print("Scripts de PowerShell creados en dist/")

def main():
    """Función principal."""
    print("=== Empaquetador de Cambio Dollar para Windows ===\n")

    # Verificar que estamos en el directorio correcto
    if not Path('pyproject.toml').exists():
        print("Error: Ejecuta este script desde el directorio raiz del proyecto (donde esta pyproject.toml)")
        sys.exit(1)

    # Verificar que PyInstaller esté instalado
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller no esta instalado. Instalandolo...")
        if not run_command('pip install pyinstaller'):
            print("Error al instalar PyInstaller. Instálalo manualmente con: pip install pyinstaller")
            sys.exit(1)

    # Crear directorio dist si no existe
    Path('dist').mkdir(exist_ok=True)

    # Construir el ejecutable
    if not build_executable():
        sys.exit(1)

    # Crear scripts auxiliares
    create_batch_scripts()
    create_powershell_scripts()

    # Crear script de instalador
    create_installer_script()

    print("\n=== Empaquetado completado ===")
    print("Archivos generados:")
    print("- dist/cambio-dollar.exe (ejecutable principal)")
    print("- dist/run_server.bat (script para iniciar servidor)")
    print("- dist/cli_help.bat (ayuda de comandos)")
    print("- installer.iss (script para Inno Setup)")
    print("- cambio_dollar.spec (configuracion de PyInstaller)")
    print("\nPara crear el instalador:")
    print("1. Descarga e instala Inno Setup desde https://jrsoftware.org/isinfo.php")
    print("2. Ejecuta el script installer.iss con Inno Setup Compiler")
    print("3. El instalador se creara en la carpeta 'installer/'")

if __name__ == '__main__':
    main()