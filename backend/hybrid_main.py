"""
Hybrid Spandak8s Backend API

This approach combines the best of both worlds:
1. Real-time status checking from Kubernetes (no database needed)
2. Module definitions loaded from local YAML file (your existing config)
3. Simple user authentication with minimal database (just users table)

Architecture:
- Module definitions: Load from local YAML file (config/module-definitions.yaml)
- Real-time status: Query Kubernetes directly
- User management: Lightweight PostgreSQL (just users + sessions)
- No heavy database schema for module/tenant data
"""

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import yaml
import logging
import os
from datetime import datetime, timedelta
from kubernetes import client, config
import hashlib
import jwt
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Spandak8s Hybrid API",
    description="Hybrid API: YAML configs + Kubernetes real-time + minimal auth DB",
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

# Security
security = HTTPBearer()

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Initialize Kubernetes client  
try:
    config.load_incluster_config()  # If running in cluster
except Exception:
    try:
        # Try to load from WSL kubeconfig first
        import os
        wsl_kubeconfig = os.path.expanduser("~/.kube/config")
        if not os.path.exists(wsl_kubeconfig):
            # If Windows kubeconfig doesn't exist, try to access WSL kubeconfig
            wsl_kubeconfig = "/mnt/c/Users/" + os.getenv("USERNAME", "user") + "/.kube/config"
        
        config.load_kube_config(config_file=wsl_kubeconfig)
        logger.info("Loaded kubeconfig for WSL Kubernetes cluster")
    except Exception as e:
        try:
            # Fallback to default kubeconfig loading
            config.load_kube_config()
            logger.info("Loaded local kubeconfig")
        except Exception as e2:
            logger.warning(f"Could not load Kubernetes config: {e2}")
        
k8s_core = client.CoreV1Api()
k8s_apps = client.AppsV1Api()

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

# Minimal in-memory user store (replace with database for production)
USERS_DB = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256("spanda123!".encode()).hexdigest(),
        "roles": ["admin", "user"],
        "created_at": datetime.now().isoformat()
    },
    "user": {
        "username": "user", 
        "password_hash": hashlib.sha256("user123!".encode()).hexdigest(),
        "roles": ["user"],
        "created_at": datetime.now().isoformat()
    }
}

# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str

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

# Authentication functions
def create_jwt_token(username: str, roles: List[str]) -> str:
    """Create JWT token for user"""
    payload = {
        "username": username,
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    username = payload.get("username")
    if username not in USERS_DB:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "username": username,
        "roles": payload.get("roles", []),
        "user_data": USERS_DB[username]
    }

# Kubernetes helper functions
def get_deployed_modules(namespace: str) -> List[Dict[str, Any]]:
    """Get list of deployed modules in a namespace with their status"""
    try:
        deployments = k8s_apps.list_namespaced_deployment(namespace=namespace)
        modules = []
        
        for deployment in deployments.items:
            labels = deployment.metadata.labels or {}
            
            # Check if this is a spanda module
            if "spanda.ai/module" in labels:
                module_name = labels["spanda.ai/module"]
                
                # Get deployment status
                total_replicas = deployment.status.replicas or 0
                ready_replicas = deployment.status.ready_replicas or 0
                
                status = "running"
                if ready_replicas == 0:
                    status = "failed"
                elif ready_replicas < total_replicas:
                    status = "degraded"
                
                modules.append({
                    "name": module_name,
                    "status": status,
                    "replicas": {
                        "desired": total_replicas,
                        "ready": ready_replicas
                    },
                    "deployment_name": deployment.metadata.name
                })
        
        return modules
    except Exception as e:
        logger.error(f"Error getting deployed modules: {e}")
        return []

def check_kubernetes_connectivity():
    """Check if Kubernetes API is accessible"""
    try:
        k8s_core.list_namespace()
        return True
    except Exception:
        return False

