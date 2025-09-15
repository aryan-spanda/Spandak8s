#!/usr/bin/env python3

import subprocess
from pathlib import Path

def test_helm_deployment():
    """Test the exact Helm deployment command"""
    
    # Construct the paths
    base_path = Path(__file__).parent.parent / "spandaai-platform-deployment" / "bare-metal" / "modules"
    module_path = base_path / "data-lake-baremetal"
    helm_path = module_path / "helm"
    values_file = helm_path / "values.yaml"
    
    print(f"Module path: {module_path}")
    print(f"Helm path: {helm_path}")
    print(f"Values file: {values_file}")
    print(f"Path exists: {helm_path.exists()}")
    
    if not helm_path.exists():
        print("ERROR: Helm path does not exist!")
        return
    
    # Convert Windows paths to WSL paths
    wsl_helm_path = str(helm_path).replace('\\', '/').replace('C:', '/mnt/c')
    wsl_values_file = str(values_file).replace('\\', '/').replace('C:', '/mnt/c')
    
    print(f"WSL Helm path: {wsl_helm_path}")
    print(f"WSL Values file: {wsl_values_file}")
    
    # Build the exact Helm command that would be used
    release_name = "langflow-dev-minio"
    namespace = "langflow-dev"
    
    helm_cmd_parts = [
        f"helm upgrade --install {release_name} '{wsl_helm_path}'",
        f"--namespace {namespace} --create-namespace",
        f"--values '{wsl_values_file}'",
        f"--set global.namespace={namespace}",
        f"--set namespace={namespace}",
        f"--set tenant.name={namespace}",
        f"--set tenant.tier=bronze",
        f"--set module.name=minio",
        f"--set spandaModule=minio",
        f"--set spandaTenant=langflow",
        f"--set spandaEnvironment=dev",
        f"--set minio.enabled=true",
        f"--set spark.enabled=false",
        f"--set dremio.enabled=false",
        f"--set kafka.enabled=false",
        f"--set nifi.enabled=false",
        f"--set nessie.enabled=false",
        f"--wait --timeout=300s"
    ]
    
    full_command = " ".join(helm_cmd_parts)
    print(f"\nFull Helm command:")
    print(full_command)
    
    helm_cmd = [
        "wsl", "bash", "-c",
        full_command
    ]
    
    print(f"\nExecuting command...")
    try:
        result = subprocess.run(
            helm_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        if result.returncode == 0:
            print("SUCCESS: Helm deployment would work!")
        else:
            print("ERROR: Helm deployment failed!")
            
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out!")
    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")

if __name__ == "__main__":
    test_helm_deployment()
