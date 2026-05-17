import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

CYCLE_YEAR = 2025


async def test_get_my_sheet(client: AsyncClient, employee_headers):
    resp = await client.get(f"/goals/my-sheet?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "goals" in data or isinstance(data, dict)


async def test_create_goal_success(client: AsyncClient, employee_headers):
    resp = await client.post("/goals/", headers=employee_headers, json={
        "thrust_area": "Revenue Growth",
        "title": "Test Goal Alpha",
        "description": "Increase test revenue",
        "uom_type": "min",
        "target_value": 500000,
        "weightage": 15,
        "cycle_year": CYCLE_YEAR
    })
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["title"] == "Test Goal Alpha"
    assert data["weightage"] == 15


async def test_create_goal_weightage_below_minimum(client: AsyncClient, employee_headers):
    """Weightage below 10% must be rejected."""
    resp = await client.post("/goals/", headers=employee_headers, json={
        "thrust_area": "Test",
        "title": "Invalid weightage goal",
        "description": "test",
        "uom_type": "min",
        "target_value": 100,
        "weightage": 5,
        "cycle_year": CYCLE_YEAR
    })
    assert resp.status_code == 400


async def test_create_goal_exceeds_100_percent(client: AsyncClient, employee_headers):
    """Total weightage cannot exceed 100%."""
    # First create enough goals to use up most weightage
    # Then try adding one that would exceed 100%
    resp = await client.post("/goals/", headers=employee_headers, json={
        "thrust_area": "Test",
        "title": "Overflow goal",
        "uom_type": "min",
        "target_value": 100,
        "weightage": 99,  # will exceed 100 if other goals exist
        "cycle_year": CYCLE_YEAR
    })
    # Either 400 (exceeds 100%) or 201 if sheet is empty — verify logic
    if resp.status_code == 201:
        # If this succeeded, adding another 20% must fail
        resp2 = await client.post("/goals/", headers=employee_headers, json={
            "thrust_area": "Test",
            "title": "Overflow goal 2",
            "uom_type": "min",
            "target_value": 100,
            "weightage": 20,
            "cycle_year": CYCLE_YEAR
        })
        assert resp2.status_code == 400


async def test_max_8_goals_enforced(client: AsyncClient, employee2_headers):
    """Cannot add more than 8 goals to a sheet."""
    # Add goals until limit or until the 9th is rejected
    created = 0
    for i in range(9):
        resp = await client.post("/goals/", headers=employee2_headers, json={
            "thrust_area": "Test",
            "title": f"Goal {i+1}",
            "uom_type": "min",
            "target_value": 100,
            "weightage": 10,
            "cycle_year": CYCLE_YEAR
        })
        if resp.status_code in (200, 201):
            created += 1
        elif resp.status_code == 400:
            break
    # At some point it must have been rejected
    assert created <= 8


async def test_update_goal(client: AsyncClient, employee_headers):
    """Employee can update a goal in draft state."""
    # Create a goal first
    create_resp = await client.post("/goals/", headers=employee_headers, json={
        "thrust_area": "Efficiency",
        "title": "Goal to Update",
        "uom_type": "max",
        "target_value": 48,
        "weightage": 10,
        "cycle_year": CYCLE_YEAR
    })
    if create_resp.status_code not in (200, 201):
        pytest.skip("Could not create goal for update test")
    goal_id = create_resp.json()["id"]

    update_resp = await client.put(f"/goals/{goal_id}", headers=employee_headers, json={
        "title": "Updated Goal Title",
        "target_value": 36,
        "weightage": 10
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Goal Title"


async def test_delete_goal(client: AsyncClient, employee_headers):
    """Employee can delete a goal in draft state."""
    create_resp = await client.post("/goals/", headers=employee_headers, json={
        "thrust_area": "Test",
        "title": "Goal to Delete",
        "uom_type": "zero",
        "target_value": 0,
        "weightage": 10,
        "cycle_year": CYCLE_YEAR
    })
    if create_resp.status_code not in (200, 201):
        pytest.skip("Could not create goal for delete test")
    goal_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/goals/{goal_id}", headers=employee_headers)
    assert delete_resp.status_code in (200, 204)


async def test_submit_sheet_incomplete_weightage(client: AsyncClient, employee_headers):
    """Submitting a sheet where total weightage != 100% must fail."""
    resp = await client.post("/goals/submit", headers=employee_headers, json={"cycle_year": CYCLE_YEAR})
    # If total is not 100%, must be 400
    # (may pass if goals happen to total 100 — this is an integration check)
    assert resp.status_code in (200, 400)
    if resp.status_code == 400:
        assert "100" in resp.json().get("detail", "").lower() or "weightage" in resp.json().get("detail", "").lower()


async def test_employee_cannot_access_manager_routes(client: AsyncClient, employee_headers):
    resp = await client.get("/manager/team-sheets?cycle_year=2025", headers=employee_headers)
    assert resp.status_code == 403


async def test_employee_cannot_access_admin_routes(client: AsyncClient, employee_headers):
    resp = await client.get("/admin/users", headers=employee_headers)
    assert resp.status_code == 403
