# 🚀 Spandak8s CLI & Platform

The complete **Spanda AI Platform** CLI with hybrid backend. Provides imperative control over platform modules like MinIO, Spark, Dremio, security-vault, and data lake infrastructure with beautiful Rich UI, real-time monitoring, and advanced resource management.

## ✨ Features

### 🎯 **Platform Modules**
- **Dynamic Module Management** - Security-vault, data lake components, Kafka, and more
- **Environment-Specific Deployments** - dev, staging, prod with values overlays
- **Tenant-Scoped Namespaces** - Dynamic namespace generation (tenant-environment)
- **Resource Cleanup Options** - Granular control over PVC, secrets, and serviceaccount cleanup
- **Real-time Status** - Direct Kubernetes API monitoring via WSL integration

### 🖥️ **CLI Interface**
- **Beautiful Rich UI** with tables, progress bars, and colored output
- **Cross-Platform** support (Windows with WSL2 integration)
- **Simple Commands** - `python spandak8s enable/disable module-name --env tenant-environment`
- **Advanced Cleanup** - `--keep-data`, `--complete-cleanup` options
- **Auto-Configuration** with intelligent defaults

### ⚡ **Hybrid Backend**
- **No Authentication Required** - Direct API access for development
- **YAML-based Configuration** - Module definitions from local file
- **WSL-Kubernetes Integration** - Seamless Windows-to-WSL kubectl access
- **Helm-based Deployments** - Environment-specific values files
- **Dynamic Namespace Support** - Global namespace inheritance

### 🧹 **Advanced Resource Management**
- **Smart Cleanup** - Configurable PVC and resource removal
- **Data Preservation** - Option to keep persistent volumes
- **Complete Cleanup** - Remove all resources including secrets
- **Resource Warnings** - Clear data loss warnings before destructive operations

## 📦 Quick Start

### Prerequisites

1. **Windows with WSL2** (Ubuntu recommended)
2. **Kubernetes cluster** (kind, k3s, or production cluster)
3. **Helm 3.x** installed in WSL
4. **kubectl** configured in WSL

### Installation

```bash
# Clone the repository
git clone https://github.com/aryan-spanda/Spandak8s.git
cd Spandak8s

# Set up backend environment
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-hybrid.txt

# Start the backend (in a separate terminal)
python hybrid_main.py

# Use the CLI (in main directory)
python spandak8s --help
```

### Basic Usage

```bash
# Enable a module
python spandak8s enable security-vault --env langflow-dev

# Disable a module (removes PVCs by default)
python spandak8s disable security-vault --env langflow-dev

# Disable but keep data
python spandak8s disable security-vault --env langflow-dev --keep-data

# Complete cleanup (removes everything)
python spandak8s disable security-vault --env langflow-dev --complete-cleanup

# Check module status
python spandak8s modules status security-vault --env langflow-dev

# List available modules
python spandak8s modules list
```

## 🏗️ Architecture

### WSL-Integrated Hybrid Backend

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Spandak8s     │    │  Hybrid Backend  │    │   WSL Ubuntu    │
│      CLI        │◄──►│    FastAPI       │◄──►│                 │
│                 │    │                  │    │ • kubectl       │
│ • Rich UI       │    │ • No Auth        │    │ • helm          │
│ • Commands      │    │ • YAML Config    │    │ • Kind cluster  │
│ • Cleanup Opts  │    │ • WSL kubectl    │    │ • Kubeconfig    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Module Definitions│    │   Kubernetes    │
                       │    YAML File      │    │    Cluster      │
                       │                   │    │                 │
                       │ • Security-Vault  │    │ • Dynamic       │
                       │ • Data Lake       │    │   Namespaces    │
                       │ • Environment     │    │ • Helm Charts   │
                       │   Values          │    │ • Real-time     │
                       └──────────────────┘    └─────────────────┘
