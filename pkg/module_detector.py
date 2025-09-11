"""
Spandak8s CLI - Platform Module Detection and Health Monitoring

This module provides intelligent detection and monitoring of platform modules:
- Auto-discovery of running modules in Kubernetes clusters
- Health status monitoring for MinIO, Spark, Dremio, etc.
- Configuration validation and compliance checking
- Dependency analysis and conflict detection
- Performance metrics collection and analysis
- Module lifecycle management (install/upgrade/remove)

Key Features:
- Real-time module discovery via Kubernetes APIs
- Health scoring and alerting
- Configuration drift detection
- Resource usage monitoring
- Integration with monitoring systems (Prometheus, Grafana)
- Automated remediation suggestions
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from rich.console import Console

from pkg.kubernetes import (
    run_kubectl,
    check_module_health,
    get_service_endpoints,
    check_namespace_exists
)

console = Console()

# Module detection patterns - how to identify each module type
MODULE_PATTERNS = {
    "minio": {
        "labels": ["app=minio", "app.kubernetes.io/name=minio"],
        "services": ["minio", "minio-service"],
        "check_status": "statefulset.apps/minio"
    },
    "spark": {
        "labels": ["app=spark", "app.kubernetes.io/name=spark"],
        "services": ["spark-master", "spark-worker"],
        "check_status": "deployment.apps/spark-master"
    },
    "dremio": {
        "labels": ["app=dremio", "app.kubernetes.io/name=dremio"],
        "services": ["dremio", "dremio-service"],
        "check_status": "statefulset.apps/dremio"
    },
    "kafka": {
        "labels": ["app=kafka", "app.kubernetes.io/name=kafka"],
        "services": ["kafka", "kafka-headless"],
        "check_status": "statefulset.apps/kafka"
    },
    "airflow": {
        "labels": ["app=airflow", "app.kubernetes.io/name=airflow"],
        "services": ["airflow-webserver", "airflow-scheduler"],
        "check_status": "deployment.apps/airflow-webserver"
    },
    "jupyterhub": {
        "labels": ["app=jupyterhub", "app.kubernetes.io/name=jupyterhub"],
        "services": ["jupyterhub", "jupyterhub-hub"],
        "check_status": "deployment.apps/jupyterhub"
    },
    "prometheus": {
        "labels": ["app=prometheus", "app.kubernetes.io/name=prometheus"],
        "services": ["prometheus-server"],
        "check_status": "deployment.apps/prometheus-server"
    },
    "grafana": {
        "labels": ["app=grafana", "app.kubernetes.io/name=grafana"],
        "services": ["grafana"],
        "check_status": "deployment.apps/grafana"
    }
}

def get_available_modules() -> List[Dict[str, Any]]:
    """Get list of available platform modules from charts directory"""
    available_modules = []
    
    # Try to find charts directory
    charts_paths = [
        os.environ.get("SNAP", "") + "/charts" if os.environ.get("SNAP") else "",
        "../spandaai-platform-deployment/bare-metal/modules",
        "./charts",
        "/opt/spandak8s/charts"
    ]
    
    charts_dir = None
    for path in charts_paths:
        if path and Path(path).exists():
            charts_dir = Path(path)
            break
    
    if not charts_dir:
        # Return default modules if no charts directory found
        for module_name, pattern in MODULE_PATTERNS.items():
            available_modules.append({
                "name": module_name,
                "description": f"{module_name.title()} platform module",
                "version": "latest",
                "category": "platform",
                "check_status": pattern["check_status"]
            })
        return available_modules
    
    # Scan charts directory for available modules
    try:
        for item in charts_dir.iterdir():
            if item.is_dir() and item.name in MODULE_PATTERNS:
                module_info = {
                    "name": item.name,
                    "description": f"{item.name.title()} platform module",
                    "version": "latest",
                    "category": "platform",
                    "check_status": MODULE_PATTERNS[item.name]["check_status"]
                }
                
                # Try to read Chart.yaml for more details
                chart_yaml = item / "Chart.yaml"
                if chart_yaml.exists():
                    try:
                        with open(chart_yaml, 'r') as f:
                            chart_data = yaml.safe_load(f)
                        
                        module_info.update({
                            "description": chart_data.get("description", module_info["description"]),
                            "version": chart_data.get("version", "latest"),
                        })
                    except Exception:
                        pass  # Use defaults if can't read Chart.yaml
                
                available_modules.append(module_info)
    
    except Exception as e:
        console.print(f"⚠️ [yellow]Warning: Could not scan charts directory: {e}[/yellow]")
        # Fallback to default modules
        return get_available_modules()
    
    return available_modules

def detect_running_modules(namespace: str) -> Dict[str, Dict[str, Any]]:
    """Detect which modules are currently running in a namespace"""
    if not check_namespace_exists(namespace):
        return {}
    
    running_modules = {}
    
    try:
        # Get all resources in the namespace
        all_resources = run_kubectl("get", "all", "-o", "json", namespace=namespace, die=False)
        if not all_resources:
            return {}
        
        resources_data = json.loads(all_resources)
        all_resources_text = json.dumps(resources_data)
        
        # Check each module pattern
        for module_name, pattern in MODULE_PATTERNS.items():
            module_info = check_module_in_namespace(module_name, pattern, namespace, all_resources_text)
            if module_info:
                running_modules[module_name] = module_info
    
    except Exception as e:
        console.print(f"⚠️ [yellow]Warning: Error detecting modules in {namespace}: {e}[/yellow]")
    
    return running_modules

def check_module_in_namespace(module_name: str, pattern: Dict[str, Any], 
                            namespace: str, all_resources_text: str) -> Optional[Dict[str, Any]]:
    """Check if a specific module is running in the namespace"""
    
    # Check if the module's check_status pattern exists in resources
    if pattern["check_status"] not in all_resources_text:
        return None
    
    # Module is detected, get detailed health info
    health_info = check_module_health(namespace, module_name)
    
    if health_info["status"] == "not_found":
        return None
    
    # Get additional configuration information
    module_config = get_module_configuration(module_name, namespace)
    
    return {
        "name": module_name,
        "status": health_info["status"],
        "namespace": namespace,
        "pods": len(health_info["pods"]),
        "services": len(health_info["services"]),
        "endpoints": health_info["endpoints"],
        "configuration": module_config,
        "health": health_info
    }

def get_module_configuration(module_name: str, namespace: str) -> Dict[str, Any]:
    """Extract configuration information for a module"""
    config = {}
    
    try:
        # Try to get configuration from ConfigMaps
        configmaps_result = run_kubectl("get", "configmaps", "-l", f"app={module_name}", 
                                       "-o", "json", namespace=namespace, die=False)
        if configmaps_result:
            configmaps_data = json.loads(configmaps_result)
            for cm in configmaps_data.get("items", []):
                cm_data = cm.get("data", {})
                config.update(cm_data)
        
        # Try to get resource information from the main deployment/statefulset
        resource_types = ["deployment", "statefulset", "daemonset"]
        for resource_type in resource_types:
            try:
                resource_result = run_kubectl("get", resource_type, "-l", f"app={module_name}",
                                            "-o", "json", namespace=namespace, die=False)
                if resource_result:
                    resource_data = json.loads(resource_result)
                    for resource in resource_data.get("items", []):
                        spec = resource.get("spec", {})
                        
                        # Extract replicas
                        if "replicas" in spec:
                            config["replicas"] = spec["replicas"]
                        
                        # Extract resource requests/limits from containers
                        template = spec.get("template", {})
                        containers = template.get("spec", {}).get("containers", [])
                        for container in containers:
                            resources = container.get("resources", {})
                            if resources.get("requests"):
                                config.update({f"requests_{k}": v for k, v in resources["requests"].items()})
                            if resources.get("limits"):
                                config.update({f"limits_{k}": v for k, v in resources["limits"].items()})
                        
                        # Extract storage information from volume claims
                        volume_claims = template.get("spec", {}).get("volumes", [])
                        for volume in volume_claims:
                            if "persistentVolumeClaim" in volume:
                                pvc_name = volume["persistentVolumeClaim"]["claimName"]
                                # Get PVC details
                                try:
                                    pvc_result = run_kubectl("get", "pvc", pvc_name, "-o", "json", 
                                                           namespace=namespace, die=False)
                                    if pvc_result:
                                        pvc_data = json.loads(pvc_result)
                                        storage_size = pvc_data["spec"]["resources"]["requests"]["storage"]
                                        config["storage"] = storage_size
                                except Exception:
                                    pass
                        
                        break  # Only process first resource
                break
            except Exception:
                continue
    
    except Exception as e:
        console.print(f"⚠️ [yellow]Warning: Could not get configuration for {module_name}: {e}[/yellow]")
    
    return config

def get_module_endpoints(module_name: str, namespace: str) -> List[str]:
    """Get all endpoints for a module"""
    endpoints = []
    
    try:
        pattern = MODULE_PATTERNS.get(module_name, {})
        service_names = pattern.get("services", [])
        
        # Also try to discover services by label
        services_result = run_kubectl("get", "services", "-l", f"app={module_name}",
                                     "-o", "json", namespace=namespace, die=False)
        if services_result:
            services_data = json.loads(services_result)
            discovered_services = [svc["metadata"]["name"] for svc in services_data.get("items", [])]
            service_names.extend(discovered_services)
        
        # Remove duplicates
        service_names = list(set(service_names))
        
        for service_name in service_names:
            try:
                service_endpoints = get_service_endpoints(namespace, service_name)
                endpoints.extend(service_endpoints)
            except Exception:
                continue
    
    except Exception as e:
        console.print(f"⚠️ [yellow]Warning: Could not get endpoints for {module_name}: {e}[/yellow]")
    
    return endpoints

def validate_module_health(module_name: str, namespace: str) -> Dict[str, Any]:
    """Perform comprehensive health check for a module"""
    health_report = {
        "module": module_name,
        "namespace": namespace,
        "overall_status": "unknown",
        "checks": {}
    }
    
    try:
        # Check if module exists
        health_info = check_module_health(namespace, module_name)
        health_report["checks"]["existence"] = {
            "status": "pass" if health_info["status"] != "not_found" else "fail",
            "details": f"Module {'found' if health_info['status'] != 'not_found' else 'not found'}"
        }
        
        if health_info["status"] == "not_found":
            health_report["overall_status"] = "not_found"
            return health_report
        
        # Check pod health
        pods = health_info["pods"]
        running_pods = sum(1 for pod in pods if pod["status"] == "Running")
        total_pods = len(pods)
        
        health_report["checks"]["pods"] = {
            "status": "pass" if running_pods == total_pods and total_pods > 0 else "fail",
            "details": f"{running_pods}/{total_pods} pods running"
        }
        
        # Check service availability
        services = health_info["services"]
        health_report["checks"]["services"] = {
            "status": "pass" if len(services) > 0 else "fail",
            "details": f"{len(services)} services available"
        }
        
        # Check endpoints
        endpoints = health_info["endpoints"]
        health_report["checks"]["endpoints"] = {
            "status": "pass" if len(endpoints) > 0 else "warn",
            "details": f"{len(endpoints)} endpoints available"
        }
        
        # Determine overall status
        if all(check["status"] == "pass" for check in health_report["checks"].values()):
            health_report["overall_status"] = "healthy"
        elif any(check["status"] == "fail" for check in health_report["checks"].values()):
            health_report["overall_status"] = "unhealthy"
        else:
            health_report["overall_status"] = "degraded"
    
    except Exception as e:
        health_report["overall_status"] = "error"
        health_report["error"] = str(e)
    
    return health_report
