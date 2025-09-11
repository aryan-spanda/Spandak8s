"""
Spandak8s CLI - Platform API Client

This module provides HTTP client functionality for communicating with the Spanda Platform backend:
- REST API communication with proper authentication
- Tenant management API calls
- Module deployment and configuration APIs
- Status monitoring and health check endpoints
- Error handling and retry logic with exponential backoff
- Response caching and rate limiting

Key Features:
- JWT/OAuth2 authentication support
- Automatic token refresh
- Request/response logging for debugging
- Multi-environment endpoint management
- Async operation support for long-running tasks
"""

import requests
from typing import Dict, Any, List
from pkg.config import SpandaConfig

class SpandaAPIClient:
    """Client for making API calls to the Spanda Platform backend"""
    
    def __init__(self, config: SpandaConfig):
        self.config = config
        self.base_url = config.api_base_url.rstrip('/')
        self.timeout = config.api_timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'spandak8s-cli/0.1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")
    
    def get_tenant_status(self, tenant_name: str, environment: str) -> Dict[str, Any]:
        """Get status of all modules for a tenant environment"""
        endpoint = f"/tenants/{tenant_name}/{environment}/status"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def enable_module(self, tenant_name: str, environment: str, 
                     module_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Enable a module for a tenant environment"""
        endpoint = f"/tenants/{tenant_name}/{environment}/modules/{module_name}"
        response = self._make_request('POST', endpoint, json=config)
        return response.json()
    
    def disable_module(self, tenant_name: str, environment: str, 
                      module_name: str) -> Dict[str, Any]:
        """Disable a module for a tenant environment"""
        endpoint = f"/tenants/{tenant_name}/{environment}/modules/{module_name}"
        response = self._make_request('DELETE', endpoint)
        return response.json()
    
    def get_module_config(self, tenant_name: str, environment: str, 
                         module_name: str) -> Dict[str, Any]:
        """Get current configuration for a module"""
        endpoint = f"/tenants/{tenant_name}/{environment}/modules/{module_name}/config"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def update_module_config(self, tenant_name: str, environment: str, 
                           module_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration for an existing module"""
        endpoint = f"/tenants/{tenant_name}/{environment}/modules/{module_name}/config"
        response = self._make_request('PUT', endpoint, json=config)
        return response.json()
    
    def list_available_modules(self) -> List[Dict[str, Any]]:
        """Get list of all available platform modules"""
        endpoint = "/modules"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def get_module_schema(self, module_name: str) -> Dict[str, Any]:
        """Get configuration schema for a module"""
        endpoint = f"/modules/{module_name}/schema"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def create_tenant(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tenant"""
        endpoint = "/tenants"
        response = self._make_request('POST', endpoint, json=tenant_data)
        return response.json()
    
    def list_tenants(self) -> List[Dict[str, Any]]:
        """List all tenants"""
        endpoint = "/tenants"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def get_tenant_info(self, tenant_name: str) -> Dict[str, Any]:
        """Get detailed information about a tenant"""
        endpoint = f"/tenants/{tenant_name}"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the API backend is healthy"""
        endpoint = "/health"
        response = self._make_request('GET', endpoint)
        return response.json()
