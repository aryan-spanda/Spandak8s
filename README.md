# 🚀 Spandak8s CLI

The official command-line interface for the **Spanda AI Platform**. Provides imperative control over platform modules like MinIO, Spark, Dremio, and other data lake infrastructure components with beautiful Rich UI and comprehensive resource management.

## ✨ Features

- 🎯 **13 Platform Modules** across 6 categories (Data Storage, Analytics, Security, etc.)
- 📊 **3 Resource Tiers** - Bronze (10 CPU/20Gi), Standard (20 CPU/40Gi), Premium (50 CPU/100Gi)
- 🖥️ **Beautiful Rich UI** with tables, progress bars, and colored output
- ⚡ **Cross-Platform** support (Windows/Linux/macOS with WSL integration)
- 🔧 **Auto-Configuration** with intelligent defaults and validation
- 📦 **Multiple Distribution** methods (Snap, PyPI, Docker, GitHub Releases)

## 📦 Installation

### Via Snap (Recommended for Linux)

```bash
sudo snap install spandak8s
```

### Via Python pip

```bash
pip install spandak8s
```

### Via Docker

```bash
docker run --rm -it spandaai/spandak8s:latest --help
```

### From Source

```bash
git clone https://github.com/spanda-ai/spandak8s-cli.git
cd spandak8s-cli
pip install -e .
```

### Windows Setup

For Windows users, we provide a PowerShell setup script with WSL integration:

```powershell
# Clone the repository
git clone https://github.com/spanda-ai/spandak8s-cli.git
cd spandak8s-cli

# Run the Windows setup script
.\setup-powershell.ps1 setup-wsl
.\setup-powershell.ps1 install-dev

# Test the installation
.\setup-powershell.ps1 test
```

## 🎯 Quick Start

### 1. Check Platform Status

```bash
# Check if CLI is working and cluster is accessible
spandak8s status cluster

# Check module health
spandak8s status modules
```

### 2. Explore Available Modules

```bash
# List all available platform modules
spandak8s modules list

# Show modules by category
spandak8s modules list-categories

# Show available resource tiers
spandak8s modules list-tiers
```

### 3. Generate Tenant Configuration

```bash
# Generate configuration for a tenant with specific modules
spandak8s modules generate-config \
  --tenant-name my-company \
  --modules data-lake-baremetal,langflow-ai \
  --tier standard \
  --output-file my-company-config.yaml
```

### 4. Deploy Tenant

```bash
# Create a new tenant
spandak8s tenants create my-company --tier standard

# Deploy tenant configuration
spandak8s tenants deploy my-company-config.yaml

# Check tenant status
spandak8s tenants status my-company
```

## 🏗️ Available Platform Modules

### Data Storage & Management
- **data-lake-baremetal** - Complete data lake with MinIO, Spark, Dremio
- **minio-standalone** - Standalone object storage
- **dremio-standalone** - SQL query engine

### Analytics & Processing  
- **spark-cluster** - Distributed compute engine
- **jupyter-notebooks** - Interactive development environment
- **superset-analytics** - Business intelligence dashboards

### AI & Machine Learning
- **langflow-ai** - Visual AI workflow builder
- **ollama-llm** - Local language model inference
- **vector-database** - Embeddings and similarity search

### Security & Monitoring
- **vault-secrets** - Secret management
- **monitoring-stack** - Prometheus + Grafana + AlertManager

### Platform Services
- **argocd-gitops** - GitOps continuous delivery
- **ingress-controllers** - Load balancing and routing

### Communication
- **kafka-streaming** - Event streaming platform

## 💰 Resource Tiers

| Tier | CPU Limit | Memory Limit | Storage | Best For |
|------|-----------|--------------|---------|----------|
| **Bronze** | 10 cores | 20 GiB | 100 GiB | Development, testing |
| **Standard** | 20 cores | 40 GiB | 500 GiB | Small production workloads |
| **Premium** | 50 cores | 100 GiB | 2 TiB | Large production environments |

## 📋 Configuration Examples

### Basic Tenant Configuration

```yaml
# Generated with: spandak8s modules generate-config --tenant-name acme --tier standard
tenant:
  name: acme
  tier: standard

modules:
  - data-lake-baremetal
  - langflow-ai

resourceQuota:
  hard:
    requests.cpu: '20'
    requests.memory: 40Gi
    limits.cpu: '20'
    limits.memory: 40Gi
    requests.storage: 500Gi
```

### Advanced Configuration with Custom Resources

```yaml
tenant:
  name: enterprise-corp
  tier: premium
  customResources:
    requests.cpu: '75'
    requests.memory: 150Gi

modules:
  - data-lake-baremetal
  - spark-cluster
  - vault-secrets
  - monitoring-stack
  - argocd-gitops
```

