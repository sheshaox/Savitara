@echo off
REM ========================================
REM Savitara - Stop All Services
REM ========================================

echo.
echo Stopping Savitara Services...
echo.

REM Stop Python processes (Backend)
taskkill /F /IM python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend stopped
) else (
    echo [INFO] No Backend processes found
)

REM Stop Node processes (Frontend)
taskkill /F /IM node.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Frontend stopped
) else (
    echo [INFO] No Frontend processes found
)

echo.
echo All services stopped!
echo.
pause
