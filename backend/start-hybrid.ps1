# Hybrid Backend Setup and Start Script for Windows

Write-Host "🚀 Starting Spandak8s Hybrid Backend Setup..." -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version 2>$null
    Write-Host "✅ Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 3 is required but not installed." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install hybrid requirements
Write-Host "📚 Installing hybrid backend dependencies..." -ForegroundColor Yellow
pip install -r requirements-hybrid.txt

# Check if module definitions exist
$moduleDefPath = "..\config\module-definitions.yaml"
if (-not (Test-Path $moduleDefPath)) {
    Write-Host "❌ Module definitions file not found at: $moduleDefPath" -ForegroundColor Red
    Write-Host "   Please ensure the config/module-definitions.yaml file exists" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ Found module definitions file" -ForegroundColor Green
}

# Check Kubernetes connectivity
Write-Host "🔍 Checking Kubernetes connectivity..." -ForegroundColor Yellow
try {
    kubectl cluster-info --request-timeout=5s 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Kubernetes cluster accessible" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Kubernetes cluster not accessible" -ForegroundColor Yellow
        Write-Host "   Some features will be limited without cluster access" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  kubectl not found or cluster not accessible" -ForegroundColor Yellow
    Write-Host "   Some features will be limited without cluster access" -ForegroundColor Yellow
}

# Create environment file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "⚙️ Creating environment configuration..." -ForegroundColor Yellow
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
    Write-Host "✅ Created .env file with default configuration" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎯 Hybrid Backend Features:" -ForegroundColor Cyan
Write-Host "  ✅ Module definitions from your YAML file" -ForegroundColor Green
Write-Host "  ✅ Real-time status from Kubernetes" -ForegroundColor Green  
Write-Host "  ✅ Simple JWT authentication (in-memory users)" -ForegroundColor Green
Write-Host "  ✅ No database required!" -ForegroundColor Green
Write-Host ""

Write-Host "👥 Default Users:" -ForegroundColor Cyan
Write-Host "  Username: admin | Password: spanda123! | Roles: admin, user" -ForegroundColor Yellow
Write-Host "  Username: user  | Password: user123!  | Roles: user" -ForegroundColor Yellow
Write-Host ""

# Start the hybrid server
Write-Host "🚀 Starting Hybrid FastAPI server..." -ForegroundColor Green
Write-Host "📖 API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🔍 Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "🔐 Login: POST http://localhost:8000/api/v1/auth/login" -ForegroundColor Cyan
Write-Host ""

uvicorn hybrid_main:app --reload --host 0.0.0.0 --port 8000