```

### Key Components

#### **1. CLI Interface (`spandak8s` command)**
- **Rich Terminal UI** with progress indicators and colored status
- **Environment Parsing** - Supports `--env tenant-environment` format
- **Resource Management** - Advanced cleanup options with clear warnings
- **Module Commands** - enable, disable, status, list

#### **2. Hybrid Backend (`backend/hybrid_main.py`)**
- **FastAPI Server** running on localhost:8000
- **WSL Integration** - Direct kubectl/helm execution through WSL
- **Dynamic Namespaces** - Tenant-environment namespace generation
- **Environment-Specific Values** - Automatic values-{env}.yaml file selection

#### **3. Module Definitions (`config/module-definitions.yaml`)**
- **Module Catalog** - Security-vault, data lake components, Kafka
- **Helm Configuration** - Chart paths, values, and dependencies
- **Resource Tiers** - Bronze, Standard, Premium resource allocations

## 📋 Command Reference

### Module Management

#### Enable/Deploy Modules

```bash
# Basic module deployment
python spandak8s enable security-vault --env langflow-dev
python spandak8s enable minio --env langflow-dev
python spandak8s enable kafka --env production-prod

# Alternative syntax
python spandak8s modules enable security-vault --env langflow-dev
```

#### Disable/Undeploy Modules

```bash
# Default: Remove module and PVCs (saves resources, data loss!)
python spandak8s disable security-vault --env langflow-dev

# Keep persistent data (preserves PVCs)
python spandak8s disable security-vault --env langflow-dev --keep-data

# Complete cleanup (removes ALL resources including secrets, RBAC, custom resources)
python spandak8s disable security-vault --env langflow-dev --complete-cleanup

# Keep data but cleanup other resources
python spandak8s disable security-vault --env langflow-dev --keep-data --complete-cleanup

# Preview what would be cleaned up (dry run)
python spandak8s disable security-vault --env langflow-dev --dry-run

# Force disable without confirmation
python spandak8s disable security-vault --env langflow-dev --force
```

### Comprehensive Resource Cleanup Matrix

| Option | Helm Resources | PVCs (Data) | Secrets | ServiceAccounts | RBAC (Roles) | NetworkPolicies | Ingresses | Custom Resources |
|--------|----------------|-------------|---------|-----------------|--------------|-----------------|-----------|------------------|
| **Default** | ❌ Removed | ❌ **DELETED** | ✅ Kept | ✅ Kept | ✅ Kept | ✅ Kept | ✅ Kept | ✅ Kept |
| **--keep-data** | ❌ Removed | ✅ **Preserved** | ✅ Kept | ✅ Kept | ✅ Kept | ✅ Kept | ✅ Kept | ✅ Kept |
| **--complete-cleanup** | ❌ Removed | ❌ **DELETED** | ❌ **DELETED** | ❌ **DELETED** | ❌ **DELETED** | ❌ **DELETED** | ❌ **DELETED** | ❌ **DELETED** |

### Custom Resources Cleaned Up

When using `--complete-cleanup`, the following Custom Resource Definitions (CRDs) are automatically cleaned:

- **Kafka Resources** (`kafkas.kafka.strimzi.io`, `kafkatopics.kafka.strimzi.io`, `kafkausers.kafka.strimzi.io`)
- **Vault Resources** (`vaults.vault.security.coreos.com`, `vaultpolicies.vault.security.coreos.com`)
- **Certificate Management** (`certificates.cert-manager.io`, `issuers.cert-manager.io`)
- **Module-Specific CRDs** (based on module patterns)

#### Status and Information

```bash
# Check specific module status
python spandak8s modules status security-vault --env langflow-dev

# List all available modules
python spandak8s modules list

# Check platform status
python spandak8s status

# Check cluster connectivity
python spandak8s status cluster
```

### Environment Variables and Configuration

```bash
# Backend configuration
export SPANDA_API_BASE_URL="http://localhost:8000"
export SPANDA_DEFAULT_TENANT="langflow"
export SPANDA_DEFAULT_ENVIRONMENT="dev"

