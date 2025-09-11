#!/bin/bash
# Quick start script for Spandak8s CLI development and publishing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to find Python and pip
find_python() {
    # Try different Python commands
    for cmd in python3 python python3.11 python3.10 python3.9 python3.8; do
        if command -v "$cmd" &> /dev/null; then
            PYTHON_CMD="$cmd"
            echo "Found Python: $PYTHON_CMD"
            break
        fi
    done
    
    if [[ -z "$PYTHON_CMD" ]]; then
        print_error "Python not found. Please install Python 3.8+ first."
        echo "On Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
        echo "On WSL: Make sure Python is installed and in PATH"
        exit 1
    fi
}

find_pip() {
    # Try different pip commands
    for cmd in pip3 pip "$PYTHON_CMD -m pip"; do
        if eval "command -v $cmd" &> /dev/null 2>&1 || eval "$cmd --version" &> /dev/null 2>&1; then
            PIP_CMD="$cmd"
            echo "Found pip: $PIP_CMD"
            break
        fi
    done
    
    if [[ -z "$PIP_CMD" ]]; then
        print_warning "pip not found. Attempting to install pip..."
        # Try to install pip
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install python3-pip
        else
            print_error "pip not found and couldn't install automatically."
            echo "Please install pip manually:"
            echo "  Ubuntu/Debian: sudo apt install python3-pip"
            echo "  CentOS/RHEL: sudo yum install python3-pip"
            echo "  Or download: curl https://bootstrap.pypa.io/get-pip.py | python3"
            exit 1
        fi
        PIP_CMD="pip3"
    fi
}

# Check if we're in the right directory
if [[ ! -f "spandak8s" ]] || [[ ! -f "snapcraft.yaml" ]]; then
    print_error "Please run this script from the Spandak8s directory"
    exit 1
fi

# Initialize Python and pip commands
find_python
find_pip

print_header "Spandak8s CLI - Quick Start"

# Parse command line arguments
ACTION=${1:-help}

