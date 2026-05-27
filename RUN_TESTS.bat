@echo off
chcp 65001 >nul
title ClipForge Test Runner

echo ============================================
echo  ClipForge Test Runner
echo ============================================
echo.

:: Find Python
set PYTHON_CMD=python
where %PYTHON_CMD% >nul 2>&1
if %errorlevel% neq 0 (
    set PYTHON_CMD=%LOCALAPPDATA%\Python\bin\python.exe
)

echo Using: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

:: Menu
echo Select test mode:
echo   1 - Quick test (51 tests, no FFmpeg needed)
echo   2 - Full test (54 pytest tests)
echo   3 - Generate test assets (requires FFmpeg)
echo   4 - Input/output module check
echo.
set /p MODE="Enter choice (1-4): "

if "%MODE%"=="1" (
    echo.
    echo Running quick test suite...
    echo.
    %PYTHON_CMD% tests/run_all_tests.py
)

if "%MODE%"=="2" (
    echo.
    echo Running pytest suite (54 tests)...
    echo.
    %PYTHON_CMD% -m pytest tests/ -v --tb=short
)

if "%MODE%"=="3" (
    echo.
    echo Generating test assets...
    echo.
    %PYTHON_CMD% tests/generate_test_assets.py
    if %errorlevel% neq 0 (
        echo.
        echo Note: FFmpeg is required. Download from: https://ffmpeg.org/download.html
    )
)

if "%MODE%"=="4" (
    echo.
    echo Checking module imports...
    echo.
    %PYTHON_CMD% -c "
import os; os.environ['QT_QPA_PLATFORM'] = 'offscreen'
modules = [
    'core.config','core.models','core.database','core.matcher',
    'core.rules','core.timeline','core.tts','core.subtitle',
    'core.ffmpeg','core.renderer','core.pipeline','core.scanner',
    'core.ai_planner',
]
ok, fail = 0, 0
for m in modules:
    try:
        __import__(m)
        print(f'  OK  {m}')
        ok += 1
    except Exception as e:
        print(f'  FAIL {m}: {e}')
        fail += 1
print(f'\nResults: {ok}/{ok+fail} passed')
"
)

echo.
if "%MODE%"=="" (
    echo Invalid choice.
) else (
    echo Done.
)
pause
