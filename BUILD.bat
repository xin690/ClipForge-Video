@echo off
chcp 65001 >nul
title ClipForge Build

setlocal enabledelayedexpansion

echo ============================================
echo  ClipForge - Build Script
echo ============================================
echo.

:: Find correct Python
set PYTHON_CMD=
if exist "%USERPROFILE%\AppData\Local\Python\bin\python.exe" (
    set PYTHON_CMD=%USERPROFILE%\AppData\Local\Python\bin\python.exe
)
if exist "venv\Scripts\python.exe" set PYTHON_CMD=venv\Scripts\python.exe
if "!PYTHON_CMD!"=="" set PYTHON_CMD=python

echo Using: !PYTHON_CMD!

:: 1. Install PyInstaller
echo [1/5] Check PyInstaller...
"!PYTHON_CMD!" -m pip install pyinstaller -q 2>&1

:: 2. Install dependencies
echo [2/5] Install dependencies...
"!PYTHON_CMD!" -m pip install -r requirements.txt -q

:: 3. Clean previous builds
echo [3/5] Clean cache...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: 4. Build executable (using spec file)
echo [4/5] Build executable...
"!PYTHON_CMD!" -m PyInstaller clipforge.spec --noconfirm 2>&1

:: 5. Copy additional files
echo [5/5] Copy resources...
:: WARNING: config.yaml is copied as-is — ensure no secrets before building
if exist "dist\ClipForge.exe" (
    if not exist "dist\config.yaml" copy config.yaml dist\config.yaml >nul
    if not exist "dist\config.template.yaml" copy config.template.yaml dist\config.template.yaml >nul
    if not exist "dist\scripts" mkdir dist\scripts >nul 2>&1
    if exist "scripts" xcopy /E /I /Y scripts\*.json dist\scripts >nul 2>&1
    if not exist "dist\assets\videos" mkdir dist\assets\videos >nul 2>&1
    if not exist "dist\assets\bgm" mkdir dist\assets\bgm >nul 2>&1
    if exist "app.ico" copy app.ico dist\ >nul
    echo.
    echo ============================================
    echo  SUCCESS: dist\ClipForge.exe
    echo ============================================
    for %%f in (dist\ClipForge.exe) do echo  Size: %%~zf bytes (%%~zf/1MB!%%~zf! MB)
    echo.
    echo  Run: dist\ClipForge.exe
) else (
    echo.
    echo ============================================
    echo  ERROR: Build failed!
    echo ============================================
)

endlocal
pause
