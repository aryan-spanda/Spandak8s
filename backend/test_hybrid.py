import pytest
import asyncio
from httpx import AsyncClient
from hybrid_main import app

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_token(client: AsyncClient):
    """Get authentication token for testing."""
    login_data = {"username": "admin", "password": "spanda123!"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test basic health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
    assert "components" in data

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login."""
    login_data = {"username": "admin", "password": "spanda123!"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert "admin" in data["user"]["roles"]

@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient):
    """Test failed login with wrong credentials."""
    login_data = {"username": "admin", "password": "wrongpassword"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_module_definitions(client: AsyncClient, auth_headers):
    """Test getting module definitions from YAML file."""
    response = await client.get("/api/v1/modules/definitions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    assert "resource_tiers" in data

@pytest.mark.asyncio
async def test_list_modules(client: AsyncClient, auth_headers):
    """Test listing all modules."""
    response = await client.get("/api/v1/modules", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    
    if data["modules"]:
        module = data["modules"][0]
        required_fields = ["name", "display_name", "description", "version", "category"]
        for field in required_fields:
            assert field in module

@pytest.mark.asyncio
async def test_validate_modules(client: AsyncClient, auth_headers):
    """Test module validation."""
    # Get available modules first
    modules_response = await client.get("/api/v1/modules", headers=auth_headers)
    modules_data = modules_response.json()
    
    if modules_data["modules"]:
        # Test with valid module
        valid_module = modules_data["modules"][0]["name"]
        payload = {"modules": [valid_module]}
        response = await client.post("/api/v1/modules/validate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0
    
    # Test with invalid module
    payload = {"modules": ["invalid-module-name"]}
    response = await client.post("/api/v1/modules/validate", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0

@pytest.mark.asyncio
async def test_generate_tenant_config(client: AsyncClient, auth_headers):
    """Test tenant configuration generation."""
    # Get available modules first
    modules_response = await client.get("/api/v1/modules", headers=auth_headers)
    modules_data = modules_response.json()
    
    if modules_data["modules"]:
        module_name = modules_data["modules"][0]["name"]
        payload = {
            "tenant_name": "test-tenant",
            "modules": [module_name],
            "tier": "bronze"
        }
        response = await client.post("/api/v1/tenants/generate-config", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["tenant"]["name"] == "test-tenant"
        assert data["tenant"]["tier"] == "bronze"
        assert module_name in data["modules"]
        assert "resourceQuota" in data

@pytest.mark.asyncio
async def test_platform_status(client: AsyncClient, auth_headers):
    """Test getting platform status."""
    response = await client.get("/api/v1/platform/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "platform_status" in data
    assert "total_tenants" in data
    assert "available_modules" in data
    assert "api_version" in data

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test that endpoints require authentication."""
    response = await client.get("/api/v1/modules")
    assert response.status_code == 401
    
    response = await client.get("/api/v1/tenants")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_tier(client: AsyncClient, auth_headers):
    """Test handling of invalid resource tier."""
    payload = {
        "tenant_name": "test-tenant",
        "modules": ["any-module"],
        "tier": "invalid-tier"
    }
    response = await client.post("/api/v1/tenants/generate-config", json=payload, headers=auth_headers)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_get_module_details(client: AsyncClient, auth_headers):
    """Test getting specific module details."""
    # Get available modules first
    modules_response = await client.get("/api/v1/modules", headers=auth_headers)
    modules_data = modules_response.json()
    
    if modules_data["modules"]:
        module_name = modules_data["modules"][0]["name"]
        
        # Test existing module
        response = await client.get(f"/api/v1/modules/{module_name}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == module_name
    
    # Test non-existing module
    response = await client.get("/api/v1/modules/non-existing-module", headers=auth_headers)
    assert response.status_code == 404
