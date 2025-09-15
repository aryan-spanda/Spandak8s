"""
Hybrid Spandak8s Backend API

This approach combines the best of both worlds:
1. Real-time status checking from Kubernetes (no database needed)
2. Module definitions loaded from local YAML file (your existing config)
3. Simple deployment without authentication

Architecture:
- Module definitions: Load from local YAML file (config/module-definitions.yaml)
- Real-time status: Query Kubernetes directly
- No authentication: Direct API access for module enable/disable
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import yaml
import logging
import os
from datetime import datetime
from kubernetes import client, config
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Spandak8s Hybrid API",
    description="Hybrid API: YAML configs + Kubernetes real-time",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Kubernetes client  
k8s_core = None
k8s_apps = None

try:
    config.load_incluster_config()  # If running in cluster
    logger.info("Loaded in-cluster Kubernetes config")
except Exception:
    try:
        # For WSL-based clusters, we need to use the WSL kubeconfig from Windows
        import subprocess
        import tempfile
        
        # Get the kubeconfig from WSL
        result = subprocess.run(
            ["wsl", "cat", "/home/aryanpola/.kube/config"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Write the WSL kubeconfig to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
                f.write(result.stdout)
                temp_kubeconfig = f.name
            
            # Load the kubeconfig
            config.load_kube_config(config_file=temp_kubeconfig)
            logger.info("Loaded kubeconfig from WSL")
            
            # Clean up temp file
            os.unlink(temp_kubeconfig)
        else:
            raise Exception("Could not read WSL kubeconfig")
            
    except Exception as e:
        logger.warning(f"Could not load WSL kubeconfig: {e}")
        try:
            # Fallback to default Windows kubeconfig loading
            config.load_kube_config()
            logger.info("Loaded local Windows kubeconfig")
        except Exception as e2:
            logger.warning(f"Could not load any Kubernetes config: {e2}")

# Initialize Kubernetes API clients
try:
    k8s_core = client.CoreV1Api()
    k8s_apps = client.AppsV1Api()
    logger.info("Kubernetes API clients initialized")
except Exception as e:
    logger.error(f"Failed to initialize Kubernetes clients: {e}")
    k8s_core = None
    k8s_apps = None

# Load module definitions from YAML file
def load_module_definitions():
    """Load module definitions from local YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "module-definitions.yaml"
    
    if not config_path.exists():
        logger.error(f"Module definitions file not found: {config_path}")
        # Return minimal default configuration
        return {
            "modules": {},
            "resource_tiers": {
                "bronze": {"cpu": "10", "memory": "20Gi", "storage": "100Gi"},
                "standard": {"cpu": "20", "memory": "40Gi", "storage": "500Gi"},
                "premium": {"cpu": "50", "memory": "100Gi", "storage": "2Ti"}
            }
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            definitions = yaml.safe_load(f)
            logger.info(f"Loaded {len(definitions.get('modules', {}))} module definitions")
            return definitions
    except Exception as e:
        logger.error(f"Error loading module definitions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load module definitions: {e}")

# Cache module definitions (reload when file changes)
_module_definitions = None
_last_modified = None

def get_module_definitions():
    """Get module definitions with file change detection"""
    global _module_definitions, _last_modified
    
    config_path = Path(__file__).parent.parent / "config" / "module-definitions.yaml"
    
    if config_path.exists():
        current_modified = config_path.stat().st_mtime
        if _module_definitions is None or current_modified != _last_modified:
            _module_definitions = load_module_definitions()
            _last_modified = current_modified
            logger.info("Reloaded module definitions due to file change")
    else:
        if _module_definitions is None:
            _module_definitions = load_module_definitions()
    
    return _module_definitions

# Pydantic Models
class ModuleValidationRequest(BaseModel):
    modules: List[str] = Field(..., description="List of module names to validate")

class TenantConfigRequest(BaseModel):
    tenant_name: str = Field(..., description="Name of the tenant")
    modules: List[str] = Field(..., description="List of modules to enable")
    tier: str = Field(..., description="Resource tier (bronze/standard/premium)")
    custom_resources: Optional[Dict[str, Any]] = Field(None, description="Custom resource overrides")

class TenantDeployRequest(BaseModel):
    tenant_config: Dict[str, Any] = Field(..., description="Complete tenant configuration")

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    components: Dict[str, str]

# Kubernetes helper functions
def get_deployed_modules(namespace: str) -> List[Dict[str, Any]]:
    """Get list of deployed modules in a namespace with their status"""
    try:
        deployments = k8s_apps.list_namespaced_deployment(namespace=namespace)
        modules = []
        
        for deployment in deployments.items:
            labels = deployment.metadata.labels or {}
            if "spanda.ai/module" in labels:
                modules.append({
                    "name": labels.get("spanda.ai/module", "unknown"),
                    "type": "deployment",
                    "status": "running" if deployment.status.ready_replicas else "pending",
                    "replicas": deployment.status.replicas or 0,
                    "ready_replicas": deployment.status.ready_replicas or 0
                })
        
        # Also check StatefulSets
        statefulsets = k8s_apps.list_namespaced_stateful_set(namespace=namespace)
        for sts in statefulsets.items:
            labels = sts.metadata.labels or {}
            if "spanda.ai/module" in labels:
                modules.append({
                    "name": labels.get("spanda.ai/module", "unknown"),
                    "type": "statefulset",
                    "status": "running" if sts.status.ready_replicas else "pending",
                    "replicas": sts.status.replicas or 0,
                    "ready_replicas": sts.status.ready_replicas or 0
                })
                
        return modules
        
    except Exception as e:
        logger.error(f"Error getting deployed modules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get deployed modules: {e}")

# API Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    k8s_status = "healthy"
    try:
        k8s_core.list_namespace(limit=1)
    except Exception:
        k8s_status = "unhealthy"
        
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        components={
            "api": "healthy",
            "kubernetes": k8s_status,
            "module_definitions": "healthy"
        }
    )

