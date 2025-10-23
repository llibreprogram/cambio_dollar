#!/usr/bin/env python3
"""
Script de validación para el empaquetado de Windows
Verifica que todos los archivos necesarios estén presentes y sean válidos.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Verificar que un archivo existe."""
    if file_path.exists():
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NO ENCONTRADO)")
        return False

def check_file_size(file_path, min_size_kb=100):
    """Verificar que un archivo tenga un tamaño mínimo."""
    if file_path.exists():
        size_kb = file_path.stat().st_size / 1024
        if size_kb >= min_size_kb:
            print(f"✓ Tamaño de {file_path.name}: {size_kb:.1f} KB")
            return True
        else:
            print(f"⚠️ Tamaño de {file_path.name}: {size_kb:.1f} KB (muy pequeño)")
            return False
    return False

def validate_executable(exe_path):
    """Validación básica del ejecutable."""
    if not exe_path.exists():
        return False

    # Verificar que sea un archivo ejecutable (básico)
    try:
        with open(exe_path, 'rb') as f:
            header = f.read(2)
            if header == b'MZ':  # Header de ejecutable Windows
                print(f"✓ {exe_path.name}: Header de ejecutable válido")
                return True
            else:
                print(f"⚠️ {exe_path.name}: Header no reconocido")
                return False
    except Exception as e:
        print(f"❌ Error al validar {exe_path.name}: {e}")
        return False

def main():
    """Función principal de validación."""
    print("🔍 Validando empaquetado de Windows para Cambio Dollar")
    print("=" * 60)

    project_root = Path(__file__).parent
    dist_dir = project_root / 'dist'

    all_good = True

    # Verificar archivos de construcción
    print("\n📁 Archivos de Construcción:")
    checks = [
        (project_root / 'build_windows.py', 'Script de construcción'),
        (project_root / '.env.windows', 'Archivo de configuración'),
        (project_root / 'installer.iss', 'Script de Inno Setup'),
        (project_root / 'cambio_dollar' / 'pyinstaller_hooks.py', 'Hooks de PyInstaller'),
    ]

    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_good = False

    # Verificar archivos generados
    print("\n📦 Archivos Generados:")
    generated_checks = [
        (dist_dir / 'cambio-dollar.exe', 'Ejecutable principal'),
        (dist_dir / 'run_server.bat', 'Script Batch'),
        (dist_dir / 'run_server.ps1', 'Script PowerShell'),
    ]

    for file_path, description in generated_checks:
        if check_file_exists(file_path, description):
            if file_path.suffix == '.exe':
                check_file_size(file_path, 10000)  # 10MB mínimo para ejecutable
                validate_executable(file_path)
        else:
            all_good = False

    # Verificar documentación
    print("\n📖 Documentación:")
    docs_checks = [
        (project_root / 'README_Windows.md', 'Guía de Windows'),
        (project_root / 'Windows_Installer_README.md', 'Documentación del instalador'),
    ]

    for file_path, description in docs_checks:
        if not check_file_exists(file_path, description):
            all_good = False

    # Verificar estructura del proyecto
    print("\n🏗️ Estructura del Proyecto:")
    if (project_root / 'cambio_dollar').exists():
        print("✓ Directorio cambio_dollar encontrado")
        cli_file = project_root / 'cambio_dollar' / 'cli.py'
        if check_file_exists(cli_file, 'Archivo CLI principal'):
            # Verificar que sea ejecutable
            try:
                # Solo verificar sintaxis básica
                with open(cli_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'def main' in content and 'if __name__' in content:
                        print("✓ Archivo CLI tiene estructura correcta")
                    else:
                        print("⚠️ Archivo CLI podría tener estructura incompleta")
                        all_good = False
            except Exception as e:
                print(f"❌ Error al validar CLI: {e}")
                all_good = False
        else:
            all_good = False
    else:
        print("❌ Directorio cambio_dollar no encontrado")
        all_good = False

    # Resumen final
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ¡Validación completada exitosamente!")
        print("\n🎉 El paquete de Windows está listo para distribución.")
        print("\n📋 Próximos pasos:")
        print("  1. Probar el ejecutable: dist\\cambio-dollar.exe --help")
        print("  2. Crear instalador MSI con Inno Setup")
        print("  3. Probar instalación en máquina limpia")
        return 0
    else:
        print("❌ Validación fallida. Corrija los problemas antes de distribuir.")
        print("\n🔧 Posibles soluciones:")
        print("  • Ejecute: python build_windows.py")
        print("  • Verifique que PyInstaller esté instalado")
        print("  • Revise logs de error en la consola")
        return 1

if __name__ == "__main__":
    sys.exit(main())