# Script de PowerShell para ejecutar Cambio Dollar en Windows
# Uso: .\run_server.ps1

param(
    [switch]$Help,
    [int]$Port = 8000,
    [string]$Host = "localhost"
)

if ($Help) {
    Write-Host "Cambio Dollar - Servidor Web"
    Write-Host ""
    Write-Host "Uso: .\run_server.ps1 [-Port <puerto>] [-Host <host>]"
    Write-Host ""
    Write-Host "Parámetros:"
    Write-Host "  -Port    Puerto del servidor (por defecto: 8000)"
    Write-Host "  -Host    Host del servidor (por defecto: localhost)"
    Write-Host "  -Help    Muestra esta ayuda"
    Write-Host ""
    Write-Host "Ejemplos:"
    Write-Host "  .\run_server.ps1"
    Write-Host "  .\run_server.ps1 -Port 8080"
    Write-Host "  .\run_server.ps1 -Host 0.0.0.0 -Port 8000"
    exit
}

Write-Host "=== Cambio Dollar ===" -ForegroundColor Cyan
Write-Host "Iniciando servidor web..." -ForegroundColor Green
Write-Host ""
Write-Host "URL: http://$Host`:$Port" -ForegroundColor Yellow
Write-Host "Presiona Ctrl+C para detener el servidor" -ForegroundColor Gray
Write-Host ""

try {
    & ".\cambio-dollar.exe" serve --host $Host --port $Port
} catch {
    Write-Host "Error al iniciar el servidor: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Presiona Enter para continuar"
}