# WSL paths (automatically handled)
# Windows: C:\Users\...\spandaai-platform-deployment
# WSL: /mnt/c/Users/.../spandaai-platform-deployment
```

## 🔧 Development Setup

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements-hybrid.txt

# Start development server
python hybrid_main.py

# Check health
curl http://localhost:8000/health
```

### CLI Development

```bash
# Install in development mode
pip install -e .

# Test CLI commands
python spandak8s --help
python spandak8s modules list

# Debug mode
python spandak8s --debug modules enable security-vault --env langflow-dev
```

### WSL Setup Verification

```bash
# Check WSL kubectl access
wsl -e bash -c "kubectl get nodes"

# Check WSL helm installation
wsl -e bash -c "helm version"

# Verify kubeconfig
wsl -e bash -c "kubectl config current-context"
```

## 🎯 Module Catalog

### Security Modules
- **security-vault** - HashiCorp Vault with keyholding and primary vault architecture
  - Dynamic namespace deployment
  - Environment-specific configurations (values-dev.yaml, values-prod.yaml)
  - Two-vault architecture with transit seal

### Data Lake Modules
- **minio** - S3-compatible object storage
- **spark** - Distributed data processing
- **dremio** - Data lake analytics platform
- **kafka** - Event streaming platform

### Resource Tiers
- **Bronze** - 10 CPU, 20Gi Memory, 100Gi Storage
- **Standard** - 20 CPU, 40Gi Memory, 500Gi Storage  
- **Premium** - 50 CPU, 100Gi Memory, 2Ti Storage

## 🚨 Important Notes

### Data Loss Warnings

⚠️ **Default disable behavior has changed** - By default, `spandak8s disable` now removes PVCs to save resources. This **WILL DELETE YOUR DATA**!

- Use `--keep-data` to preserve persistent volumes
- Always backup important data before disabling modules
- Test with non-production environments first

### Resource Management

- **PVCs consume disk space** - Clean them up when not needed
- **Secrets may contain credentials** - Use `--complete-cleanup` carefully
- **ServiceAccounts affect RBAC** - Review permissions before cleanup

### Namespace Strategy

- **Dynamic Namespaces** - Format: `{tenant}-{environment}` (e.g., `langflow-dev`)
- **Environment Isolation** - Each tenant-environment gets its own namespace
- **Global Values** - Namespaces are set dynamically via Helm `--set global.namespace=`

## 🔍 API Reference

### REST Endpoints

```bash
# Health check
GET http://localhost:8000/health

# List modules
GET http://localhost:8000/api/v1/modules

# Enable module
POST http://localhost:8000/api/v1/tenants/{tenant}/modules/{module}/enable
Query: environment=dev&tier=bronze

# Disable module with cleanup options
POST http://localhost:8000/api/v1/tenants/{tenant}/modules/{module}/disable  
Query: environment=dev&cleanup_pvcs=true&cleanup_all=false

# Module status
GET http://localhost:8000/api/v1/tenants/{tenant}/modules/{module}/status
Query: environment=dev
```

## 🐛 Troubleshooting

### Common Issues

**Backend connection failed:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check backend logs
cd backend
python hybrid_main.py
```

**WSL kubectl access failed:**
```bash
# Test WSL connectivity
wsl -e bash -c "kubectl get nodes"

# Check kubeconfig
wsl -e bash -c "echo $KUBECONFIG"

# Verify kubeconfig content
wsl -e bash -c "kubectl config view"
```

**Module deployment failed:**
```bash
# Check Helm charts exist
ls "../spandaai-platform-deployment/bare-metal/modules/"

# Check namespace
wsl -e bash -c "kubectl get ns langflow-dev"

# Check Helm releases
wsl -e bash -c "helm list -n langflow-dev"
```

**Permission denied:**
```bash
# Check current directory
pwd

# Verify Python environment
which python
python --version

# Check backend virtual environment
cd backend
venv\Scripts\activate
```

### Debug Mode

Enable detailed logging:

```bash
# CLI debug
python spandak8s --debug modules enable security-vault --env langflow-dev

