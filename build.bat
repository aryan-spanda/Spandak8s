@echo off
REM Build script for Spandak8s CLI on Windows

echo Building Spandak8s CLI...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or later.
    exit /b 1
)

REM Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo Error: pip not found. Please install pip.
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    exit /b 1
)

echo Building Python package...
python setup.py sdist bdist_wheel
if errorlevel 1 (
    echo Error: Failed to build package.
    exit /b 1
)

echo.
echo ✅ Build successful!
echo.
echo Package files created in dist/ directory:
dir dist\

echo.
echo To install locally, run:
echo   pip install dist\spandak8s-0.1.0-py3-none-any.whl
echo.
echo To test the CLI, run:
echo   python -m spandak8s --help
