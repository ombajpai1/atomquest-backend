import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

CYCLE_YEAR = 2025


async def test_get_checkin_data(client: AsyncClient, employee_headers):
    sheet_resp = await client.get(f"/goals/my-sheet?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    if sheet_resp.status_code != 200:
        pytest.skip("No sheet for checkin test")
    sheet_id = sheet_resp.json().get("id")
    resp = await client.get(f"/checkins/{sheet_id}?quarter=Q1", headers=employee_headers)
    assert resp.status_code in (200, 400)


async def test_employee_log_achievement(client: AsyncClient, employee_headers):
    sheet_resp = await client.get(f"/goals/my-sheet?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    if sheet_resp.status_code != 200:
        pytest.skip("No sheet for achievement test")
    goals = sheet_resp.json().get("goals", [])
    if not goals:
        pytest.skip("No goals for achievement logging test")
    goal_id = goals[0]["id"]
    resp = await client.put(f"/checkins/achievement/{goal_id}", headers=employee_headers, json={
        "quarter": "Q1",
        "actual_value": 750000,
        "status": "on_track"
    })
    assert resp.status_code in (200, 400)  # 400 if quarter window not open


async def test_manager_add_checkin_comment(client: AsyncClient, manager_headers):
    list_resp = await client.get(f"/manager/team-sheets?cycle_year={CYCLE_YEAR}", headers=manager_headers)
    sheets = list_resp.json()
    if not sheets:
        pytest.skip("No sheets for comment test")
    sheet_id = sheets[0]["id"]
    resp = await client.post("/checkins/comment", headers=manager_headers, json={
        "goal_sheet_id": sheet_id,
        "quarter": "Q1",
        "comment": "Good progress this quarter, keep it up."
    })
    assert resp.status_code in (200, 201)


async def test_manager_view_team_checkins(client: AsyncClient, manager_headers):
    resp = await client.get("/checkins/manager/team?quarter=Q1", headers=manager_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_progress_scores_returned(client: AsyncClient, employee_headers):
    resp = await client.get(f"/goals/my-sheet/progress?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, list) or isinstance(data, dict)
