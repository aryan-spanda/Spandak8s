#!/bin/bash
# WSL/Ubuntu Setup Script for Spandak8s Development

set -e

echo "🐧 Setting up Spandak8s development environment on WSL/Ubuntu..."

# Update package list
echo "📦 Updating package list..."
sudo apt update

# Install Python and pip if not available
echo "🐍 Installing Python and pip..."
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install development tools
echo "🔧 Installing development tools..."
sudo apt install -y build-essential git curl

# Install snapcraft for Snap packaging (optional)
echo "📦 Installing snapcraft..."
sudo snap install snapcraft --classic || echo "⚠️ Snapcraft install failed (optional)"

# Install Docker (optional)
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "⚠️ Please log out and back in for Docker group changes to take effect"
else
    echo "Docker already installed"
fi

# Create and activate virtual environment
echo "🏗️ Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
python -m pip install --upgrade pip

# Install development dependencies
echo "📚 Installing development dependencies..."
pip install -e .[dev,test]

# Test the installation
echo "🧪 Testing installation..."
python spandak8s --version
python spandak8s modules list-tiers

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Test the CLI: python spandak8s modules list-tiers"
echo "  3. Run development commands: ./quick-start.sh test"
echo ""
echo "📖 For more commands, run: ./quick-start.sh help"
