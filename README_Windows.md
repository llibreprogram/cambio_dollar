# Cambio Dollar - Instalación y Uso en Windows

Esta guía explica cómo instalar y usar la aplicación Cambio Dollar en sistemas Windows.

## 📋 Requisitos del Sistema

- **Sistema Operativo**: Windows 10 o superior
- **Arquitectura**: x64 (64-bit)
- **Memoria RAM**: Mínimo 4GB recomendado
- **Espacio en Disco**: 500MB libres para la instalación

## 🚀 Instalación

### Opción 1: Instalador MSI (Recomendado)

1. **Descargue el instalador**: `cambio-dollar-setup.exe`
2. **Ejecute el instalador** como administrador
3. **Siga las instrucciones** del asistente de instalación
4. **Complete la instalación** - se crearán accesos directos en el escritorio y menú inicio

### Opción 2: Archivo Ejecutable Portátil

1. **Descargue el archivo**: `cambio-dollar.exe`
2. **Extraiga** el archivo en una carpeta de su elección
3. **Copie** el archivo `.env` de ejemplo y configúrelo si es necesario

## ⚙️ Configuración

La aplicación incluye un archivo de configuración `.env` que puede personalizar:

```env
# Puerto del servidor web (por defecto: 8000)
PORT=8000

# Host del servidor (0.0.0.0 para todas las interfaces)
HOST=0.0.0.0

# Nivel de logging (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Base de datos SQLite
DATABASE_URL=sqlite:///cambio_dollar.db

# Intervalo de scraping en minutos
SCRAPE_INTERVAL_MINUTES=30

# Días para pronóstico
FORECAST_DAYS=7
```

## 🖥️ Uso de la Aplicación

### Inicio del Servidor

#### Método 1: Script Batch (Más Simple)
1. **Localice** el acceso directo en el escritorio o menú inicio
2. **Haga doble clic** en "Cambio Dollar"
3. **Espere** a que se abra la ventana de comandos
4. **Abra su navegador** en: `http://localhost:8000`

#### Método 2: Script PowerShell (Avanzado)
```powershell
# Desde PowerShell, navegue a la carpeta de instalación
cd "C:\\Program Files\\Cambio Dollar"

# Ejecute con opciones personalizadas
.\\run_server.ps1 -Port 8080 -Verbose
```

#### Método 3: Ejecutable Directo
```cmd
# Desde el símbolo del sistema
cambio-dollar.exe web --host 0.0.0.0 --port 8000
```

### Acceso a la Interfaz Web

Una vez iniciado el servidor, abra su navegador web y vaya a:

```
http://localhost:8000
```

La interfaz incluye:
- **Dashboard Principal**: Vista general de tasas de cambio
- **Gráficos Interactivos**: Visualización de tendencias
- **Pronósticos**: Predicciones futuras basadas en datos históricos
- **Configuración**: Ajustes de la aplicación

## 🔧 Solución de Problemas

### El Servidor no Inicia

**Síntoma**: Error al ejecutar el archivo batch o PowerShell
**Solución**:
1. Verifique que el archivo `cambio-dollar.exe` existe
2. Ejecute como administrador
3. Verifique que el puerto 8000 no esté en uso

```cmd
# Verificar puertos en uso
netstat -ano | findstr :8000
```

### Error de Puerto Ocupado

**Síntoma**: "Address already in use"
**Solución**: Cambie el puerto en la configuración

```powershell
# Ejecutar en puerto diferente
.\\run_server.ps1 -Port 8081
```

### Problemas de Conexión

**Síntoma**: No puede acceder desde otros dispositivos
**Solución**: Configure el host como 0.0.0.0

```env
HOST=0.0.0.0
```

### Base de Datos Corrupta

**Síntoma**: Errores de base de datos
**Solución**: Elimine el archivo de base de datos para recrearlo

```cmd
del cambio_dollar.db
```

## 📊 Características

- **Monitoreo en Tiempo Real**: Actualización automática de tasas
- **Interfaz Web Moderna**: Acceso desde cualquier dispositivo
- **Pronósticos Inteligentes**: Predicciones basadas en análisis
- **Base de Datos Embebida**: No requiere instalación de base de datos adicional
- **Configuración Flexible**: Personalización según necesidades

## 🔒 Seguridad

- La aplicación se ejecuta localmente en su equipo
- No envía datos a servidores externos (excepto para obtener tasas de cambio)
- Los datos se almacenan localmente en SQLite
- Puerto por defecto (8000) solo accesible desde el equipo local

## 🆘 Soporte

Si experimenta problemas:

1. **Verifique los logs**: Los mensajes de error aparecen en la consola
2. **Reinicie la aplicación**: Cierre y vuelva a abrir
3. **Verifique la configuración**: Asegúrese de que el archivo `.env` sea válido
4. **Reinstale si es necesario**: Use el instalador MSI para reparar

## 📝 Notas Técnicas

- **Arquitectura**: Aplicación Python empaquetada con PyInstaller
- **Base de Datos**: SQLite embebida (no requiere instalación)
- **Servidor Web**: Uvicorn con FastAPI
- **Interfaz**: HTML/CSS/JavaScript moderno
- **Dependencias**: Todas incluidas en el ejecutable

## 🔄 Actualizaciones

Para actualizar a una nueva versión:

1. **Descargue** la nueva versión del instalador
2. **Ejecute** el instalador (se actualizará automáticamente)
3. **Reinicie** la aplicación si es necesario

---

**Versión**: 1.0
**Plataforma**: Windows 10+
**Arquitectura**: x64