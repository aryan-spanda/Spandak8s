"""
Spandak8s CLI - Hybrid Backend API Client

This module provides HTTP client functionality for communicating with the Spanda Platform hybrid backend:
- JWT authentication and session management
- Module definitions and validation
- Real-time tenant status monitoring  
- Configuration generation and deployment
- Health checking and platform status

Key Features:
- JWT authentication with automatic header injection
- RESTful API communication
- Error handling with descriptive messages
- Session management with token storage
"""

import requests
from typing import Dict, Any, List
from pkg.config import SpandaConfig

class SpandaAPIClient:
    """Client for making API calls to the Spanda Platform hybrid backend"""
    
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
        
        # Add authentication headers if available
        auth_headers = config.get_auth_headers()
        if auth_headers:
            self.session.headers.update(auth_headers)
    
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
    
    # Authentication methods
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login to the backend and get JWT token"""
        endpoint = "/api/v1/auth/login"
        payload = {"username": username, "password": password}
        
        # Temporarily remove auth headers for login
        old_headers = self.session.headers.copy()
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        try:
            response = self._make_request('POST', endpoint, json=payload)
            result = response.json()
            
            # Update session headers with new token
            if 'access_token' in result:
                self.session.headers['Authorization'] = f"Bearer {result['access_token']}"
            
            return result
        finally:
            # Restore original headers if login failed
            if 'access_token' not in locals() or not locals().get('result', {}).get('access_token'):
                self.session.headers = old_headers
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the API backend is healthy"""
        endpoint = "/health"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    # Module management methods
    def get_all_definitions(self) -> Dict[str, Any]:
        """Fetch complete module definitions from the backend API"""
        endpoint = "/api/v1/modules/definitions"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def list_modules(self) -> List[Dict[str, Any]]:
        """Get list of all available platform modules"""
        endpoint = "/api/v1/modules"
        response = self._make_request('GET', endpoint)
        return response.json().get('modules', [])
    
    def get_module_details(self, module_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific module"""
        endpoint = f"/api/v1/modules/{module_name}"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def validate_modules(self, modules: List[str]) -> Dict[str, Any]:
        """Validate module list and check dependencies"""
        endpoint = "/api/v1/modules/validate"
        payload = {"modules": modules}
        response = self._make_request('POST', endpoint, json=payload)
        return response.json()
    
    def check_module_health(self, module_name: str, tenant_name: str = None) -> Dict[str, Any]:
        """Check health status of a specific module"""
        endpoint = f"/api/v1/modules/{module_name}/health"
        params = {}
        if tenant_name:
            params['tenant_name'] = tenant_name
        response = self._make_request('GET', endpoint, params=params)
        return response.json()
    
    # Tenant management methods
    def list_tenants(self) -> List[Dict[str, Any]]:
        """List all tenants from Kubernetes"""
        endpoint = "/api/v1/tenants"
        response = self._make_request('GET', endpoint)
        return response.json().get('tenants', [])
    
    def get_tenant_status(self, tenant_name: str) -> Dict[str, Any]:
        """Get real-time status of a tenant from Kubernetes"""
        endpoint = f"/api/v1/tenants/{tenant_name}/status"
        response = self._make_request('GET', endpoint)
        return response.json()
    
    def generate_tenant_config(self, tenant_name: str, modules: List[str], 
                             tier: str, custom_resources: Dict = None) -> Dict[str, Any]:
        """Generate tenant configuration via backend API"""
        payload = {
            'tenant_name': tenant_name,
            'modules': modules,
            'tier': tier
        }
        if custom_resources:
            payload['custom_resources'] = custom_resources
            
        endpoint = "/api/v1/tenants/generate-config"
        response = self._make_request('POST', endpoint, json=payload)
        return response.json()
    
    def deploy_tenant_config(self, tenant_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy tenant configuration via backend API"""
        endpoint = "/api/v1/tenants/deploy"
        payload = {"tenant_config": tenant_config}
        response = self._make_request('POST', endpoint, json=payload, timeout=self.timeout * 3)
        return response.json()
    
    # Platform status methods
    def get_platform_status(self) -> Dict[str, Any]:
        """Get overall platform status from Kubernetes"""
        endpoint = "/api/v1/platform/status"
        response = self._make_request('GET', endpoint)
        return response.json()
