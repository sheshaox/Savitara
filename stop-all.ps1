#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Stop all Savitara services
.DESCRIPTION
    Stops all running Backend (Python) and Frontend (Node) processes
#>

Write-Host "🛑 Stopping Savitara Services..." -ForegroundColor Red
Write-Host ""

# Stop Python processes (Backend)
$pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "🐍 Stopping Backend (Python) processes..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force
    Write-Host "✅ Backend stopped" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No Backend processes found" -ForegroundColor Gray
}

# Stop Node processes (Frontend)
$nodeProcesses = Get-Process -Name node -ErrorAction SilentlyContinue
if ($nodeProcesses) {
    Write-Host "⚛️  Stopping Frontend (Node) processes..." -ForegroundColor Yellow
    $nodeProcesses | Stop-Process -Force
    Write-Host "✅ Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "ℹ️  No Frontend processes found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ All services stopped!" -ForegroundColor Green
Write-Host ""
