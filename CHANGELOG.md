# Changelog

All notable changes to the Spandak8s CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Resource quota management with bronze/standard/premium tiers
- Module definitions system with 13 platform modules
- Generate tenant configuration command
- Module category listing and organization
- Rich CLI output with tables and progress indicators

## [0.1.0] - 2025-09-10

### Added
- Initial release of Spandak8s CLI
- Module management commands (enable, disable, configure, list)
- Tenant management commands
- Status and health monitoring commands
- Kubernetes integration with fallback support
- API client for backend communication
- Snap packaging for Linux distribution
- Configuration management system
- Module detection and health checking utilities
- Professional CLI with Rich library integration
- Platform-managed resource allocation model

### Features
- **Module Management**: Enable, disable, configure, and list platform modules
- **Resource Quotas**: Three-tier resource allocation (bronze/standard/premium)
- **Tenant Configuration**: Generate complete tenant YAML configurations
- **Kubernetes Integration**: Direct cluster operations with kubectl/helm
- **API-First Design**: Backend API with Kubernetes fallback
- **Rich CLI Experience**: Colored output, progress bars, formatted tables
- **Snap Distribution**: Professional Linux packaging with dependencies
- **Module Categories**: Organized modules by Data Storage, Analytics, Security, etc.
- **Dependency Validation**: Automatic module dependency checking
- **Configuration Templates**: Predefined module configurations

### Supported Modules
- **Data Storage**: data-lake-baremetal (MinIO, Spark, Dremio)
- **Data Management**: data-management-complete (ETL, workflows)
- **Analytics & BI**: traditional-bi-baremetal, realtime-bi-baremetal
- **Monitoring**: monitoring-prometheus (Prometheus, Grafana, AlertManager)
- **Security**: security-vault, security-cert-manager
- **Networking**: 6 networking modules (VPC, load balancers, firewall)

### Technical Details
- Python 3.8+ compatibility
- Click framework for CLI commands
- Rich library for beautiful terminal output
- YAML configuration management
- Kubernetes API integration
- PostgreSQL backend support
- Helm chart integration
- Strict Snap confinement for security

### Installation Methods
- Snap Store: `snap install spandak8s`
- PyPI: `pip install spandak8s`
- Direct download from GitHub releases
- Docker container: `docker run spandaai/spandak8s`

## [0.0.1] - 2025-09-01

### Added
- Project initialization
- Basic CLI structure
- Initial architecture planning
