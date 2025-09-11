"""
Spandak8s CLI - Module Definitions Management

This module provides the core functionality for managing platform module definitions:
- Loading module definitions from YAML configuration files
- Managing resource quotas and tiers (Bronze/Standard/Premium)
- Generating tenant configurations with selected modules
- Validating module dependencies and compatibility
- Handling module categories and resource allocation

Key Classes:
- ModuleDefinitions: Main loader and management class
- Resource tier management (Bronze: 10 CPU/20Gi, Standard: 20 CPU/40Gi, Premium: 50 CPU/100Gi)
- Module validation and dependency checking

Configuration Source: config/module-definitions.yaml
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

from rich.console import Console

console = Console()

class ModuleDefinitions:
    """Manages module definitions and resource templates"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with optional custom config path"""
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Look for config in standard locations
            possible_paths = [
                Path(__file__).parent.parent / "config" / "module-definitions.yaml",
                Path("/opt/spandak8s/config/module-definitions.yaml"),
                Path("./config/module-definitions.yaml")
            ]
            
            self.config_path = None
            for path in possible_paths:
                if path.exists():
                    self.config_path = path
                    break
        
        self._definitions = None
        self._load_definitions()
    
    def _load_definitions(self):
        """Load module definitions from YAML file"""
        if not self.config_path or not self.config_path.exists():
            console.print("[red]Warning: Module definitions file not found, using defaults[/red]")
            self._definitions = self._get_default_definitions()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._definitions = yaml.safe_load(file)
        except Exception as e:
            console.print(f"[red]Error loading module definitions: {e}[/red]")
            self._definitions = self._get_default_definitions()
    
    def _get_default_definitions(self) -> Dict[str, Any]:
        """Return default module definitions if config file not found"""
        return {
            "modules": {
                "data-lake-baremetal": {
                    "name": "data-lake-baremetal",
                    "display_name": "Data Lake Platform",
                    "description": "Complete data lake platform with MinIO, Spark, Dremio",
                    "version": "1.0.0",
                    "category": "data-storage",
                    "dependencies": [],
                    "chart_path": "data-lake-baremetal"
                }
            },
            "categories": {
                "data-storage": {
                    "name": "Data Storage",
                    "description": "Data storage and lake management modules",
                    "icon": "💾"
                }
            },
            "resource_templates": {
                "standard": {
                    "name": "Standard Tier",
                    "description": "Standard resource allocation",
                    "resource_quota": {
                        "requests.cpu": "20",
                        "requests.memory": "40Gi",
                        "limits.cpu": "20",
                        "limits.memory": "40Gi",
                        "persistentvolumeclaims": "10",
                        "requests.storage": "100Gi"
                    }
                }
            }
        }
    
    def get_all_modules(self) -> Dict[str, Any]:
        """Get all available module definitions"""
        return self._definitions.get("modules", {})
    
    def get_module(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific module definition by name"""
        return self._definitions.get("modules", {}).get(name)
    
    def get_modules_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all modules in a specific category"""
        modules = []
        for module_name, module_def in self._definitions.get("modules", {}).items():
            if module_def.get("category") == category:
                modules.append(module_def)
        return modules
    
    def get_categories(self) -> Dict[str, Any]:
        """Get all module categories"""
        return self._definitions.get("categories", {})
    
    def get_resource_templates(self) -> Dict[str, Any]:
        """Get all resource quota templates"""
        return self._definitions.get("resource_templates", {})
    
    def get_resource_template(self, tier: str) -> Optional[Dict[str, Any]]:
        """Get specific resource quota template by tier"""
        return self._definitions.get("resource_templates", {}).get(tier)
    
    def generate_tenant_values(self, 
                             namespace: str, 
                             modules: List[str], 
                             resource_tier: str = "standard",
                             storage_class: str = "standard") -> Dict[str, Any]:
        """Generate complete tenant values file with resource quotas and enabled modules"""
        
        # Get resource template
        resource_template = self.get_resource_template(resource_tier)
        if not resource_template:
            console.print(f"[yellow]Warning: Resource tier '{resource_tier}' not found, using standard[/yellow]")
            resource_template = self.get_resource_template("standard")
        
        # Base tenant configuration
        tenant_config = {
            "global": {
                "namespace": namespace,
                "storageClass": storage_class
            },
            "resourceQuota": {
                "enabled": True,
                "hard": resource_template["resource_quota"]
            }
        }
        
        # Add enabled modules with their default configurations
        all_modules = self.get_all_modules()
        for module_name in modules:
            module_def = all_modules.get(module_name)
            if module_def:
                # Enable the module with its default configuration
                tenant_config[module_name] = {
                    "enabled": True,
                    "version": module_def.get("version", "1.0.0"),
                    "description": module_def.get("description", ""),
                    "values": module_def.get("default_config", {})
                }
                
                # Update namespace in module config if tenant_scope is true
                if module_def.get("default_config", {}).get("tenant_scope", True):
                    if "values" not in tenant_config[module_name]:
                        tenant_config[module_name]["values"] = {}
                    if "global" not in tenant_config[module_name]["values"]:
                        tenant_config[module_name]["values"]["global"] = {}
                    
                    tenant_config[module_name]["values"]["global"]["namespace"] = namespace
                    tenant_config[module_name]["values"]["global"]["storageClass"] = storage_class
            else:
                # Module not found, add as disabled
                tenant_config[module_name] = {"enabled": False}
        
        # Add all other modules as disabled
        for module_name in all_modules:
            if module_name not in tenant_config:
                tenant_config[module_name] = {"enabled": False}
        
        return tenant_config
    
    def list_available_modules(self) -> List[Dict[str, Any]]:
        """Get list of available modules formatted for CLI display"""
        modules = []
        for module_name, module_def in self.get_all_modules().items():
            category_info = self.get_categories().get(module_def.get("category", ""), {})
            
            modules.append({
                "name": module_name,
                "display_name": module_def.get("display_name", module_name),
                "description": module_def.get("description", ""),
                "version": module_def.get("version", "latest"),
                "category": module_def.get("category", "unknown"),
                "category_icon": category_info.get("icon", "📦"),
                "dependencies": module_def.get("dependencies", []),
                "chart_path": module_def.get("chart_path", module_name)
            })
        
        return modules
    
    def validate_dependencies(self, modules: List[str]) -> tuple[bool, List[str]]:
        """Validate that all module dependencies are satisfied"""
        all_modules = self.get_all_modules()
        missing_deps = []
        
        for module_name in modules:
            module_def = all_modules.get(module_name)
            if module_def:
                deps = module_def.get("dependencies", [])
                for dep in deps:
                    if dep not in modules:
                        missing_deps.append(f"{module_name} requires {dep}")
        
        return len(missing_deps) == 0, missing_deps

# Global instance
module_definitions = ModuleDefinitions()