@app.get("/api/v1/modules/definitions")
async def get_module_definitions_api():
    """Get complete module definitions from YAML file"""
    logger.info("Guest user requested module definitions")
    return get_module_definitions()

@app.get("/api/v1/modules")
async def list_modules():
    """Get list of all available platform modules"""
    definitions = get_module_definitions()
    modules = []
    
    for name, data in definitions.get("modules", {}).items():
        modules.append({
            "name": name,
            "display_name": data.get("display_name", name),
            "description": data.get("description", ""),
            "version": data.get("version", "1.0.0"),
            "category": data.get("category", "other"),
            "dependencies": data.get("dependencies", [])
        })
    
    return {"modules": modules}

@app.get("/api/v1/modules/{module_name}")
async def get_module_details(module_name: str):
    """Get detailed information about a specific module"""
    definitions = get_module_definitions()
    
    if module_name not in definitions.get("modules", {}):
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
    
    return definitions["modules"][module_name]

@app.post("/api/v1/modules/validate")
async def validate_modules(request: ModuleValidationRequest):
    """Validate if modules exist and check dependencies"""
    definitions = get_module_definitions()
    available_modules = definitions.get("modules", {})
    
    validation_results = []
    
    for module_name in request.modules:
        if module_name in available_modules:
            module = available_modules[module_name]
            dependencies = module.get("dependencies", [])
            
            # Check if dependencies are also in the request
            missing_deps = [dep for dep in dependencies if dep not in request.modules]
            
            validation_results.append({
                "module": module_name,
                "valid": True,
                "dependencies": dependencies,
                "missing_dependencies": missing_deps
            })
        else:
            validation_results.append({
                "module": module_name,
                "valid": False,
                "error": "Module not found"
            })
    
    return {"validation_results": validation_results}

@app.get("/api/v1/tenants")
async def list_tenants():
    """Get list of tenant namespaces from Kubernetes"""
    try:
        namespaces = k8s_core.list_namespace()
        tenant_namespaces = []
        
        for ns in namespaces.items:
            labels = ns.metadata.labels or {}
            if "spanda.ai/tenant" in labels:
                tenant_name = labels.get("spanda.ai/tenant")
                environment = labels.get("spanda.ai/environment", "dev")
                
                # Get deployed modules for this tenant
                deployed_modules = get_deployed_modules(ns.metadata.name)
                
                tenant_namespaces.append({
                    "tenant": tenant_name,
                    "environment": environment,
                    "namespace": ns.metadata.name,
                    "deployed_modules": deployed_modules,
                    "created": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None
                })
        
        return {"tenants": tenant_namespaces}
        
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tenants: {e}")

