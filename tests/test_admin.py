import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_admin_list_users(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) >= 4  # at least the 4 seeded users
    emails = [u["email"] for u in users]
    assert "admin@company.com" in emails
    assert "emp1@company.com" in emails


async def test_admin_create_user(client: AsyncClient, admin_headers):
    resp = await client.post("/admin/users", headers=admin_headers, json={
        "name": "Test User",
        "email": "testuser_new@company.com",
        "password": "Test@1234",
        "role": "employee",
        "department": "Engineering"
    })
    assert resp.status_code in (200, 201)
    assert resp.json()["email"] == "testuser_new@company.com"


async def test_admin_create_duplicate_user(client: AsyncClient, admin_headers):
    """Creating a user with an existing email must fail."""
    resp = await client.post("/admin/users", headers=admin_headers, json={
        "name": "Duplicate",
        "email": "emp1@company.com",
        "password": "Test@1234",
        "role": "employee",
        "department": "Engineering"
    })
    assert resp.status_code in (400, 409)


async def test_admin_update_user(client: AsyncClient, admin_headers):
    list_resp = await client.get("/admin/users", headers=admin_headers)
    users = list_resp.json()
    emp = next((u for u in users if u["role"] == "employee"), None)
    if not emp:
        pytest.skip("No employee found to update")
    resp = await client.put(f"/admin/users/{emp['id']}", headers=admin_headers, json={
        "department": "Updated Department"
    })
    assert resp.status_code == 200


async def test_admin_get_cycle_config(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/cycle", headers=admin_headers)
    assert resp.status_code in (200, 404)


async def test_admin_create_cycle_config(client: AsyncClient, admin_headers):
    resp = await client.post("/admin/cycle", headers=admin_headers, json={
        "cycle_year": 2026,
        "goal_setting_open": "2026-01-01",
        "q1_open": "2026-04-01",
        "q2_open": "2026-07-01",
        "q3_open": "2026-10-01",
        "q4_open": "2026-12-15",
        "is_active": False
    })
    assert resp.status_code in (200, 201)


async def test_admin_shared_goals(client: AsyncClient, admin_headers):
    # Get a goal to share
    list_resp = await client.get("/admin/users", headers=admin_headers)
    employees = [u for u in list_resp.json() if u["role"] == "employee"]
    if len(employees) < 2:
        pytest.skip("Need at least 2 employees for shared goal test")

    # Get the first employee's goals
    sheet_resp = await client.get(f"/goals/my-sheet?cycle_year=2025", headers={
        "Authorization": f"Bearer {(await client.post('/auth/login', data={'username': employees[0]['email'], 'password': 'Emp@123'})).json()['access_token']}"
    })
    if sheet_resp.status_code != 200:
        pytest.skip("Could not fetch sheet for shared goal test")
    goals = sheet_resp.json().get("goals", [])
    if not goals:
        pytest.skip("No goals to share")

    resp = await client.post("/admin/shared-goals", headers=admin_headers, json={
        "goal_id": goals[0]["id"],
        "employee_ids": [employees[1]["id"]]
    })
    assert resp.status_code in (200, 201, 400)


async def test_admin_unlock_sheet(client: AsyncClient, admin_headers, manager_headers):
    # Find an approved sheet to unlock
    list_resp = await client.get("/manager/team-sheets?cycle_year=2025", headers=manager_headers)
    sheets = list_resp.json()
    approved = [s for s in sheets if s.get("status") == "approved"]
    if not approved:
        pytest.skip("No approved sheets to unlock")
    sheet_id = approved[0]["id"]
    resp = await client.put(f"/admin/unlock-sheet/{sheet_id}", headers=admin_headers)
    assert resp.status_code in (200, 400)


async def test_admin_get_audit_log(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/audit-log", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_admin_audit_log_filter(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/audit-log?entity_type=goal", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    for entry in data:
        assert entry.get("entity_type") == "goal"
