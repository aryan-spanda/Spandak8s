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
        config.load_kube_config()  # If running locally
        logger.info("Loaded local kubeconfig")
    except Exception as e:
        logger.warning(f"Could not load Kubernetes config: {e}")
        
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
        with open(config_path, 'r') as f:
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
async def get_module_definitions_api(user: dict = Depends(get_current_user)):
    """Get complete module definitions from YAML file"""
    logger.info(f"User {user['username']} requested module definitions")
    return get_module_definitions()

@app.get("/api/v1/modules")
async def list_modules(user: dict = Depends(get_current_user)):
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
async def get_module_details(module_name: str, user: dict = Depends(get_current_user)):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