@app.get("/api/v1/tenants/{tenant_name}/status")
async def get_tenant_status(tenant_name: str):
    """Get comprehensive status of a tenant across all environments"""
    try:
        namespaces = k8s_core.list_namespace()
        tenant_status = {
            "tenant": tenant_name,
            "environments": []
        }
        
        for ns in namespaces.items:
            labels = ns.metadata.labels or {}
            if labels.get("spanda.ai/tenant") == tenant_name:
                environment = labels.get("spanda.ai/environment", "dev")
                deployed_modules = get_deployed_modules(ns.metadata.name)
                
                env_status = {
                    "environment": environment,
                    "namespace": ns.metadata.name,
                    "status": "running" if deployed_modules else "empty",
                    "modules": deployed_modules,
                    "created": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None
                }
                tenant_status["environments"].append(env_status)
        
        if not tenant_status["environments"]:
            raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
            
        return tenant_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tenant status: {e}")

@app.get("/api/v1/modules/{module_name}/health")
async def check_module_health(module_name: str):
    """Check health status of a specific module across all deployments"""
    try:
        all_namespaces = k8s_core.list_namespace()
        module_instances = []
        
        for ns in all_namespaces.items:
            deployed_modules = get_deployed_modules(ns.metadata.name)
            for module in deployed_modules:
                if module["name"] == module_name:
                    module_instances.append({
                        "namespace": ns.metadata.name,
                        "tenant": ns.metadata.labels.get("spanda.ai/tenant", "unknown"),
                        "environment": ns.metadata.labels.get("spanda.ai/environment", "dev"),
                        **module
                    })
        
        if not module_instances:
            return {
                "module": module_name,
                "status": "not_deployed",
                "instances": []
            }
        
        # Determine overall health
        healthy_instances = [inst for inst in module_instances if inst["status"] == "running"]
        overall_status = "healthy" if len(healthy_instances) == len(module_instances) else "degraded"
        
        return {
            "module": module_name,
            "status": overall_status,
            "instances": module_instances,
            "summary": {
                "total_instances": len(module_instances),
                "healthy_instances": len(healthy_instances)
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking module health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check module health: {e}")

@app.post("/api/v1/tenants/generate-config")
async def generate_tenant_config(request: TenantConfigRequest):
    """Generate Kubernetes manifests for a tenant configuration"""
    definitions = get_module_definitions()
    available_modules = definitions.get("modules", {})
    resource_tiers = definitions.get("resource_tiers", {})
    
    # Validate modules
    for module_name in request.modules:
        if module_name not in available_modules:
            raise HTTPException(status_code=400, detail=f"Module '{module_name}' not found")
    
    # Validate tier
    if request.tier not in resource_tiers:
        raise HTTPException(status_code=400, detail=f"Resource tier '{request.tier}' not found")
    
    # Generate configuration
    tenant_config = {
        "tenant": {
            "name": request.tenant_name,
            "tier": request.tier,
            "resources": resource_tiers[request.tier]
        },
        "modules": {},
        "kubernetes_manifests": {
            "namespace": f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {request.tenant_name}
  labels:
    spanda.ai/tenant: {request.tenant_name}
    spanda.ai/tier: {request.tier}
"""
        }
    }
    
    # Add module configurations
    for module_name in request.modules:
        module_def = available_modules[module_name]
        tenant_config["modules"][module_name] = {
            "enabled": True,
            "version": module_def.get("version", "latest"),
            "config": module_def.get("default_config", {})
        }
    
    return tenant_config

@app.get("/api/v1/platform/status")
async def get_platform_status():
    """Get overall platform status and statistics"""
    try:
        # Get all namespaces
        namespaces = k8s_core.list_namespace()
        platform_namespaces = [ns for ns in namespaces.items 
                             if ns.metadata.labels and "spanda.ai/tenant" in ns.metadata.labels]
        
        # Count tenants and modules
        tenants = set()
        total_modules = 0
        module_types = {}
        
        for ns in platform_namespaces:
            tenant_name = ns.metadata.labels.get("spanda.ai/tenant")
            if tenant_name:
                tenants.add(tenant_name)
            
            deployed_modules = get_deployed_modules(ns.metadata.name)
            total_modules += len(deployed_modules)
            
            for module in deployed_modules:
                module_name = module["name"]
                if module_name in module_types:
                    module_types[module_name] += 1
                else:
                    module_types[module_name] = 1
        
        # Get available modules from definitions
        definitions = get_module_definitions()
        available_modules = definitions.get("modules", {})
        
        return {
            "platform": {
                "status": "running",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            },
            "statistics": {
                "total_tenants": len(tenants),
                "total_namespaces": len(platform_namespaces),
                "total_deployed_modules": total_modules,
                "available_modules": len(available_modules),
                "module_distribution": module_types
            },
            "tenants": list(tenants)
        }
        
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get platform status: {e}")

# Module Deployment Helper Functions
def get_module_deployment_path(module_name: str) -> Path:
    """Get the path to module deployment files"""
    # Assume spandaai-platform-deployment is a sibling directory to Spandak8s
    base_path = Path(__file__).parent.parent.parent / "spandaai-platform-deployment" / "bare-metal" / "modules"
    
    # Get module definitions to check if this module is part of a larger chart
    definitions = get_module_definitions()
    module_config = definitions.get("modules", {}).get(module_name, {})
    
    # Check if module has a parent chart specified
    parent_chart = module_config.get("chart_path", module_name)
    module_path = base_path / parent_chart
    
    if not module_path.exists():
        raise HTTPException(status_code=404, detail=f"Module deployment files not found for '{module_name}' at path '{module_path}'")
    
    return module_path

def is_module_deployed_via_kubectl(namespace: str, module_name: str) -> Dict[str, Any]:
    """Check if a module is deployed using direct kubectl commands via WSL"""
    import subprocess
    
    try:
        # Check for StatefulSets with various label selectors
        label_selectors = [
            "spanda.ai/module=data-lake-baremetal",
            f"spanda.ai/module={module_name}",
            f"service={module_name}",
            "component=data-lake"
        ]
        
        # Add specific service labels for Spark components
        if module_name == "spark":
            label_selectors.extend([
                "service=spark-master",
                "service=spark-notebook",
                "service=spark-worker"
            ])
        
        statefulsets_found = []
        deployments_found = []
        
        for label_selector in label_selectors:
            # Check StatefulSets
            cmd = ["wsl", "bash", "-c", 
                   f"kubectl get statefulsets -n {namespace} -l '{label_selector}' -o name 2>/dev/null"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                statefulsets_found.extend([s.split('/')[-1] for s in result.stdout.strip().split('\n') if s.strip()])
            
            # Check Deployments
            cmd = ["wsl", "bash", "-c", 
                   f"kubectl get deployments -n {namespace} -l '{label_selector}' -o name 2>/dev/null"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                deployments_found.extend([d.split('/')[-1] for d in result.stdout.strip().split('\n') if d.strip()])
        
        # Special case: Check for any deployments with component=data-lake (broader search)
        cmd = ["wsl", "bash", "-c", 
               f"kubectl get deployments -n {namespace} -l 'component=data-lake' -o name 2>/dev/null"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            all_deployments = [d.split('/')[-1] for d in result.stdout.strip().split('\n') if d.strip()]
            
            # Filter by module name if it matches any component
            for dep in all_deployments:
                if module_name in dep.lower() or any(keyword in dep.lower() for keyword in [module_name, f"{module_name}-"]):
                    deployments_found.append(dep)
        
        # Remove duplicates
        statefulsets_found = list(set(statefulsets_found))
        deployments_found = list(set(deployments_found))
        
        is_deployed = len(statefulsets_found) > 0 or len(deployments_found) > 0
        
        if is_deployed:
            # Get replica status for found resources
            total_replicas = 0
            ready_replicas = 0
            
            for sts in statefulsets_found:
                cmd = ["wsl", "bash", "-c", 
                       f"kubectl get statefulset {sts} -n {namespace} -o jsonpath='{{.status.replicas}}|{{.status.readyReplicas}}' 2>/dev/null"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0 and result.stdout.strip():
                    try:
                        replicas, ready = result.stdout.strip().split('|')
                        total_replicas += int(replicas) if replicas else 0
                        ready_replicas += int(ready) if ready else 0
                    except:
                        pass
            
            status = "running" if ready_replicas > 0 else "failed"
            if 0 < ready_replicas < total_replicas:
                status = "degraded"
                
            return {
                "deployed": True,
                "status": status,
                "replicas": {
                    "desired": total_replicas,
                    "ready": ready_replicas
                },
                "statefulsets": statefulsets_found,
                "deployments": deployments_found
            }
        else:
            return {
                "deployed": False,
                "status": "not_deployed"
            }
            
    except Exception as e:
        logger.error(f"Error checking deployment via kubectl: {e}")
        return {
            "deployed": False,
            "status": "unknown",
            "error": str(e)
        }

def is_module_deployed(namespace: str, module_name: str) -> Dict[str, Any]:
    """Check if a module is already deployed in the tenant namespace"""
    try:
        # First try kubectl approach (more reliable for WSL setup)
        kubectl_result = is_module_deployed_via_kubectl(namespace, module_name)
        if kubectl_result.get("deployed") or kubectl_result.get("status") != "unknown":
            return kubectl_result
        
        # Fallback to Kubernetes API if available
        if k8s_core is None or k8s_apps is None:
            return {
                "deployed": False,
                "status": "unknown",
                "error": "Kubernetes API not available"
            }
        
        # Map module names to their actual deployed labels
        module_label_mapping = {
            "minio": ["data-lake-baremetal", "minio"],
            "spark": ["data-lake-baremetal", "spark"], 
            "dremio": ["data-lake-baremetal", "dremio"]
        }
        
        # Get possible module labels to check
        possible_labels = module_label_mapping.get(module_name, [module_name])
        
        deployments = []
        statefulsets = []
        
        # Try each possible label for deployments
        for label in possible_labels:
            # Try spanda.ai/module label
            deps = k8s_apps.list_namespaced_deployment(
                namespace=namespace,
                label_selector=f"spanda.ai/module={label}"
            )
            deployments.extend(deps.items)
            
            # Try service label
            if len(deps.items) == 0:
                deps = k8s_apps.list_namespaced_deployment(
                    namespace=namespace,
                    label_selector=f"service={module_name}"
                )
                deployments.extend(deps.items)
        
        # Try each possible label for statefulsets
        for label in possible_labels:
            # Try spanda.ai/module label
            sts = k8s_apps.list_namespaced_stateful_set(
                namespace=namespace,
                label_selector=f"spanda.ai/module={label}"
            )
            statefulsets.extend(sts.items)
            
            # Try service label
            if len(sts.items) == 0:
                sts = k8s_apps.list_namespaced_stateful_set(
                    namespace=namespace,
                    label_selector=f"service={module_name}"
                )
                statefulsets.extend(sts.items)
        
        # Remove duplicates
        unique_deployments = {dep.metadata.name: dep for dep in deployments}.values()
        unique_statefulsets = {sts.metadata.name: sts for sts in statefulsets}.values()
        
        is_deployed = len(list(unique_deployments)) > 0 or len(list(unique_statefulsets)) > 0
        
        if is_deployed:
            # Get status from deployments
            total_replicas = 0
            ready_replicas = 0
            
            for deployment in unique_deployments:
                total_replicas += deployment.status.replicas or 0
                ready_replicas += deployment.status.ready_replicas or 0
                
            for statefulset in unique_statefulsets:
                total_replicas += statefulset.status.replicas or 0
                ready_replicas += statefulset.status.ready_replicas or 0
            
            status = "running"
            if ready_replicas == 0:
                status = "failed"
            elif ready_replicas < total_replicas:
                status = "degraded"
                
            return {
                "deployed": True,
                "status": status,
                "replicas": {
                    "desired": total_replicas,
                    "ready": ready_replicas
                }
            }
        else:
            return {
                "deployed": False,
                "status": "not_deployed"
            }
            
    except Exception as e:
        logger.error(f"Error checking module deployment status: {e}")
        return {
            "deployed": False,
            "status": "unknown",
            "error": str(e)
        }

def deploy_module_with_helm(module_name: str, namespace: str, tenant_tier: str = "bronze") -> Dict[str, Any]:
    """Deploy a module using Helm"""
    import subprocess
    
    try:
        module_path = get_module_deployment_path(module_name)
        helm_path = module_path / "helm"
        
        if not helm_path.exists():
            raise HTTPException(status_code=400, detail=f"Helm charts not found for module '{module_name}'")
        
        # Use default values file
        values_file = helm_path / "values.yaml"
        
        # Create release name
        release_name = f"{namespace}-{module_name}"
        
        # Get module definitions to check for specific component settings
        definitions = get_module_definitions()
        module_config = definitions.get("modules", {}).get(module_name, {})
        helm_values = module_config.get("helm_values", {})
        
        # Build helm command for WSL
        # Convert Windows paths to WSL paths and properly escape spaces
        wsl_helm_path = str(helm_path).replace('\\', '/').replace('C:', '/mnt/c')
        wsl_values_file = str(values_file).replace('\\', '/').replace('C:', '/mnt/c')
        
        # Escape spaces in paths by wrapping in single quotes
        wsl_helm_path_escaped = f"'{wsl_helm_path}'"
        wsl_values_file_escaped = f"'{wsl_values_file}'"
        
        # Start building the helm command
        helm_cmd_parts = [
            f"helm upgrade --install {release_name} {wsl_helm_path_escaped}",
            f"--namespace {namespace} --create-namespace",
            f"--values {wsl_values_file_escaped}",
            f"--set global.namespace={namespace}",
            f"--set namespace={namespace}",
            f"--set tenant.name={namespace}",
            f"--set tenant.tier={tenant_tier}",
            f"--set module.name={module_name}",
            f"--set spandaModule={module_name}",
            f"--set spandaTenant={namespace.split('-')[0]}",
            f"--set spandaEnvironment={namespace.split('-')[1] if '-' in namespace else 'dev'}"
        ]
        
        # Add module-specific helm values
        for key, value in helm_values.items():
            if isinstance(value, bool):
                helm_cmd_parts.append(f"--set {key}={str(value).lower()}")
            else:
                helm_cmd_parts.append(f"--set {key}={value}")
        
        # Remove wait to avoid hanging on post-install hooks
        helm_cmd_parts.append("--timeout=300s")
        
        helm_cmd = [
            "wsl", "bash", "-c",
            " ".join(helm_cmd_parts)
        ]
        
        logger.info(f"Deploying module {module_name} to {namespace} with WSL command: {' '.join(helm_cmd)}")
        
        # First, clean up any existing jobs that might conflict with post-install hooks
        cleanup_cmd = [
            "wsl", "bash", "-c", 
            f"kubectl delete job data-lake-init -n {namespace} --ignore-not-found=true"
        ]
        
        try:
            subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=30)
        except Exception:
            # Ignore cleanup errors
            pass
        
        # Execute helm command via WSL
        result = subprocess.run(
            helm_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "release_name": release_name,
                "namespace": namespace,
                "output": result.stdout,
                "deployment_method": "helm"
            }
        else:
            logger.error(f"Helm deployment failed: {result.stderr}")
            raise HTTPException(
                status_code=500, 
                detail=f"Module deployment failed: {result.stderr}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Module deployment timed out")
    except Exception as e:
        import traceback
        logger.error(f"Error deploying module {module_name}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

def undeploy_module_with_helm(module_name: str, namespace: str) -> Dict[str, Any]:
    """Undeploy a module using Helm"""
    import subprocess
    
    try:
        release_name = f"{namespace}-{module_name}"
        
        # Build helm uninstall command for WSL
        helm_cmd = [
            "wsl", "bash", "-c",
            f"helm uninstall {release_name} --namespace {namespace} --timeout=300s"
        ]
        
        logger.info(f"Undeploying module {module_name} from {namespace} with WSL command: {' '.join(helm_cmd)}")
        
        # Execute helm command via WSL
        result = subprocess.run(
            helm_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "release_name": release_name,
                "namespace": namespace,
                "output": result.stdout,
                "deployment_method": "helm"
            }
        else:
            logger.error(f"Helm uninstall failed: {result.stderr}")
            raise HTTPException(
                status_code=500, 
                detail=f"Module undeployment failed: {result.stderr}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Module undeployment timed out")
    except Exception as e:
        logger.error(f"Error undeploying module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Undeployment failed: {str(e)}")

# Module Management Endpoints
@app.post("/api/v1/tenants/{tenant_name}/modules/{module_name}/enable")
async def enable_module(
    tenant_name: str, 
    module_name: str,
    environment: str = "dev",
    tier: str = "bronze"
):
    """Enable/deploy a specific module for a tenant"""
    try:
        # Validate module exists in definitions
        definitions = get_module_definitions()
        available_modules = definitions.get("modules", {})
        
        if module_name not in available_modules:
            raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found in definitions")
        
        # Check if module is already deployed
        # Construct namespace from tenant and environment
        namespace = f"{tenant_name}-{environment}"
        deployment_status = is_module_deployed(namespace, module_name)
        
        if deployment_status["deployed"]:
            if deployment_status["status"] == "running":
                return {
                    "success": True,
                    "message": f"Module '{module_name}' is already running",
                    "status": deployment_status,
                    "namespace": namespace
                }
            else:
                # Module exists but not healthy, try to redeploy
                logger.warning(f"Module {module_name} exists but status is {deployment_status['status']}, redeploying...")
        
        # Deploy the module
        logger.info(f"Deploying module {module_name} for tenant {tenant_name} in {environment} environment")
        
        deployment_result = deploy_module_with_helm(module_name, namespace, tier)
        
        # Wait a moment and check final status
        import time
        time.sleep(5)  # Give Kubernetes time to update
        
        final_status = is_module_deployed(namespace, module_name)
        
        return {
            "success": True,
            "message": f"Module '{module_name}' successfully enabled",
            "deployment": deployment_result,
            "status": final_status,
            "namespace": namespace,
            "tenant": tenant_name,
            "environment": environment,
            "tier": tier
        }
        
    except Exception as e:
        logger.error(f"Error enabling module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable module: {str(e)}")

@app.post("/api/v1/tenants/{tenant_name}/modules/{module_name}/disable") 
async def disable_module(
    tenant_name: str, 
    module_name: str,
    environment: str = "dev"
):
    """Disable/undeploy a specific module for a tenant"""
    try:
        # Construct namespace from tenant and environment
        namespace = f"{tenant_name}-{environment}"
        
        # Check if module is deployed
        deployment_status = is_module_deployed(namespace, module_name)
        
        if not deployment_status["deployed"]:
            return {
                "success": True,
                "message": f"Module '{module_name}' is already not deployed",
                "namespace": namespace
            }
        
        # Undeploy the module
        logger.info(f"Undeploying module {module_name} for tenant {tenant_name} in {environment} environment")
        
        undeploy_result = undeploy_module_with_helm(module_name, namespace)
        
        # Wait a moment and check final status
        import time
        time.sleep(3)  # Give Kubernetes time to clean up
        
        final_status = is_module_deployed(namespace, module_name)
        
        return {
            "success": True,
            "message": f"Module '{module_name}' successfully disabled",
            "undeploy": undeploy_result,
            "status": final_status,
            "namespace": namespace,
            "tenant": tenant_name,
            "environment": environment
        }
        
    except Exception as e:
        logger.error(f"Error disabling module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable module: {str(e)}")

@app.get("/api/v1/debug/k8s")
async def debug_k8s_connection():
    """Debug endpoint to test Kubernetes connection"""
    try:
        # Test basic cluster connection
        namespaces = k8s_core.list_namespace()
        
        # Test specific namespace
        pods = k8s_core.list_namespaced_pod(namespace="langflow-dev")
        
        # Test specific StatefulSets
        sts = k8s_apps.list_namespaced_stateful_set(namespace="langflow-dev")
        
        return {
            "cluster_connection": "OK",
            "namespaces_count": len(namespaces.items),
            "langflow_dev_pods": len(pods.items),
            "langflow_dev_statefulsets": len(sts.items),
            "statefulset_names": [s.metadata.name for s in sts.items],
            "statefulset_labels": [s.metadata.labels for s in sts.items]
        }
    except Exception as e:
        return {
            "cluster_connection": "ERROR",
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/api/v1/tenants/{tenant_name}/modules/{module_name}/status")
async def get_module_deployment_status(
    tenant_name: str,
    module_name: str,
    environment: str = "dev"
):
    """Get deployment status of a specific module for a tenant"""
    try:
        # Construct namespace from tenant and environment
        namespace = f"{tenant_name}-{environment}"
        
        # Check deployment status
        deployment_status = is_module_deployed(namespace, module_name)
        
        return {
            "module": module_name,
            "tenant": tenant_name,
            "environment": environment,
            "namespace": namespace,
            "deployed": deployment_status.get("deployed", False),
            "status": deployment_status.get("status", "unknown"),
            "details": deployment_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting module status {module_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get module status: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
