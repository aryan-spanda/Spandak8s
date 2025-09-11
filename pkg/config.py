"""
Spandak8s CLI - Configuration Management

This module handles all configuration aspects of the CLI including:
- Loading and managing user configuration files (~/.spanda/config.yaml)
- Backend API connection settings (authentication, endpoints)
- JWT token management and authentication
- Default values for commands and operations
- Environment-specific configurations

Key Features:
- Automatic config file creation and setup
- JWT token storage and management
- Backend API authentication
- Kubernetes configuration integration
- Multi-environment support (dev/staging/prod)
"""

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
                'base_url': 'http://localhost:8000',  # Updated for hybrid backend
                'timeout': 30,
                'verify_ssl': True
            },
            'auth': {
                'token': None,  # JWT token storage
                'username': None,  # Last logged in user
                'expires_at': None  # Token expiration
            },
            'kubernetes': {
                'config_path': '~/.kube/config',
                'context': None  # Use current context
            },
            'tenant': {
                'name': 'default',
                'namespace_prefix': 'tenant'
            },
            'defaults': {
                'environment': 'dev',
                'storage_class': 'standard',
                'replicas': 1,
                'tier': 'bronze'  # Default resource tier
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
        return self.get('api.base_url', 'http://localhost:8000')
    
    @property
    def api_timeout(self) -> int:
        return self.get('api.timeout', 30)
    
    @property
    def auth_token(self) -> str:
        """Get stored JWT token"""
        return self.get('auth.token')
    
    @property
    def auth_username(self) -> str:
        """Get last logged in username"""
        return self.get('auth.username')
    
    def set_auth_token(self, token: str, username: str = None) -> None:
        """Store JWT token and username"""
        self.set('auth.token', token)
        if username:
            self.set('auth.username', username)
        self.save()
    
    def clear_auth(self) -> None:
        """Clear stored authentication"""
        self.set('auth.token', None)
        self.set('auth.username', None)
        self.set('auth.expires_at', None)
        self.save()
    
    def is_authenticated(self) -> bool:
        """Check if user has valid authentication"""
        return bool(self.auth_token)

    @property
    def tenant_name(self) -> str:
        return self.get('tenant.name', 'default')
    
    @property
    def kubeconfig_path(self) -> str:
        return self.get('kubernetes.config_path', '~/.kube/config')
    
    @property
    def default_environment(self) -> str:
        return self.get('defaults.environment', 'dev')
    
    @property
    def default_storage_class(self) -> str:
        return self.get('defaults.storage_class', 'standard')
    
    @property
    def default_tier(self) -> str:
        return self.get('defaults.tier', 'bronze')
    
    def get_auth_headers(self) -> dict:
        """Get HTTP headers for authenticated requests"""
        token = self.auth_token
        if token:
            return {'Authorization': f'Bearer {token}'}
        return {}
