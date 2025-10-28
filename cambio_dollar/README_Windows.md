# Instalador de Cambio Dollar para Windows

Este documento explica cómo crear y usar el instalador de Cambio Dollar para Windows.

## Requisitos previos

### Para construir el instalador:
- Python 3.10 o superior
- Git
- Inno Setup (gratuito): https://jrsoftware.org/isinfo.php

### Para usar la aplicación:
- Windows 10 o superior
- Conexión a internet (para capturar datos del mercado)

## Construcción del instalador

### Paso 1: Preparar el entorno

```bash
# Clonar el repositorio
git clone https://github.com/llibreprogram/cambio_dollar.git
cd cambio_dollar

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -e .
pip install pyinstaller
```

### Paso 2: Construir el ejecutable

```bash
# Ejecutar el script de construcción
python build_windows.py
```

Esto creará:
- `dist/cambio-dollar.exe` - El ejecutable principal
- `installer.iss` - Script para Inno Setup
- Scripts auxiliares en `dist/`

### Paso 3: Crear el instalador

1. Descarga e instala [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Abre Inno Setup Compiler
3. Carga el archivo `installer.iss`
4. Compila el instalador

El instalador se creará en la carpeta `installer/` como `cambio-dollar-setup-0.1.0.exe`

## Instalación

1. Ejecuta `cambio-dollar-setup-0.1.0.exe`
2. Sigue el asistente de instalación
3. Elige la ubicación de instalación (por defecto: `C:\Program Files\Cambio Dollar`)
4. Opcionalmente crea accesos directos en el escritorio y menú inicio

## Uso de la aplicación

### Iniciar el servidor web

Después de la instalación, puedes:

1. **Desde el menú Inicio**: Busca "Cambio Dollar" y ejecuta
2. **Desde el escritorio**: Si creaste el acceso directo
3. **Desde línea de comandos**: Ejecuta `cambio-dollar.exe serve`

El servidor se iniciará en `http://localhost:8000`

### Comandos disponibles

La aplicación incluye una interfaz de línea de comandos completa:

```bash
# Capturar datos del mercado
cambio-dollar.exe fetch

# Generar recomendación de trading
cambio-dollar.exe analyze

# Ver pronóstico del día
cambio-dollar.exe forecast

# Registrar una operación
cambio-dollar.exe trade buy 500 --rate 58.50

# Ver historial
cambio-dollar.exe history

# Listar proveedores
cambio-dollar.exe providers

# Iniciar servidor web
cambio-dollar.exe serve
```

### Scripts auxiliares incluidos

- `run_server.bat` - Inicia el servidor web
- `cli_help.bat` - Muestra ayuda de comandos

## Configuración

La aplicación crea automáticamente una base de datos SQLite en la carpeta de datos del usuario.

Para configuraciones avanzadas, puedes crear un archivo `.env` en el directorio de instalación con:

```env
# Puerto del servidor (por defecto: 8000)
SERVER_PORT=8000

# Host del servidor (por defecto: localhost)
SERVER_HOST=localhost

# Nivel de logging
LOG_LEVEL=INFO

# Intervalo del scheduler en segundos
SCHEDULER_INTERVAL_SECONDS=300
```

## Solución de problemas

### El ejecutable no se inicia
- Asegúrate de tener Microsoft Visual C++ Redistributable instalado
- Verifica que no haya antivirus bloqueando la aplicación

### Error de conexión
- La aplicación necesita internet para capturar datos del mercado
- Verifica tu conexión a internet

### Puerto ocupado
- Si el puerto 8000 está ocupado, cambia el puerto en la configuración
- O usa: `cambio-dollar.exe serve --port 8001`

### Base de datos corrupta
- Elimina el archivo `cambio_dollar.db` en la carpeta de datos
- La aplicación creará una nueva base de datos automáticamente

## Desarrollo

Para modificar la aplicación:

1. Clona el repositorio
2. Instala en modo desarrollo: `pip install -e .`
3. Para empaquetar: `python build_windows.py`

## Soporte

Si encuentras problemas:
1. Revisa los logs en la consola
2. Verifica la configuración
3. Consulta la documentación en el repositorio

---
**Versión**: 0.1.0
**Plataforma**: Windows 10+
**Python**: 3.10+</content>
<parameter name="filePath">/home/llibre/cambio_dollar_final/cambio_dollar/README_WINDOWS.md