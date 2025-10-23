# Script PowerShell para ejecutar Cambio Dollar
# Versión avanzada con opciones de configuración

param(
    [Parameter(Mandatory=$false)]
    [int]$Port = 8000,

    [Parameter(Mandatory=$false)]
    [string]$Host = "0.0.0.0",

    [Parameter(Mandatory=$false)]
    [switch]$NoBrowser,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose,

    [Parameter(Mandatory=$false)]
    [switch]$Debug,

    [Parameter(Mandatory=$false)]
    [string]$ConfigFile = ".env",

    [Parameter(Mandatory=$false)]
    [switch]$Help
)

# Función para mostrar ayuda
function Show-Help {
    Write-Host "Cambio Dollar - Script de Ejecución PowerShell" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso:" -ForegroundColor Yellow
    Write-Host "  .\run_server.ps1 [opciones]" -ForegroundColor White
    Write-Host ""
    Write-Host "Opciones:" -ForegroundColor Yellow
    Write-Host "  -Port <número>       Puerto del servidor (por defecto: 8000)" -ForegroundColor White
    Write-Host "  -Host <dirección>    Host del servidor (por defecto: 0.0.0.0)" -ForegroundColor White
    Write-Host "  -NoBrowser          No abrir navegador automáticamente" -ForegroundColor White
    Write-Host "  -Verbose            Modo verbose con más información" -ForegroundColor White
    Write-Host "  -Debug              Modo debug con información detallada" -ForegroundColor White
    Write-Host "  -ConfigFile <ruta>  Archivo de configuración (por defecto: .env)" -ForegroundColor White
    Write-Host "  -Help               Mostrar esta ayuda" -ForegroundColor White
    Write-Host ""
    Write-Host "Ejemplos:" -ForegroundColor Yellow
    Write-Host "  .\run_server.ps1" -ForegroundColor White
    Write-Host "  .\run_server.ps1 -Port 8080 -Verbose" -ForegroundColor White
    Write-Host "  .\run_server.ps1 -Host 127.0.0.1 -NoBrowser" -ForegroundColor White
    Write-Host ""
}

# Mostrar ayuda si se solicita
if ($Help) {
    Show-Help
    exit 0
}

# Banner de inicio
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CAMBIO DOLLAR - Servidor Web" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si el ejecutable existe
$exePath = Join-Path $PSScriptRoot "cambio-dollar.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "ERROR: No se encuentra cambio-dollar.exe" -ForegroundColor Red
    Write-Host "Ejecute primero: python build_windows.py" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "O presione cualquier tecla para salir..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Verificar archivo de configuración
if ($ConfigFile -ne ".env" -and -not (Test-Path $ConfigFile)) {
    Write-Warning "Archivo de configuración '$ConfigFile' no encontrado. Usando configuración por defecto."
}

# Mostrar información del sistema
if ($Verbose -or $Debug) {
    Write-Host "Información del sistema:" -ForegroundColor Yellow
    Write-Host "  Ejecutable: $exePath" -ForegroundColor White
    Write-Host "  Puerto: $Port" -ForegroundColor White
    Write-Host "  Host: $Host" -ForegroundColor White
    Write-Host "  Configuración: $ConfigFile" -ForegroundColor White
    Write-Host "  Modo debug: $($Debug.ToString())" -ForegroundColor White
    Write-Host ""
}

# Verificar si el puerto está en uso
$portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Warning "El puerto $Port ya está en uso. El servidor podría fallar al iniciar."
    Write-Host ""
}

# Construir comando
$cmdArgs = @(
    "web",
    "--host", $Host,
    "--port", $Port.ToString()
)

# Agregar opciones adicionales
if ($Debug) {
    $cmdArgs += "--verbose"
    $env:PYTHONVERBOSE = "1"
}

if ($Verbose) {
    Write-Host "Comando a ejecutar:" -ForegroundColor Yellow
    Write-Host "  cambio-dollar.exe $($cmdArgs -join ' ')" -ForegroundColor White
    Write-Host ""
}

# URL del servidor
$serverUrl = "http://localhost:$Port"
if ($Host -ne "127.0.0.1" -and $Host -ne "localhost") {
    $serverUrl = "http://$Host`:$Port"
}

Write-Host "Iniciando servidor en $serverUrl" -ForegroundColor Green
Write-Host "Presione Ctrl+C para detener el servidor" -ForegroundColor Yellow
Write-Host ""

try {
    # Ejecutar el servidor
    & $exePath @cmdArgs

    # Abrir navegador si no se especificó -NoBrowser
    if (-not $NoBrowser) {
        Write-Host "Abriendo navegador en $serverUrl" -ForegroundColor Cyan
        Start-Process $serverUrl
    }
}
catch {
    Write-Host ""
    Write-Host "Error al ejecutar el servidor: $($_.Exception.Message)" -ForegroundColor Red
    if ($Debug) {
        Write-Host "Detalles del error:" -ForegroundColor Red
        Write-Host $_.Exception.StackTrace -ForegroundColor Gray
    }
}
finally {
    Write-Host ""
    Write-Host "Servidor detenido." -ForegroundColor Yellow

    # Limpiar variables de entorno si se setearon
    if ($Debug) {
        Remove-Item Env:PYTHONVERBOSE -ErrorAction SilentlyContinue
    }

    Write-Host ""
    Write-Host "Presione cualquier tecla para continuar..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}