# Backend debug (in backend/hybrid_main.py)
# Set logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

```bash
# Check all components
curl http://localhost:8000/health

# Test WSL integration
curl http://localhost:8000/api/v1/debug/k8s

# Check platform status
curl http://localhost:8000/api/v1/platform/status
```

## 📁 Project Structure

```
Spandak8s/
├── README.md                    # This comprehensive guide
├── spandak8s                    # Main CLI entry point
├── spandak8s-original           # Original CLI implementation
├── backend/
│   ├── hybrid_main.py          # FastAPI backend with WSL integration
│   ├── venv/                   # Backend virtual environment
│   └── requirements-hybrid.txt # Backend dependencies
├── cmd/
│   ├── modules.py              # Module management commands
│   ├── tenants.py              # Tenant commands  
│   └── status.py               # Status commands
├── pkg/
│   ├── api_client.py           # API client with cleanup options
│   └── config.py               # Configuration management
└── config/
    └── module-definitions.yaml # Module catalog and configuration
```

## 🤝 Contributing

We welcome contributions! Key areas:

- **New Modules** - Add module definitions and Helm charts
- **Environment Support** - Additional environment-specific configurations  
- **Resource Management** - Enhanced cleanup and monitoring
- **WSL Integration** - Improved cross-platform support

Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- 📖 Documentation: https://docs.spanda.ai
- 💬 Community: https://community.spanda.ai  
- 🐛 Issues: https://github.com/aryan-spanda/Spandak8s/issues
- 📧 Email: support@spanda.ai

---

**⚡ Quick Start**: `python spandak8s enable security-vault --env langflow-dev`

**⚠️ Data Safety**: Use `--keep-data` when disabling modules to preserve persistent volumes!
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

## 🏗️ Architecture

### Hybrid Backend Design

This platform uses a **hybrid architecture** that combines the best of database and stateless approaches:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Spandak8s     │    │  Hybrid Backend  │    │   Kubernetes    │
│      CLI        │◄──►│    FastAPI       │◄──►│    Cluster      │
│                 │    │                  │    │                 │
│ • Rich UI       │    │ • JWT Auth       │    │ • Real-time     │
│ • Commands      │    │ • YAML Config    │    │   Status        │
│ • Auth Token    │    │ • K8s Queries    │    │ • Deployments   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Module Definitions│
                       │    YAML File      │
                       │                   │
                       │ • 13 Modules      │
                       │ • 3 Tiers         │
                       │ • Dependencies    │
                       └──────────────────┘
```

### Key Components

#### **1. CLI Interface (`spandak8s` command)**
- **Rich Terminal UI** with beautiful tables and progress bars
- **Authentication** with automatic JWT token management  
- **Module Management** commands for listing, validating, and configuring
- **Tenant Operations** for creating and managing isolated environments
- **Cross-Platform** support (Windows PowerShell, Linux Bash, macOS Terminal)

#### **2. Hybrid Backend (`backend/hybrid_main.py`)**
- **FastAPI Server** running on `http://localhost:8000`
- **YAML Configuration** loaded from `config/module-definitions.yaml`
- **Real-time Monitoring** via direct Kubernetes API queries
- **JWT Authentication** with in-memory users (no database overhead)
- **Auto-reload** detects YAML file changes and reloads configuration

#### **3. Module Definitions (`config/module-definitions.yaml`)**
- **13 Platform Modules** across 6 categories
- **Resource Tiers** (Bronze/Standard/Premium) with CPU/memory limits
- **Dependency Management** with conflict detection
- **Default Configurations** for each module

#### **4. Kubernetes Integration**
- **Real-time Status** from live cluster (pod health, resource usage)
- **Tenant Namespaces** for multi-tenant isolation
- **Resource Quotas** enforced per tier and tenant
- **GitOps Ready** with ArgoCD integration

### Backend Quick Start