# API Endpoints

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """User login endpoint"""
    username = request.username
    password = request.password
    
    if username not in USERS_DB:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user = USERS_DB[username]
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if password_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_jwt_token(username, user["roles"])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRATION_HOURS * 3600,
        "user": {
            "username": username,
            "roles": user["roles"]
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    k8s_status = "healthy" if check_kubernetes_connectivity() else "unhealthy"
    
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
async def get_module_definitions_api():  # user: dict = Depends(get_current_user)
    """Get complete module definitions from YAML file"""
    logger.info(f"Guest user requested module definitions")  # User {user['username']} requested module definitions
    return get_module_definitions()

@app.get("/api/v1/modules")
async def list_modules():  # user: dict = Depends(get_current_user)
    """Get list of all available platform modules"""
    definitions = get_module_definitions()
    modules = []
    
    for name, data in definitions.get("modules", {}).items():
        modules.append({
            "name": name,
            "display_name": data.get("display_name", name),
            "description": data.get("description", ""),
            "version": data.get("version", "1.0.0"),
            "category": data.get("category", "uncategorized")
        })
    
    return {"modules": modules}

@app.get("/api/v1/modules/{module_name}")
async def get_module_details(module_name: str):  # user: dict = Depends(get_current_user)
    """Get detailed information about a specific module"""
    definitions = get_module_definitions()
    modules = definitions.get("modules", {})
    
    if module_name not in modules:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")
    
    return modules[module_name]

@app.post("/api/v1/modules/validate")
async def validate_modules(request: ModuleValidationRequest, user: dict = Depends(get_current_user)):
    """Validate module list and check dependencies"""
    definitions = get_module_definitions()
    available_modules = definitions.get("modules", {})
    errors = []
    warnings = []
    
    # Check if all modules exist
    for module in request.modules:
        if module not in available_modules:
            errors.append(f"Module '{module}' not found")
    
    # Check dependencies
    for module in request.modules:
        if module in available_modules:
            deps = available_modules[module].get("dependencies", [])
            for dep in deps:
                if dep not in request.modules:
                    warnings.append(f"Module '{module}' recommends dependency '{dep}' which is not included")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

@app.get("/api/v1/tenants")
async def list_tenants(user: dict = Depends(get_current_user)):
    """Get tenants by querying Kubernetes namespaces"""
    try:
        # Look for namespaces with spanda label
        namespaces = k8s_core.list_namespace(
            label_selector="spanda.ai/managed=true"
        )
        
        tenants = []
        for ns in namespaces.items:
            tenant_name = ns.metadata.name
            labels = ns.metadata.labels or {}
            
            # Get deployed modules with real-time status
            modules = get_deployed_modules(tenant_name)
            
            tenants.append({
                "name": tenant_name,
                "tier": labels.get("spanda.ai/tier", "unknown"),
                "status": "running" if ns.status.phase == "Active" else "failed",
                "modules": modules,
                "created_at": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None
            })
        
        return {"tenants": tenants}
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tenants: {e}")

@app.get("/api/v1/tenants/{tenant_name}/status")
async def get_tenant_status(tenant_name: str, user: dict = Depends(get_current_user)):
    """Get real-time tenant status from Kubernetes"""
    try:
        # Check if namespace exists
        try:
            namespace = k8s_core.read_namespace(name=tenant_name)
        except client.ApiException as e:
            if e.status == 404:
                raise HTTPException(status_code=404, detail=f"Tenant {tenant_name} not found")
            raise
        
        # Get resource quota usage
        try:
            quota = k8s_core.read_namespaced_resource_quota(
                name=f"{tenant_name}-quota",
                namespace=tenant_name
            )
            resource_usage = {
                "hard": dict(quota.status.hard) if quota.status and quota.status.hard else {},
                "used": dict(quota.status.used) if quota.status and quota.status.used else {}
            }
        except Exception:
            resource_usage = {"hard": {}, "used": {}}
        
        # Get pod status
        pods = k8s_core.list_namespaced_pod(namespace=tenant_name)
        pod_status = {
            "running": 0,
            "pending": 0, 
            "failed": 0,
            "total": len(pods.items)
        }
        
        for pod in pods.items:
            phase = pod.status.phase.lower()
            if phase in pod_status:
                pod_status[phase] += 1
        
        # Get deployed modules with status
        modules = get_deployed_modules(tenant_name)
        
        return {
            "tenant_name": tenant_name,
            "namespace": tenant_name,
            "status": "running" if namespace.status.phase == "Active" else "failed",
            "modules": modules,
            "resource_usage": resource_usage,
            "pods": pod_status,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting tenant status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tenant status: {e}")

@app.get("/api/v1/modules/{module_name}/health")
async def check_module_health(module_name: str, tenant_name: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Check module health in real-time from Kubernetes"""
    try:
        namespace = tenant_name or "default"
        
        # Find deployments for this module
        deployments = k8s_apps.list_namespaced_deployment(
            namespace=namespace,
            label_selector=f"spanda.ai/module={module_name}"
        )
        
        if not deployments.items:
            raise HTTPException(status_code=404, detail=f"Module {module_name} not found in namespace {namespace}")
        
        deployment = deployments.items[0]
        
        # Check deployment status
        total_replicas = deployment.status.replicas or 0
        ready_replicas = deployment.status.ready_replicas or 0
        
        status = "healthy"
        if ready_replicas == 0:
            status = "unhealthy"
        elif ready_replicas < total_replicas:
            status = "degraded"
        
        # Get pods for this deployment
        pods = k8s_core.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"spanda.ai/module={module_name}"
        )
        
        pod_status = {
            "running": 0,
            "pending": 0,
            "failed": 0
        }
        
        for pod in pods.items:
            phase = pod.status.phase.lower()
            if phase in pod_status:
                pod_status[phase] += 1
        
        return {
            "module_name": module_name,
            "tenant": tenant_name,
            "status": status,
            "replicas": {
                "desired": total_replicas,
                "ready": ready_replicas,
                "available": deployment.status.available_replicas or 0
            },
            "pods": pod_status,
            "last_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking module health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check module health: {e}")

@app.post("/api/v1/tenants/generate-config")
async def generate_tenant_config(request: TenantConfigRequest, user: dict = Depends(get_current_user)):
    """Generate tenant configuration using YAML module definitions"""
    definitions = get_module_definitions()
    
    # Get tier resources
    tier_resources = definitions.get("resource_tiers", {}).get(request.tier.lower())
    if not tier_resources:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")
    
    # Validate modules exist
    available_modules = definitions.get("modules", {})
    for module in request.modules:
        if module not in available_modules:
            raise HTTPException(status_code=400, detail=f"Module {module} not found")
    
    # Build configuration
    config = {
        "tenant": {
            "name": request.tenant_name,
            "tier": request.tier,
            "namespace": request.tenant_name
        },
        "modules": request.modules,
        "resourceQuota": {
            "hard": {
                "requests.cpu": tier_resources["cpu"],
                "requests.memory": tier_resources["memory"],
                "limits.cpu": tier_resources["cpu"],
                "limits.memory": tier_resources["memory"],
                "requests.storage": tier_resources["storage"]
            }
        },
        "moduleConfigs": {}
    }
    
    # Add custom resources if provided
    if request.custom_resources:
        config["resourceQuota"]["hard"].update(request.custom_resources)
    
    # Add module-specific configurations from YAML
    for module_name in request.modules:
        module = available_modules.get(module_name)
        if module and "default_config" in module:
            config["moduleConfigs"][module_name] = module["default_config"]
    
    logger.info(f"Generated configuration for tenant {request.tenant_name} with tier {request.tier}")
    return config

@app.get("/api/v1/platform/status")
async def get_platform_status(user: dict = Depends(get_current_user)):
    """Get overall platform health and status"""
    try:
        # Count spanda-managed namespaces
        namespaces = k8s_core.list_namespace(label_selector="spanda.ai/managed=true")
        total_tenants = len(namespaces.items)
        
        # Get cluster info
        try:
            cluster_info = k8s_core.list_node()
            cluster_nodes = len(cluster_info.items)
            cluster_status = "healthy"
        except Exception:
            cluster_nodes = 0
            cluster_status = "unhealthy"
        
        # Count available modules
        definitions = get_module_definitions()
        available_modules = len(definitions.get("modules", {}))
        
        return {
            "platform_status": "healthy",
            "total_tenants": total_tenants,
            "available_modules": available_modules,
            "cluster_nodes": cluster_nodes,
            "cluster_status": cluster_status,
            "api_version": "1.0.0",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting platform status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get platform status: {e}")

# Module Deployment Helper Functions
def get_module_deployment_path(module_name: str) -> Path:
    """Get the path to module deployment files"""
    # Assume spandaai-platform-deployment is a sibling directory to Spandak8s
    base_path = Path(__file__).parent.parent.parent / "spandaai-platform-deployment" / "bare-metal" / "modules"
    module_path = base_path / module_name
    
    if not module_path.exists():
        raise HTTPException(status_code=404, detail=f"Module deployment files not found for '{module_name}'")
    
    return module_path

def is_module_deployed(namespace: str, module_name: str) -> Dict[str, Any]:
    """Check if a module is already deployed in the tenant namespace"""
    try:
        # Look for deployments with the module label
        deployments = k8s_apps.list_namespaced_deployment(
            namespace=namespace,
            label_selector=f"spanda.ai/module={module_name}"
        )
        
        # Look for statefulsets with the module label
        statefulsets = k8s_apps.list_namespaced_stateful_set(
            namespace=namespace,
            label_selector=f"spanda.ai/module={module_name}"
        )
        
        is_deployed = len(deployments.items) > 0 or len(statefulsets.items) > 0
        
        if is_deployed:
            # Get status from deployments
            total_replicas = 0
            ready_replicas = 0
            
            for deployment in deployments.items:
                total_replicas += deployment.status.replicas or 0
                ready_replicas += deployment.status.ready_replicas or 0
                
            for statefulset in statefulsets.items:
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
                "status": "not_deployed",
                "replicas": {
                    "desired": 0,
                    "ready": 0
                }
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
        
        # Build helm command for WSL
        # Convert Windows paths to WSL paths
        wsl_helm_path = str(helm_path).replace('\\', '/').replace('C:', '/mnt/c')
        wsl_values_file = str(values_file).replace('\\', '/').replace('C:', '/mnt/c')
        
        helm_cmd = [
            "wsl", "bash", "-c",
            f"helm upgrade --install {release_name} '{wsl_helm_path}' "
            f"--namespace {namespace} --create-namespace "
            f"--values '{wsl_values_file}' "
            f"--set global.namespace={namespace} "
            f"--set namespace={namespace} "
            f"--set tenant.name={namespace} "
            f"--set tenant.tier={tenant_tier} "
            f"--set module.name={module_name} "
            f"--set spandaTenant={namespace.split('-')[0]} "
            f"--set spandaEnvironment={namespace.split('-')[1] if '-' in namespace else 'dev'} "
            f"--wait --timeout=300s"
        ]
        
        logger.info(f"Deploying module {module_name} to {namespace} with WSL command: {' '.join(helm_cmd)}")
        
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
            f"helm uninstall {release_name} --namespace {namespace} --wait --timeout=300s"
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
            # Check if it's just because release doesn't exist
            if "not found" in result.stderr.lower():
                return {
                    "success": True,
                    "message": "Module was not deployed or already removed",
                    "release_name": release_name,
                    "namespace": namespace
                }
            else:
                logger.error(f"Helm uninstall failed: {result.stderr}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Module removal failed: {result.stderr}"
                )
                
    except Exception as e:
        logger.error(f"Error undeploying module {module_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Removal failed: {e}")

# Module Deployment API Endpoints
@app.post("/api/v1/tenants/{tenant_name}/modules/{module_name}/enable")
async def enable_module(
    tenant_name: str, 
    module_name: str,
    environment: str = "dev",
    tier: str = "bronze"
    # user: dict = Depends(get_current_user)
):
    """Enable/deploy a specific module for a tenant"""
    try:
        # Validate module exists in definitions
        definitions = get_module_definitions()
        available_modules = definitions.get("modules", {})
        
        if module_name not in available_modules:
            raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found in definitions")
        
        # Check if module is already deployed
        # Use environment directly as namespace since it already includes tenant context
        namespace = environment
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
        import traceback
        logger.error(f"Error enabling module {module_name} for tenant {tenant_name}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to enable module: {str(e)}")

@app.post("/api/v1/tenants/{tenant_name}/modules/{module_name}/disable") 
async def disable_module(
    tenant_name: str,
    module_name: str, 
    environment: str = "dev"
    # user: dict = Depends(get_current_user)
):
    """Disable/undeploy a specific module for a tenant"""
    try:
        # Use environment directly as namespace since it already includes tenant context
        namespace = environment
        
        # Check if module is currently deployed
        deployment_status = is_module_deployed(namespace, module_name)
        
        if not deployment_status["deployed"]:
            return {
                "success": True,
                "message": f"Module '{module_name}' is already disabled",
                "namespace": namespace
            }
        
        # Undeploy the module
        logger.info(f"Disabling module {module_name} for tenant {tenant_name} in {environment} environment")
        
        undeployment_result = undeploy_module_with_helm(module_name, namespace)
        
        # Wait and verify removal
        import time
        time.sleep(5)
        
        final_status = is_module_deployed(namespace, module_name)
        
        return {
            "success": True,
            "message": f"Module '{module_name}' successfully disabled",
            "undeployment": undeployment_result,
            "status": final_status,
            "namespace": namespace,
            "tenant": tenant_name,
            "environment": environment
        }
        
    except Exception as e:
        logger.error(f"Error disabling module {module_name} for tenant {tenant_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable module: {e}")

@app.get("/api/v1/tenants/{tenant_name}/modules/{module_name}/status")
async def get_module_deployment_status(
    tenant_name: str,
    module_name: str,
    environment: str = "dev"
    # user: dict = Depends(get_current_user)
):
    """Get the deployment status of a specific module for a tenant"""
    try:
        # Use environment directly as namespace since it already includes tenant context
        namespace = environment
        deployment_status = is_module_deployed(namespace, module_name)
        
        return {
            "module_name": module_name,
            "tenant": tenant_name,
            "environment": environment,
            "namespace": namespace,
            **deployment_status,
            "last_checked": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting module status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get module status: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
