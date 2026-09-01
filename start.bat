@echo off
title TerraRisk AI - Launcher
color 0A

echo.
echo  ████████╗███████╗██████╗ ██████╗  █████╗ ██████╗ ██╗███████╗██╗  ██╗
echo  ╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║██╔════╝██║ ██╔╝
echo     ██║   █████╗  ██████╔╝██████╔╝███████║██████╔╝██║███████╗█████╔╝
echo     ██║   ██╔══╝  ██╔══██╗██╔══██╗██╔══██║██╔══██╗██║╚════██║██╔═██╗
echo     ██║   ███████╗██║  ██║██║  ██║██║  ██║██║  ██║██║███████║██║  ██╗
echo     ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝
echo.
echo              Kerala Disaster Intelligence Platform
echo  ================================================================
echo.

:: ── Check Python ─────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: ── Check Node ────────────────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo  [1/3] Starting Flask Backend (port 5000)...
start "TerraRisk Backend" cmd /k "cd /d %~dp0backend && python server.py"

echo  [2/3] Starting Vite Frontend (port 5173)...
start "TerraRisk Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo  [3/3] Waiting for servers to boot...
timeout /t 4 /nobreak >nul

echo  [OK]  Opening TerraRisk AI in your browser...
start "" "http://localhost:5173"

echo.
echo  ================================================================
echo   TerraRisk AI is now running!
echo.
echo   Frontend  ->  http://localhost:5173
echo   Backend   ->  http://localhost:5000
echo.
echo   Close this window anytime. The servers keep running in their
echo   own windows. Close those windows to shut everything down.
echo  ================================================================
echo.
pause
