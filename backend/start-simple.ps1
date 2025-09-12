# Simple Hybrid Backend Start Script

Write-Host "Starting Spandak8s Hybrid Backend..." -ForegroundColor Green

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install requirements
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements-hybrid.txt

# Create environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating environment configuration..." -ForegroundColor Yellow
    @"
# Hybrid Backend Configuration
JWT_SECRET_KEY=hybrid-secret-key-change-in-production-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Logging
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "Created .env file with default configuration" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting Hybrid FastAPI server..." -ForegroundColor Green
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""

uvicorn hybrid_main:app --reload --host 0.0.0.0 --port 8000