```powershell
# Start the hybrid backend
cd backend
.\start-hybrid.ps1

# Default users:
# Username: admin | Password: spanda123! | Roles: admin, user
# Username: user  | Password: user123!  | Roles: user

# API Documentation: http://localhost:8000/docs
# Health Check: http://localhost:8000/health
```

### Why Hybrid Architecture?

| Feature | Database Approach | Stateless Approach | **Hybrid Approach** |
|---------|------------------|-------------------|-------------------|
| **Complexity** | High | Low | **Medium** |
| **Real-time Data** | Stale | Perfect | **Perfect** |
| **Authentication** | Full | None | **Simple** |
| **Dependencies** | 20+ packages | 3 packages | **6 packages** |
| **Setup Time** | 30+ minutes | 5 minutes | **10 minutes** |
| **Database Required** | PostgreSQL + Redis | None | **None** |
| **Production Ready** | Yes | Limited | **Yes** |

**Result**: Get real-time monitoring with simple authentication, without database complexity! 🎯

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

## 🔧 Development & Testing

### Backend Development

The hybrid backend provides a development-friendly environment:

```powershell
# Backend development setup
cd backend

# Start backend with auto-reload
.\start-hybrid.ps1

# Run tests
pip install pytest httpx
pytest test_hybrid.py -v

# Available test endpoints:
# - Authentication (login/logout)
# - Module management (list/validate)
# - Tenant operations (status/config)
# - Platform monitoring (health/status)
```

### CLI Development

```bash
# Install in development mode
pip install -e .

# Test CLI with backend
spandak8s login        # Username: admin, Password: spanda123!
spandak8s modules list # Should show modules from YAML
spandak8s status platform

# Run CLI tests
python -m pytest tests/ -v
```

### Backend Files Structure

```
backend/
├── hybrid_main.py           # Main FastAPI application (580 lines)
├── requirements-hybrid.txt  # Minimal dependencies (6 packages)
├── start-hybrid.ps1        # Windows setup script
├── test_hybrid.py          # Comprehensive test suite
└── .env                    # Auto-generated configuration
```

### Recent Architecture Changes

#### ✅ **Hybrid Backend Implementation** 
- **Why**: User questioned "why would we need database when we are checking realtime"
- **Solution**: Created hybrid approach combining YAML configs + real-time K8s + JWT auth
- **Result**: Only 6 dependencies vs 20+ in database version, no PostgreSQL needed

#### ✅ **Configuration Updates**
- **Updated**: `pkg/config.py` with JWT token management
- **Added**: Authentication helper methods (`set_auth_token`, `clear_auth`, `get_auth_headers`)
- **Changed**: Default API URL from `:8080` to `:8000` for hybrid backend

#### ✅ **CLI Authentication Integration**
- **Added**: Login/logout/whoami commands to main CLI
- **Updated**: `pkg/api_client.py` completely rewritten for hybrid backend
- **Removed**: Old database-dependent imports and methods

#### ✅ **File Cleanup**
- **Removed**: Redundant backend files (main.py, stateless_main.py, docker configs)
- **Kept**: Only essential files for hybrid approach
- **Consolidated**: Multiple documentation files into single README

### File Cleanup Summary

**Removed Files:**
- `backend/main.py` (database version)
- `backend/stateless_main.py` (stateless version)  
- `backend/docker-compose.yml` (database dependencies)
- `backend/requirements.txt` (heavy dependencies)
- Multiple documentation files (consolidated into this README)

**Current Clean Structure:**
```
Spandak8s/
├── README.md                 # This comprehensive guide
├── CHANGELOG.md             # Version history
├── spandak8s                # Main CLI entry point
├── pkg/                     # CLI packages
│   ├── config.py           # Configuration with JWT support
│   └── api_client.py       # Hybrid backend integration
├── config/
│   └── module-definitions.yaml  # Platform modules
└── backend/                 # Hybrid backend (6 files only)
    ├── hybrid_main.py
    ├── requirements-hybrid.txt
    ├── start-hybrid.ps1
    ├── test_hybrid.py
    └── .env
```

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
