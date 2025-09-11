"""
Spandak8s CLI - Configuration Management

This module handles all configuration aspects of the CLI including:
- Loading and managing user configuration files (~/.spanda/config.yaml)
- Platform connection settings (API endpoints, authentication)
- Default values for commands and operations
- Environment-specific configurations
- Configuration validation and error handling

Key Features:
- Automatic config file creation and setup
- Environment variable override support
- Secure credential management
- Multi-environment configuration support (dev/staging/prod)
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any

class SpandaConfig:
    """Handles configuration loading and management for the CLI"""
    
    def __init__(self, config_path: str = "~/.spanda/config.yaml"):
        self.config_path = Path(config_path).expanduser()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if not self.config_path.exists():
            return self._create_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise Exception(f"Failed to load config from {self.config_path}: {e}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'api': {
                'base_url': 'http://localhost:8080',
                'timeout': 30,
                'verify_ssl': True
            },
            'kubernetes': {
                'config_path': '~/.kube/config',
                'context': None  # Use current context
            },
            'tenant': {
                'name': 'default',
                'namespace_prefix': 'tenant'
            },
            'charts': {
                'path': '/opt/spandak8s/charts',  # In snap, this will be the charts location
                'repository': {
                    'name': 'spanda-platform',
                    'url': 'https://charts.spanda.ai'  # When you publish charts
                }
            },
            'defaults': {
                'environment': 'dev',
                'storage_class': 'standard',
                'replicas': 1
            }
        }
        
        # Create config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save default config
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        
        return default_config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'api.base_url')"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the final key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
        
        # Save to file
        self.save()
    
    def save(self) -> None:
        """Save current configuration to file"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
    
    @property
    def api_base_url(self) -> str:
        return self.get('api.base_url', 'http://localhost:8080')
    
    @property
    def api_timeout(self) -> int:
        return self.get('api.timeout', 30)
    
    @property
    def tenant_name(self) -> str:
        return self.get('tenant.name', 'default')
    
    @property
    def charts_path(self) -> str:
        # In snap environment, charts will be at /snap/spandak8s/current/charts
        snap_path = os.environ.get('SNAP')
        if snap_path:
            return f"{snap_path}/charts"
        return self.get('charts.path', '../spandaai-platform-deployment/bare-metal/modules')
    
    @property
    def kubeconfig_path(self) -> str:
        return self.get('kubernetes.config_path', '~/.kube/config')
    
    @property
    def default_environment(self) -> str:
        return self.get('defaults.environment', 'dev')
    
    @property
    def default_storage_class(self) -> str:
        return self.get('defaults.storage_class', 'standard')
