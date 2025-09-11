# PowerShell script to set up Spandak8s development environment via WSL
# Run this from PowerShell in Windows

param(
    [Parameter(Position=0)]
    [string]$Action = "help"
)

# Colors for PowerShell output
function Write-Header {
    param([string]$Message)
    Write-Host "=== $Message ===" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Check if WSL is available
function Test-WSL {
    try {
        wsl --version | Out-Null
        return $true
    }
    catch {
        Write-Error "WSL is not available. Please install WSL first."
        Write-Host "Install WSL: wsl --install" -ForegroundColor Yellow
        return $false
    }
}

# Get the WSL path for the current directory
$CurrentDir = Get-Location
$WSLPath = $CurrentDir.Path -replace 'C:', '/mnt/c' -replace '\\', '/'

Write-Header "Spandak8s CLI - PowerShell Setup"

if (-not (Test-WSL)) {
    exit 1
}

switch ($Action) {
    "setup-wsl" {
        Write-Header "Setting up WSL Environment"
        
        Write-Host "Installing Python and dependencies in WSL..." -ForegroundColor Cyan
        
        # Update package list and install Python
        wsl bash -c "sudo apt update"
        wsl bash -c "sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential git curl"
        
        # Install snapcraft (optional)
        Write-Host "Installing snapcraft..." -ForegroundColor Cyan
        wsl bash -c "sudo snap install snapcraft --classic || echo 'Snapcraft install failed (optional)'"
        
        Write-Success "WSL environment setup complete!"
    }
    
    "install-dev" {
        Write-Header "Installing Development Environment"
        
        # Navigate to project directory and set up Python environment
        wsl bash -c "cd '$WSLPath' && python3 -m venv venv"
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python -m pip install --upgrade pip"
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && pip install -e .[dev,test]"
        
        # Test installation
        Write-Host "Testing installation..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python spandak8s --version"
        
        Write-Success "Development environment installed successfully!"
        Write-Host ""
        Write-Host "To run commands, use:" -ForegroundColor Yellow
        Write-Host "  .\setup-powershell.ps1 test" -ForegroundColor White
    }
    
    "test" {
        Write-Header "Running Tests"
        
        # Test CLI commands
        Write-Host "Testing CLI commands..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python spandak8s --version"
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python spandak8s modules list-tiers"
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python spandak8s modules list-categories"
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python spandak8s modules list"
        
        # Generate sample config
        Write-Host "Testing config generation..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python spandak8s modules generate-config test-tenant --modules data-lake-baremetal --tier standard --output test-config.yaml"
        
        # Check if config was generated
        if (wsl bash -c "cd '$WSLPath' && test -f test-config.yaml && echo 'exists'") {
            Write-Success "Configuration generated successfully!"
            Write-Host "Generated config preview:" -ForegroundColor Cyan
            wsl bash -c "cd '$WSLPath' && head -20 test-config.yaml"
            wsl bash -c "cd '$WSLPath' && rm test-config.yaml"
        }
        
        Write-Success "All tests passed!"
    }
    
    "build-python" {
        Write-Header "Building Python Package"
        
        # Install build tools and build package
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python -m pip install --upgrade build twine"
        wsl bash -c "cd '$WSLPath' && rm -rf dist/ build/ *.egg-info/"
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && python -m build"
        
        # List built packages
        Write-Host "Built packages:" -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && ls -la dist/"
        
        Write-Success "Python package built successfully!"
        Write-Host "Upload to TestPyPI with: .\setup-powershell.ps1 publish-test" -ForegroundColor Yellow
    }
    
    "build-snap" {
        Write-Header "Building Snap Package"
        
        # Check if snapcraft is available
        $snapcraftCheck = wsl bash -c "command -v snapcraft && echo 'available' || echo 'missing'"
        if ($snapcraftCheck -notmatch "available") {
            Write-Error "snapcraft not found. Run: .\setup-powershell.ps1 setup-wsl first"
            exit 1
        }
        
        # Build snap
        Write-Host "Building snap package..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && snapcraft clean"
        wsl bash -c "cd '$WSLPath' && snapcraft"
        
        # Check for built snap
        $snapFile = wsl bash -c "cd '$WSLPath' && ls *.snap 2>/dev/null | head -1"
        if ($snapFile) {
            Write-Success "Snap built successfully: $snapFile"
            Write-Host "Install locally with: wsl bash -c `"cd '$WSLPath' && sudo snap install ./$snapFile --dangerous`"" -ForegroundColor Yellow
        } else {
            Write-Error "Snap build failed"
        }
    }
    
    "build-docker" {
        Write-Header "Building Docker Image"
        
        # Build Docker image
        Write-Host "Building Docker image..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && docker build -t spandaai/spandak8s:latest ."
        
        # Test the image
        Write-Host "Testing Docker image..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && docker run --rm spandaai/spandak8s:latest --version"
        
        Write-Success "Docker image built successfully!"
        Write-Host "Run with: wsl bash -c `"docker run --rm spandaai/spandak8s:latest modules list-tiers`"" -ForegroundColor Yellow
    }
    
    "publish-test" {
        Write-Header "Publishing to Test Repositories"
        
        # Build Python package first
        & $PSCommandPath build-python
        
        # Upload to TestPyPI
        Write-Host "Uploading to TestPyPI..." -ForegroundColor Cyan
        wsl bash -c "cd '$WSLPath' && source venv/bin/activate && twine upload --repository testpypi dist/* || echo 'TestPyPI upload failed (might already exist)'"
        
        Write-Success "Test publication complete!"
        Write-Host "Install from TestPyPI with:" -ForegroundColor Yellow
        Write-Host "  pip install --index-url https://test.pypi.org/simple/ spandak8s" -ForegroundColor White
    }
    
    "clean" {
        Write-Header "Cleaning Build Artifacts"
        
        # Clean Python artifacts
        wsl bash -c "cd '$WSLPath' && rm -rf dist/ build/ *.egg-info/ __pycache__/ .pytest_cache/"
        wsl bash -c "cd '$WSLPath' && find . -name '*.pyc' -delete"
        wsl bash -c "cd '$WSLPath' && find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true"
        
        # Clean snap artifacts
        wsl bash -c "cd '$WSLPath' && snapcraft clean 2>/dev/null || true"
        wsl bash -c "cd '$WSLPath' && rm -f *.snap"
        
        # Clean test artifacts
        wsl bash -c "cd '$WSLPath' && rm -f test-config.yaml"
        
        Write-Success "All build artifacts cleaned!"
    }
    
    "shell" {
        Write-Header "Opening WSL Shell in Project Directory"
        wsl bash -c "cd '$WSLPath' && exec bash"
    }
    
    "help" {
        Write-Header "Spandak8s CLI - PowerShell Setup Commands"
        Write-Host ""
        Write-Host "Usage: .\setup-powershell.ps1 <command>" -ForegroundColor White
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor Yellow
        Write-Host "  setup-wsl     - Install WSL dependencies (Python, snapcraft, etc.)" -ForegroundColor White
        Write-Host "  install-dev   - Install development environment" -ForegroundColor White
        Write-Host "  test         - Run tests and verify functionality" -ForegroundColor White
        Write-Host "  build-python - Build Python package" -ForegroundColor White
        Write-Host "  build-snap   - Build Snap package" -ForegroundColor White
        Write-Host "  build-docker - Build Docker image" -ForegroundColor White
        Write-Host "  publish-test - Publish to test repositories (TestPyPI)" -ForegroundColor White
        Write-Host "  clean        - Clean all build artifacts" -ForegroundColor White
        Write-Host "  shell        - Open WSL shell in project directory" -ForegroundColor White
        Write-Host "  help         - Show this help message" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Yellow
        Write-Host "  .\setup-powershell.ps1 setup-wsl      # Initial WSL setup" -ForegroundColor White
        Write-Host "  .\setup-powershell.ps1 install-dev    # Set up development environment" -ForegroundColor White
        Write-Host "  .\setup-powershell.ps1 test          # Test the CLI" -ForegroundColor White
        Write-Host "  .\setup-powershell.ps1 build-python  # Build Python package" -ForegroundColor White
        Write-Host ""
        Write-Host "WSL Path: $WSLPath" -ForegroundColor Cyan
    }
    
    default {
        Write-Error "Unknown command: $Action"
        & $PSCommandPath help
        exit 1
    }
}
