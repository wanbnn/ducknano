@echo off
title DuckNano

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

REM Verifica PATH persistente do usuário
reg query HKCU\Environment /v PATH 2>nul | find /I "%APP_DIR%" >nul
if errorlevel 1 (
    for /f "tokens=2,*" %%A in (
        'reg query HKCU\Environment /v PATH 2^>nul ^| find "PATH"'
    ) do set "USERPATH=%%B"

    setx PATH "%USERPATH%;%APP_DIR%" >nul
)

python -m pip install requests rich

python "%APP_DIR%\app.py" %*