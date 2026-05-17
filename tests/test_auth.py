import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_login_employee_success(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "emp1@company.com", "password": "Emp@123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "employee"


async def test_login_manager_success(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "manager@company.com", "password": "Manager@123"
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "manager"


async def test_login_admin_success(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "admin@company.com", "password": "Admin@123"
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "admin"


async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "emp1@company.com", "password": "wrongpassword"
    })
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post("/auth/login", data={
        "username": "nobody@company.com", "password": "Emp@123"
    })
    assert resp.status_code == 401


async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/goals/my-sheet")
    assert resp.status_code == 401


async def test_protected_route_invalid_token(client: AsyncClient):
    resp = await client.get("/goals/my-sheet", headers={"Authorization": "Bearer fake.token.here"})
    assert resp.status_code == 401
