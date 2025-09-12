@echo off
REM Spandak8s CLI Runner - Automatically uses backend virtual environment

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "VENV_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe"
set "CLI_SCRIPT=%SCRIPT_DIR%spandak8s-original"

REM Check if backend virtual environment exists
if not exist "%VENV_PYTHON%" (
    echo ❌ Backend virtual environment not found!
    echo 🔧 Please run the backend setup first:
    echo    cd backend
    echo    python -m venv venv
    echo    .\venv\Scripts\Activate.ps1
    echo    pip install -r requirements-hybrid.txt
    exit /b 1
)

REM Check if original CLI script exists
if not exist "%CLI_SCRIPT%" (
    echo ❌ Original CLI script not found!
    exit /b 1
)

REM Run the CLI using backend Python environment
"%VENV_PYTHON%" "%CLI_SCRIPT%" %*
