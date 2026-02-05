@echo off
REM ========================================
REM Savitara - Start All Services
REM ========================================

echo.
echo ========================================
echo   Starting Savitara Application
echo ========================================
echo.

cd /d "%~dp0"

REM Check if backend exists
if not exist "backend\" (
    echo [ERROR] Backend directory not found
    pause
    exit /b 1
)

REM Check if frontend exists
if not exist "savitara-web\" (
    echo [ERROR] Frontend directory not found
    pause
    exit /b 1
)

echo [1/2] Starting Backend Server...
start "Savitara Backend" cmd /k "cd /d "%~dp0backend" && set PYTHONPATH=%~dp0backend && echo Backend starting on http://localhost:8000 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend Server...
start "Savitara Frontend" cmd /k "cd /d "%~dp0savitara-web" && echo Frontend starting... && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   Services Launched!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo Health:   http://localhost:8000/health
echo.
echo To stop: Close the command windows
echo.
echo Waiting 5 seconds to check health...
timeout /t 5 /nobreak >nul

curl http://localhost:8000/health >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Backend is healthy!
) else (
    echo.
    echo [INFO] Backend may still be starting...
)

echo.
echo All done! Press any key to close this window...
pause >nul
