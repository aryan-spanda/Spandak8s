#!/usr/bin/env python3
"""
Test script to demonstrate the new disable module options
"""
import requests
import json

def test_disable_options():
    base_url = "http://localhost:8000"
    tenant_name = "langflow"
    module_name = "security-vault"
    environment = "dev"
    
    print("🧪 Testing Enhanced Module Disable Options\n")
    
    # Test 1: Check current status
    print("1️⃣ Checking module status...")
    try:
        response = requests.get(f"{base_url}/api/v1/tenants/{tenant_name}/modules/{module_name}/status?environment={environment}")
        if response.status_code == 200:
            status = response.json()
            print(f"   Status: {status.get('status', 'unknown')}")
            print(f"   Deployed: {status.get('deployed', False)}")
        else:
            print(f"   Error: {response.status_code}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    print("\n2️⃣ Available Disable Options:\n")
    
    print("   🔸 Default disable (removes PVCs - DATA LOSS!):")
    print("     python spandak8s disable security-vault --env langflow-dev")
    print("     # This is equivalent to cleanup_pvcs=True, cleanup_all=False")
    
    print("\n   🔸 Keep data (preserves PVCs):")
    print("     python spandak8s disable security-vault --env langflow-dev --keep-data")
    print("     # This sets cleanup_pvcs=False")
    
    print("\n   🔸 Complete cleanup (removes everything):")
    print("     python spandak8s disable security-vault --env langflow-dev --complete-cleanup")
    print("     # This sets cleanup_pvcs=True, cleanup_all=True")
    
    print("\n   🔸 Keep data but complete cleanup of non-persistent resources:")
    print("     python spandak8s disable security-vault --env langflow-dev --keep-data --complete-cleanup")
    print("     # This sets cleanup_pvcs=False, cleanup_all=True")
    
    print("\n3️⃣ API Examples:\n")
    
    examples = [
        ("Default (remove PVCs)", {"environment": "dev", "cleanup_pvcs": True, "cleanup_all": False}),
        ("Keep Data", {"environment": "dev", "cleanup_pvcs": False, "cleanup_all": False}),
        ("Complete Cleanup", {"environment": "dev", "cleanup_pvcs": True, "cleanup_all": True}),
        ("Keep Data + Cleanup Secrets", {"environment": "dev", "cleanup_pvcs": False, "cleanup_all": True})
    ]
    
    for description, params in examples:
        print(f"   🔸 {description}:")
        print(f"     POST {base_url}/api/v1/tenants/{tenant_name}/modules/{module_name}/disable")
        print(f"     Params: {json.dumps(params, indent=6)}")
        print()
    
    print("4️⃣ What gets cleaned up:\n")
    print("   📦 Always removed: Deployments, Services, ConfigMaps (managed by Helm)")
    print("   💾 cleanup_pvcs=True: PersistentVolumeClaims (⚠️ DATA LOSS!)")
    print("   🔐 cleanup_all=True: Secrets, ServiceAccounts, Jobs")
    print("   🏷️  Namespace: Always preserved (may contain other modules)")

if __name__ == "__main__":
    test_disable_options()