case $ACTION in
    "install-dev")
        print_header "Installing Development Environment"
        
        # Check for virtual environment
        if [[ ! -d "venv" ]]; then
            echo "Creating virtual environment..."
            $PYTHON_CMD -m venv venv
        fi
        
        echo "Activating virtual environment..."
        source venv/bin/activate
        
        # Upgrade pip in virtual environment
        echo "Upgrading pip..."
        python -m pip install --upgrade pip
        
        # Install Python dependencies
        echo "Installing Python dependencies..."
        pip install -e .[dev,test]
        
        # Test installation
        echo "Testing installation..."
        python spandak8s --version
        
        print_success "Development environment installed successfully!"
        echo ""
        echo "To activate the environment later, run:"
        echo "  source venv/bin/activate"
        echo ""
        echo "Try: python spandak8s modules list-tiers"
        ;;
    
    "test")
        print_header "Running Tests"
        
        # Activate virtual environment if it exists
        if [[ -d "venv" ]]; then
            echo "Activating virtual environment..."
            source venv/bin/activate
        fi
        
        # Test CLI commands
        echo "Testing CLI commands..."
        $PYTHON_CMD spandak8s --version
        $PYTHON_CMD spandak8s modules list-tiers
        $PYTHON_CMD spandak8s modules list-categories
        $PYTHON_CMD spandak8s modules list
        
        # Generate sample config
        echo "Testing config generation..."
        $PYTHON_CMD spandak8s modules generate-config test-tenant \
            --modules data-lake-baremetal \
            --tier standard \
            --output test-config.yaml
        
        if [[ -f "test-config.yaml" ]]; then
            print_success "Configuration generated successfully!"
            echo "Generated config preview:"
            head -20 test-config.yaml
            rm test-config.yaml
        fi
        
        print_success "All tests passed!"
        ;;
    
    "build-snap")
        print_header "Building Snap Package"
        
        # Check if snapcraft is installed
        if ! command -v snapcraft &> /dev/null; then
            print_error "snapcraft not found. Install with: sudo snap install snapcraft --classic"
            exit 1
        fi
        
        # Build snap
        echo "Building snap package..."
        snapcraft clean
        snapcraft
        
        # Find the built snap
        SNAP_FILE=$(ls *.snap 2>/dev/null | head -1)
        if [[ -n "$SNAP_FILE" ]]; then
            print_success "Snap built successfully: $SNAP_FILE"
            echo "Install locally with: sudo snap install ./$SNAP_FILE --dangerous"
        else
            print_error "Snap build failed"
            exit 1
        fi
        ;;
    
    "build-python")
        print_header "Building Python Package"
        
        # Activate virtual environment if it exists
        if [[ -d "venv" ]]; then
            echo "Activating virtual environment..."
            source venv/bin/activate
        fi
        
        # Install build tools
        python -m pip install --upgrade build twine
        
        # Clean previous builds
        rm -rf dist/ build/ *.egg-info/
        
        # Build package
        echo "Building Python package..."
        python -m build
        
        # List built packages
        echo "Built packages:"
        ls -la dist/
        
        print_success "Python package built successfully!"
        echo "Upload to TestPyPI with: twine upload --repository testpypi dist/*"
        echo "Upload to PyPI with: twine upload dist/*"
        ;;
    
    "build-docker")
        print_header "Building Docker Image"
        
        # Build Docker image
        echo "Building Docker image..."
        docker build -t spandaai/spandak8s:latest .
        
        # Test the image
        echo "Testing Docker image..."
        docker run --rm spandaai/spandak8s:latest --version
        
        print_success "Docker image built successfully!"
        echo "Run with: docker run --rm spandaai/spandak8s:latest modules list-tiers"
        echo "Push with: docker push spandaai/spandak8s:latest"
        ;;
    
    "publish-test")
        print_header "Publishing to Test Repositories"
        
        # Build Python package
        ./quick-start.sh build-python
        
        # Upload to TestPyPI
        echo "Uploading to TestPyPI..."
        twine upload --repository testpypi dist/* || print_warning "TestPyPI upload failed (might already exist)"
        
        print_success "Test publication complete!"
        echo "Install from TestPyPI with:"
        echo "pip install --index-url https://test.pypi.org/simple/ spandak8s"
        ;;
    
    "release")
        print_header "Creating Release"
        
        # Check if we're on main branch
        BRANCH=$(git branch --show-current)
        if [[ "$BRANCH" != "main" ]] && [[ "$BRANCH" != "master" ]]; then
            print_warning "Not on main/master branch. Current branch: $BRANCH"
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
        
        # Get version from setup.py
        VERSION=$(python -c "import setup; print(setup.setup().get_version())" 2>/dev/null || echo "0.1.0")
        
        echo "Creating release for version: $VERSION"
        
        # Create and push tag
        git tag -a "v$VERSION" -m "Release v$VERSION"
        git push origin "v$VERSION"
        
        print_success "Release tag v$VERSION created and pushed!"
        echo "GitHub Actions will automatically build and publish the release."
        ;;
    
    "clean")
        print_header "Cleaning Build Artifacts"
        
        # Clean Python artifacts
        rm -rf dist/ build/ *.egg-info/ __pycache__/ .pytest_cache/
        find . -name "*.pyc" -delete
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # Clean snap artifacts
        snapcraft clean 2>/dev/null || true
        rm -f *.snap
        
        # Clean test artifacts
        rm -f test-config.yaml
        
        print_success "All build artifacts cleaned!"
        ;;
    
    "help"|*)
        print_header "Spandak8s CLI - Quick Start Commands"
        echo
        echo "Usage: $0 <command>"
        echo
        echo "Commands:"
        echo "  install-dev   - Install development environment"
        echo "  test         - Run tests and verify functionality"
        echo "  build-snap   - Build Snap package"
        echo "  build-python - Build Python package"
        echo "  build-docker - Build Docker image"
        echo "  publish-test - Publish to test repositories (TestPyPI)"
        echo "  release      - Create and push release tag"
        echo "  clean        - Clean all build artifacts"
        echo "  help         - Show this help message"
        echo
        echo "Examples:"
        echo "  $0 install-dev    # Set up development environment"
        echo "  $0 test          # Test the CLI"
        echo "  $0 build-snap    # Build Snap package"
        echo "  $0 release       # Create a new release"
        echo
        ;;
esac