## 🔧 Development

### Prerequisites
- Python 3.8+
- kubectl installed and configured
- Access to a Kubernetes cluster
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/spanda-ai/spandak8s-cli.git
cd spandak8s-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Test the CLI
spandak8s --help
```

### Project Structure

```
spandak8s-cli/
├── spandak8s                     # Main CLI entry point
├── cmd/                          # CLI command implementations
│   ├── modules.py               # Module management commands  
│   ├── tenants.py               # Tenant lifecycle management
│   └── status.py                # Platform monitoring commands
├── pkg/                          # Core library modules
│   ├── module_definitions.py   # Module definitions and resource management
│   ├── config.py                # Configuration management
│   ├── kubernetes.py            # Kubernetes integration
│   ├── api_client.py            # HTTP client for backend APIs
│   └── module_detector.py       # Module discovery and health monitoring
├── config/
│   └── module-definitions.yaml  # Central module configuration
├── pyproject.toml               # Modern Python project configuration
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker containerization
├── snapcraft.yaml              # Snap package configuration
└── Makefile                     # Build automation
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_modules.py

# Run with coverage
make test-coverage
```

### Building

```bash
# Build Python package
make build

# Build Docker image
make docker-build

# Build Snap package (Linux only)
make snap-build
```

## 📦 Publishing

### Prerequisites for Publishing

1. **PyPI Account** - Create account at https://pypi.org
2. **Snap Store Account** - Ubuntu One account for Snap Store
3. **Docker Hub Account** - For Docker image publishing
4. **GitHub Repository** - For GitHub Releases

### Manual Publishing

#### PyPI

```bash
# Build and upload to PyPI
pip install build twine
python -m build
twine upload dist/*
```

#### Snap Store

```bash
# Install snapcraft
sudo snap install snapcraft --classic

# Login to Snap Store
snapcraft login

# Export login credentials for CI/CD
snapcraft export-login --snaps=spandak8s --channels=edge,beta,candidate,stable -

# Build and publish
snapcraft
snapcraft upload spandak8s_*.snap --release=edge
```

#### Docker Hub

```bash
# Build and tag
docker build -t spandaai/spandak8s:latest .
docker tag spandaai/spandak8s:latest spandaai/spandak8s:v0.1.0

# Push to Docker Hub  
docker push spandaai/spandak8s:latest
docker push spandaai/spandak8s:v0.1.0
```

### Automated Publishing with GitHub Actions

The repository includes GitHub Actions workflows for automated publishing:

1. **Set up repository secrets:**
   ```bash
   # PyPI token
   PYPI_API_TOKEN=pypi-...
   
   # Snapcraft credentials (from snapcraft export-login)
   SNAPCRAFT_STORE_CREDENTIALS=eyJ0IjogInUxLW1hY2Fyb29uIi...
   
   # Docker Hub credentials
   DOCKER_USERNAME=your-username
   DOCKER_PASSWORD=your-password-or-token
   ```

2. **Create a release:**
   ```bash
   # Tag and push
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. **Automated workflow publishes to:**
   - PyPI (pip install spandak8s)
   - Snap Store (snap install spandak8s)
   - Docker Hub (docker pull spandaai/spandak8s)
   - GitHub Releases

## 🎨 Usage Examples

### Module Management

```bash
# List modules with beautiful table output
spandak8s modules list

# Filter by category
spandak8s modules list --category "AI & Machine Learning"

# Check module health with progress indicators
spandak8s modules health --module langflow-ai

# Generate configuration interactively
spandak8s modules generate-config --interactive
```

### Tenant Operations

```bash
# Create tenant with Bronze tier (development)
spandak8s tenants create dev-team --tier bronze

# Create tenant with custom resources
spandak8s tenants create prod-team --tier premium --cpu 100 --memory 200Gi

# List all tenants with status
spandak8s tenants list

# Get detailed tenant information
spandak8s tenants status prod-team --detailed

# Delete tenant and cleanup resources
spandak8s tenants delete dev-team --confirm
```

### Platform Monitoring

```bash
# Comprehensive cluster health check
spandak8s status cluster --detailed

# Check specific module across all tenants
spandak8s status modules --module spark-cluster

# Resource utilization overview
spandak8s status tenants --show-resources

# Full system diagnostics
spandak8s status diagnostics
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with proper tests
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to all functions and classes
- Include tests for new functionality
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: https://docs.spanda.ai/cli
- **Issues**: https://github.com/spanda-ai/spandak8s-cli/issues
- **Discussions**: https://github.com/spanda-ai/spandak8s-cli/discussions
- **Email**: support@spanda.ai

## 🎉 Acknowledgments

- Built with ❤️ using [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)
- Inspired by kubectl and other modern CLI tools
- Thanks to the Spanda AI Platform team and contributors

# Enable Spark (platform determines worker count based on tenant tier)
spandak8s enable spark --env dev
```

### 4. Check status

```bash
# Check all modules in dev environment
spandak8s status --env dev

# Check specific module
spandak8s module status minio --env dev
```

## 🛠️ Available Commands

### Module Management

```bash
# List available modules
spandak8s module list

# Enable a module (platform determines resources)
spandak8s enable <module> --env <env>
spandak8s module enable <module> --env <env>

# Disable a module
spandak8s disable <module> --env <env>
spandak8s module disable <module> --env <env>

# Scale a module (if allowed by tenant tier)
spandak8s module configure <module> --scale 3 --env <env>

# Get module status
spandak8s module status <module> --env <env>
```

### Status & Health

```bash
# Overall platform status
spandak8s status --env <env>
spandak8s status --all-envs

# Backend health check
spandak8s status health

# Kubernetes cluster info
spandak8s status cluster
```

### Tenant Management

```bash
# List all tenants
spandak8s tenant list

# Create a new tenant
spandak8s tenant create <name> --description "My Company"

# Switch to a different tenant
spandak8s tenant switch <name>

# Show current tenant
spandak8s tenant current

# Get tenant details
spandak8s tenant info [name]
```

## 🔧 Configuration

The CLI stores configuration in `~/.spanda/config.yaml`. You can modify this file directly or use the config commands:

```bash
# View current configuration
cat ~/.spanda/config.yaml

# Set a configuration value
spandak8s config set api.base_url https://my-backend.company.com

# Get a configuration value
spandak8s config get tenant.name
```

### Default Configuration

```yaml
api:
  base_url: http://localhost:8080
  timeout: 30
  verify_ssl: true

kubernetes:
  config_path: ~/.kube/config
  context: null

tenant:
  name: default
  namespace_prefix: tenant

defaults:
  environment: dev
  storage_class: standard
  replicas: 1
```

## 📚 Available Modules

The Spanda Platform provides the following modules:

| Module | Description | Platform-Managed Resources |
|--------|-------------|----------------------------|
| `minio` | Object storage service | Storage, replicas, memory |
| `spark` | Distributed computing engine | Workers, memory, CPU cores |
| `dremio` | Data lake analytics | Storage, memory allocation |
| `kafka` | Event streaming platform | Partitions, replicas, storage |
| `airflow` | Workflow orchestration | Memory, CPU, worker pods |
| `jupyterhub` | Multi-user Jupyter environment | Storage, memory per user |

## 🌍 Environments

The platform supports multiple environments per tenant:

- **dev**: Development environment with relaxed resource limits
- **staging**: Pre-production environment for testing
- **prod**: Production environment with full resource allocation

## 📖 Examples

### Complete Data Lake Setup

```bash
# Enable core data lake components - platform optimizes resources
spandak8s enable minio --env prod
spandak8s enable spark --env prod  
spandak8s enable dremio --env prod

# Enable data pipeline tools
spandak8s enable kafka --env prod
spandak8s enable airflow --env prod

# Check everything is running
spandak8s status --env prod
```

### Development Environment

```bash
# Lightweight dev setup - platform uses dev-tier resources
spandak8s enable minio --env dev
spandak8s enable spark --env dev
spandak8s enable jupyterhub --env dev

# Quick status check
spandak8s status --env dev
```

### Configuration Updates

```bash
# Scale up Spark workers (if tenant tier allows)
spandak8s module configure spark --scale 5 --env prod

# Advanced configuration via file
spandak8s module configure dremio --config-file dremio-config.yaml --env prod

# Check current resource allocation
spandak8s module status minio --env prod
```

## 🔐 Authentication

The CLI uses your Kubernetes configuration for cluster access. Make sure you have:

1. **kubectl** installed and configured
2. **Valid kubeconfig** with access to your cluster
3. **Proper RBAC permissions** for your tenant namespaces

## 🐛 Troubleshooting

### Common Issues

**Backend connection failed:**
```bash
# Check backend health
spandak8s status health

# Verify configuration
spandak8s config get api.base_url
```

**Module deployment failed:**
```bash
# Check Kubernetes cluster connectivity
spandak8s status cluster

# Verify kubectl access
kubectl get nodes
```

**Permission denied:**
```bash
# Check current tenant
spandak8s tenant current

# Verify RBAC permissions
kubectl auth can-i create pods --namespace=my-tenant-dev
```

### Debug Mode

Enable debug output for detailed error information:

```bash
spandak8s --debug <command>
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- 📖 Documentation: https://docs.spanda.ai
- 💬 Community: https://community.spanda.ai
- 🐛 Issues: https://github.com/spanda-ai/spandak8s-cli/issues
- 📧 Email: support@spanda.ai
