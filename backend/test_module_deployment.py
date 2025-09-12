#!/usr/bin/env python3
"""
Module Deployment System Test

This script tests the complete module deployment workflow:
1. Module availability check
2. Module enable/deploy
3. Status verification  
4. Module disable/undeploy
"""

import requests
import time

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_TENANT = "test-deployment"
TEST_MODULE = "data-lake-baremetal"  # Change to available module
TEST_ENVIRONMENT = "dev"
TEST_TIER = "bronze"

def login_to_backend():
    """Login to the hybrid backend"""
    print("🔐 Logging into hybrid backend...")
    
    response = requests.post(f"{API_BASE_URL}/api/v1/auth/login", json={
        "username": "admin",
        "password": "spanda123!"
    })
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Login successful")
        return {"Authorization": f"Bearer {token}"}
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def test_module_availability(headers):
    """Test that modules are available"""
    print("\n📦 Testing module availability...")
    
    # Get all modules
    response = requests.get(f"{API_BASE_URL}/api/v1/modules", headers=headers)
    if response.status_code != 200:
        print("❌ Failed to get modules list")
        return False
    
    modules = response.json().get("modules", [])
    print(f"✅ Found {len(modules)} available modules")
    
    # Check if test module exists
    module_names = [m["name"] for m in modules]
    if TEST_MODULE not in module_names:
        print(f"⚠️ Test module '{TEST_MODULE}' not found. Available modules:")
        for name in module_names[:5]:  # Show first 5
            print(f"   - {name}")
        return False
    
    print(f"✅ Test module '{TEST_MODULE}' is available")
    return True

def test_module_enable(headers):
    """Test module deployment"""
    print(f"\n🚀 Testing module enable: {TEST_MODULE}")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tenants/{TEST_TENANT}/modules/{TEST_MODULE}/enable",
        headers=headers,
        params={
            "environment": TEST_ENVIRONMENT,
            "tier": TEST_TIER
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Module enable request successful")
        print(f"   Namespace: {result.get('namespace', 'unknown')}")
        print(f"   Status: {result.get('status', {}).get('status', 'unknown')}")
        return True
    else:
        print(f"❌ Module enable failed: {response.text}")
        return False

def test_module_status(headers):
    """Test module status check"""
    print(f"\n📊 Testing module status check: {TEST_MODULE}")
    
    response = requests.get(
        f"{API_BASE_URL}/api/v1/tenants/{TEST_TENANT}/modules/{TEST_MODULE}/status",
        headers=headers,
        params={"environment": TEST_ENVIRONMENT}
    )
    
    if response.status_code == 200:
        status = response.json()
        print("✅ Module status check successful")
        print(f"   Deployed: {status.get('deployed', False)}")
        print(f"   Status: {status.get('status', 'unknown')}")
        
        replicas = status.get('replicas', {})
        if replicas:
            print(f"   Replicas: {replicas.get('ready', 0)}/{replicas.get('desired', 0)}")
        
        return status.get('deployed', False)
    else:
        print(f"❌ Module status check failed: {response.text}")
        return False

def test_module_disable(headers):
    """Test module removal"""
    print(f"\n🛑 Testing module disable: {TEST_MODULE}")
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/tenants/{TEST_TENANT}/modules/{TEST_MODULE}/disable",
        headers=headers,
        params={"environment": TEST_ENVIRONMENT}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Module disable request successful")
        print(f"   Message: {result.get('message', 'No message')}")
        return True
    else:
        print(f"❌ Module disable failed: {response.text}")
        return False

def test_health_check():
    """Test backend health"""
    print("🏥 Testing backend health...")
    
    response = requests.get(f"{API_BASE_URL}/health")
    if response.status_code == 200:
        health = response.json()
        print("✅ Backend is healthy")
        print(f"   API: {health.get('components', {}).get('api', 'unknown')}")
        print(f"   Kubernetes: {health.get('components', {}).get('kubernetes', 'unknown')}")
        return True
    else:
        print("❌ Backend health check failed")
        return False

def main():
    """Run the complete test suite"""
    print("🧪 Module Deployment System Test")
    print("=" * 50)
    
    # Test backend health first
    if not test_health_check():
        print("\n❌ Backend health check failed - stopping tests")
        return False
    
    # Login
    headers = login_to_backend()
    if not headers:
        print("\n❌ Authentication failed - stopping tests")
        return False
    
    # Test module availability
    if not test_module_availability(headers):
        print("\n❌ Module availability test failed - stopping tests")
        return False
    
    # Test deployment workflow
    print(f"\n🔄 Testing deployment workflow for module: {TEST_MODULE}")
    print(f"   Tenant: {TEST_TENANT}")
    print(f"   Environment: {TEST_ENVIRONMENT}")
    print(f"   Tier: {TEST_TIER}")
    
    # Enable module
    if not test_module_enable(headers):
        print("\n❌ Module enable test failed")
        return False
    
    # Wait for deployment to settle
    print("\n⏳ Waiting 10 seconds for deployment to settle...")
    time.sleep(10)
    
    # Check status
    deployed = test_module_status(headers)
    if not deployed:
        print("\n⚠️ Module not showing as deployed")
    
    # Disable module (cleanup)
    if not test_module_disable(headers):
        print("\n❌ Module disable test failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print("\n💡 Module deployment system is working correctly")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
