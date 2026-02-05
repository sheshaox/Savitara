# Start Savitara Backend and Frontend

Write-Host "Starting Savitara Application..." -ForegroundColor Cyan
Write-Host ""

# Get project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "savitara-web"

# Check if backend directory exists
if (-not (Test-Path $BackendPath)) {
    Write-Host "ERROR: Backend directory not found: $BackendPath" -ForegroundColor Red
    exit 1
}

# Check if frontend directory exists
if (-not (Test-Path $FrontendPath)) {
    Write-Host "ERROR: Frontend directory not found: $FrontendPath" -ForegroundColor Red
    exit 1
}

Write-Host "Backend Path: $BackendPath" -ForegroundColor Gray
Write-Host "Frontend Path: $FrontendPath" -ForegroundColor Gray
Write-Host ""

# Start Backend
Write-Host "Starting Backend Server..." -ForegroundColor Yellow
$BackendCmd = "cd '$BackendPath'; `$env:PYTHONPATH='$BackendPath'; Write-Host 'Backend starting on http://localhost:8000' -ForegroundColor Green; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd
Start-Sleep -Seconds 2

# Start Frontend
Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
$FrontendCmd = "cd '$FrontendPath'; Write-Host 'Frontend starting...' -ForegroundColor Green; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Services launched in separate windows!" -ForegroundColor Green
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "   Health:   http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "To stop: Close the PowerShell windows or press Ctrl+C in each" -ForegroundColor Gray
Write-Host ""

# Wait a bit and check if services are running
Start-Sleep -Seconds 5
Write-Host "Checking service health..." -ForegroundColor Yellow

try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "Backend is healthy!" -ForegroundColor Green
} catch {
    Write-Host "Backend may still be starting... Check the Backend window" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "All done! Your application is ready." -ForegroundColor Green
Write-Host ""
