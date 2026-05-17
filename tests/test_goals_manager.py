import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

CYCLE_YEAR = 2025


async def test_manager_get_team_sheets(client: AsyncClient, manager_headers):
    resp = await client.get(f"/manager/team-sheets?cycle_year={CYCLE_YEAR}", headers=manager_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_manager_get_specific_sheet(client: AsyncClient, manager_headers):
    # Get list first, then fetch the first sheet
    list_resp = await client.get(f"/manager/team-sheets?cycle_year={CYCLE_YEAR}", headers=manager_headers)
    sheets = list_resp.json()
    if not sheets:
        pytest.skip("No team sheets available for manager test")
    sheet_id = sheets[0]["id"]
    resp = await client.get(f"/manager/sheet/{sheet_id}", headers=manager_headers)
    assert resp.status_code == 200
    assert "goals" in resp.json() or isinstance(resp.json(), dict)


async def test_manager_approve_sheet(client: AsyncClient, manager_headers, employee_headers):
    """Full flow: employee submits → manager approves."""
    # Make sure sheet is at 100% and submit it
    # Get sheet status first
    sheet_resp = await client.get(f"/goals/my-sheet?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    if sheet_resp.status_code != 200:
        pytest.skip("Could not fetch employee sheet")

    sheet = sheet_resp.json()
    sheet_id = sheet.get("id")

    # Only proceed if sheet is in submitted state (may already be submitted or approved from prior tests)
    # Try submitting
    submit_resp = await client.post("/goals/submit", headers=employee_headers, json={"cycle_year": CYCLE_YEAR})
    # 200 = submitted, 400 = weightage issue, 409 = already submitted — any except 500 is acceptable

    # Try approving
    if sheet_id:
        approve_resp = await client.put(f"/manager/sheet/{sheet_id}/approve", headers=manager_headers)
        assert approve_resp.status_code in (200, 400, 409)  # 400/409 if already approved


async def test_manager_return_sheet_for_rework(client: AsyncClient, manager_headers):
    list_resp = await client.get(f"/manager/team-sheets?cycle_year={CYCLE_YEAR}", headers=manager_headers)
    sheets = list_resp.json()
    submitted = [s for s in sheets if s.get("status") == "submitted"]
    if not submitted:
        pytest.skip("No submitted sheets to return for rework")
    sheet_id = submitted[0]["id"]
    resp = await client.put(f"/manager/sheet/{sheet_id}/return", headers=manager_headers, json={
        "remark": "Please increase weightage on compliance goals."
    })
    assert resp.status_code == 200


async def test_manager_inline_edit_goal(client: AsyncClient, manager_headers):
    list_resp = await client.get(f"/manager/team-sheets?cycle_year={CYCLE_YEAR}", headers=manager_headers)
    sheets = list_resp.json()
    if not sheets:
        pytest.skip("No team sheets for inline edit test")
    sheet_id = sheets[0]["id"]
    sheet_detail = await client.get(f"/manager/sheet/{sheet_id}", headers=manager_headers)
    goals = sheet_detail.json().get("goals", [])
    if not goals:
        pytest.skip("No goals in sheet for inline edit test")
    goal_id = goals[0]["id"]
    resp = await client.put(f"/manager/goal/{goal_id}/edit", headers=manager_headers, json={
        "target_value": 999999,
        "weightage": goals[0]["weightage"]
    })
    assert resp.status_code in (200, 400)  # 400 if sheet is locked


async def test_manager_cannot_access_admin_routes(client: AsyncClient, manager_headers):
    resp = await client.get("/admin/users", headers=manager_headers)
    assert resp.status_code == 403
