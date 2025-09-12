# Auto-start Backend Helper for Spandak8s CLI
# This script ensures the hybrid backend is running when CLI commands are executed

param(
    [string]$Command = "",
    [switch]$CheckOnly = $false
)

$BackendPath = "c:\Users\aryan\OneDrive\Documents\spanda docs\Spandak8s\backend"
$BackendUrl = "http://localhost:8000"

function Test-BackendRunning {
    try {
        $response = Invoke-WebRequest -Uri "$BackendUrl/health" -Method GET -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-Backend {
    Write-Host "🚀 Starting Spandak8s Hybrid Backend..." -ForegroundColor Green
    
    # Change to backend directory
    Push-Location $BackendPath
    
    try {
        # Check if virtual environment exists
        if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
            Write-Host "❌ Virtual environment not found. Please run setup first." -ForegroundColor Red
            return $false
        }
        
        # Start backend in background
        Start-Process powershell -ArgumentList "-Command", "& '.\venv\Scripts\Activate.ps1'; python -m uvicorn hybrid_main:app --host 0.0.0.0 --port 8000" -WindowStyle Minimized
        
        # Wait for backend to start
        Write-Host "⏳ Waiting for backend to start..." -ForegroundColor Yellow
        $timeout = 30
        $counter = 0
        
        while ($counter -lt $timeout) {
            if (Test-BackendRunning) {
                Write-Host "✅ Backend is now running at $BackendUrl" -ForegroundColor Green
                return $true
            }
            Start-Sleep -Seconds 1
            $counter++
        }
        
        Write-Host "❌ Backend failed to start within $timeout seconds" -ForegroundColor Red
        return $false
        
    } finally {
        Pop-Location
    }
}

# Main logic
if ($CheckOnly) {
    if (Test-BackendRunning) {
        Write-Host "✅ Backend is running" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ Backend is not running" -ForegroundColor Red
        exit 1
    }
}

# Check if backend is running
if (-not (Test-BackendRunning)) {
    Write-Host "📡 Backend not running. Starting automatically..." -ForegroundColor Yellow
    
    if (-not (Start-Backend)) {
        Write-Host "❌ Failed to start backend automatically." -ForegroundColor Red
        Write-Host "💡 Please start it manually:" -ForegroundColor Cyan
        Write-Host "   cd '$BackendPath'" -ForegroundColor Yellow
        Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
        Write-Host "   python -m uvicorn hybrid_main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✅ Backend is already running" -ForegroundColor Green
}

# Execute the original command if provided
if ($Command) {
    Write-Host "🔄 Executing: $Command" -ForegroundColor Cyan
    Invoke-Expression $Command
}
