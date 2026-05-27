@echo off
chcp 65001 >nul
title ClipForge

echo ============================================
echo  ClipForge - AI 视频剪辑引擎
echo ============================================
echo.

:: Find correct Python
set PYTHON_CMD=

:: 1. Try known install paths
if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set PYTHON_CMD=%LOCALAPPDATA%\Python\bin\python.exe
)
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
)

:: 2. Try system python (skip WindowsApps stub)
if "%PYTHON_CMD%"=="" (
    for /f "skip=1 delims=" %%i in ('where python 2^>nul') do (
        echo %%i | findstr /V "WindowsApps" >nul
        if not errorlevel 1 (
            set PYTHON_CMD=%%i
            goto :found
        )
    )
)
if "%PYTHON_CMD%"=="" (
    for /f "skip=1 delims=" %%i in ('where python3 2^>nul') do (
        set PYTHON_CMD=%%i
        goto :found
    )
)

:found
if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found!
    echo Install Python 3.10+ from: https://python.org/downloads/
    pause
    exit /b 1
)

echo Using: %PYTHON_CMD%
%PYTHON_CMD% --version

:: 3. Verify essential packages
echo.
echo Checking dependencies...
%PYTHON_CMD% -c "import PyQt6, yaml, pydantic" 2>nul
if errorlevel 1 (
    echo [WARN] Missing packages. Installing...
    %PYTHON_CMD% -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: 4. Start ClipForge
echo.
echo Starting ClipForge...
%PYTHON_CMD% app.py

if errorlevel 1 (
    echo.
    echo Error: ClipForge exited with code %errorlevel%
    pause
)
