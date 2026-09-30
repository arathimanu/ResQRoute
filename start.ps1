# ResQRoute Startup Script
# Starts FastAPI backend (http://localhost:8000) and React frontend (http://localhost:5173)

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  ResQRoute — Disaster Response Decision Support & Routing System" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Start FastAPI Backend
Write-Host "`n[1/2] Starting FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Yellow
$backendJob = Start-Process .venv\Scripts\uvicorn -ArgumentList "backend.main:app --host 0.0.0.0 --port 8000 --reload" -PassThru -NoNewWindow

Start-Sleep -Seconds 2

# 2. Start React Frontend
Write-Host "`n[2/2] Starting React Frontend on http://localhost:5173 ..." -ForegroundColor Yellow
$frontendJob = Start-Process npm -WorkingDirectory frontend -ArgumentList "run dev" -PassThru -NoNewWindow

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "  System running successfully!" -ForegroundColor Green
Write-Host "  React Dashboard UI: http://localhost:5173" -ForegroundColor Green
Write-Host "  FastAPI Swagger Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "=================================================================`n" -ForegroundColor Green
