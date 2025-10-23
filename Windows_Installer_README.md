# Instalador Windows - Cambio Dollar

## 📦 Paquete Completo de Instalación para Windows

Este directorio contiene todos los archivos necesarios para crear un instalador profesional de Windows para la aplicación Cambio Dollar.

## 📁 Archivos Incluidos

### Scripts de Construcción
- **`build_windows.py`** - Script principal de construcción que:
  - Verifica requisitos (Python 3.10+, PyInstaller)
  - Crea ejecutable standalone con PyInstaller
  - Genera scripts de ayuda (Batch y PowerShell)
  - Crea script de Inno Setup para instalador MSI

### Configuración
- **`.env.windows`** - Archivo de configuración optimizado para Windows
- **`cambio_dollar/pyinstaller_hooks.py`** - Hooks de PyInstaller con todas las dependencias ocultas

### Scripts de Ejecución
- **`run_server.ps1`** - Script PowerShell avanzado con opciones:
  - Configuración de puerto y host
  - Modo verbose y debug
  - Apertura automática del navegador
  - Manejo de errores mejorado

### Instalador
- **`installer.iss`** - Script de Inno Setup que crea:
  - Instalador MSI profesional
  - Accesos directos en escritorio y menú inicio
  - Asociación de archivos
  - Página de configuración durante instalación
  - Desinstalador completo

### Documentación
- **`README_Windows.md`** - Guía completa para usuarios de Windows
- **`Makefile`** - Incluye target `make build-windows`

## 🚀 Cómo Crear el Instalador

### Prerrequisitos
1. **Python 3.10+** con todas las dependencias instaladas
2. **PyInstaller** instalado: `pip install pyinstaller`
3. **Inno Setup** descargado desde https://jrsoftware.org/isinfo.php

### Pasos de Construcción

#### Opción 1: Usando el Script de Construcción
```bash
python build_windows.py
```

#### Opción 2: Usando Make
```bash
make build-windows
```

#### Opción 3: Manual
```bash
# 1. Crear ejecutable
pyinstaller cambio_dollar.spec

# 2. Copiar archivos de configuración
cp .env.windows dist/

# 3. Crear scripts de ayuda
# (Los scripts se generan automáticamente)
```

### Crear Instalador MSI
```cmd
# Usando Inno Setup Compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## 📂 Estructura Final

Después de la construcción, se generan:

```
dist/
├── cambio-dollar.exe          # Ejecutable principal
├── run_server.bat           # Script batch simple
├── run_server.ps1           # Script PowerShell avanzado
└── .env                      # Configuración

installer/
└── cambio-dollar-setup-1.0.exe  # Instalador MSI
```

## 🎯 Características del Instalador

### Instalador MSI
- **Profesional**: Creado con Inno Setup (estándar de la industria)
- **Configurable**: Página de configuración durante instalación
- **Completo**: Incluye desinstalador, accesos directos, asociaciones de archivos
- **Multilingüe**: Soporte para inglés y español

### Ejecutable Standalone
- **Independiente**: No requiere instalación de Python
- **Completo**: Incluye todas las dependencias empaquetadas
- **Optimizado**: Comprimido con UPX para menor tamaño
- **Multiplataforma**: Funciona en Windows 7+ (x64)

### Scripts de Ejecución
- **Batch**: Para usuarios básicos
- **PowerShell**: Para usuarios avanzados con opciones completas
- **Inteligente**: Detección automática de problemas
- **User-friendly**: Mensajes claros y manejo de errores

## 🔧 Configuración Recomendada

### Para Desarrollo
```env
PORT=8000
HOST=127.0.0.1
LOG_LEVEL=DEBUG
```

### Para Producción
```env
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO
```

## 📊 Tamaño del Paquete

- **Ejecutable**: ~50-80MB (depende de dependencias)
- **Instalador**: ~60-90MB (incluye ejecutable + overhead)
- **Archivos adicionales**: ~1MB (scripts y documentación)

## 🐛 Solución de Problemas

### PyInstaller Falla
- Verificar que todas las dependencias estén instaladas
- Revisar el archivo `pyinstaller_hooks.py` para dependencias faltantes
- Ejecutar con `--debug=all` para más información

### Instalador no se Crea
- Verificar que Inno Setup esté instalado correctamente
- Revisar rutas en `installer.iss`
- Ejecutar ISCC.exe desde línea de comandos

### Ejecutable no Funciona
- Verificar que se ejecuta desde la carpeta correcta
- Revisar permisos de archivos
- Verificar que no falten archivos empaquetados

## 🔄 Actualizaciones

Para nuevas versiones:
1. Actualizar `MyAppVersion` en `installer.iss`
2. Modificar archivos de configuración si es necesario
3. Reconstruir ejecutable y instalador
4. Probar instalación en máquina limpia

## 📞 Soporte

Para problemas específicos de Windows:
- Verificar `README_Windows.md` para guías detalladas
- Revisar logs de PyInstaller en `build/` y `dist/`
- Probar scripts individualmente antes del empaquetado

---

**Versión del Paquete**: 1.0
**Compatible con**: Windows 7+ (x64)
**Requiere**: Python 3.10+, PyInstaller, Inno Setup