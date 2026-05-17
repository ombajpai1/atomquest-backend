import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_trigger_escalation_check(client: AsyncClient, admin_headers):
    resp = await client.post("/admin/escalations/trigger", headers=admin_headers)
    assert resp.status_code == 200
    assert "triggered" in resp.json().get("message", "").lower()


async def test_list_escalations(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/escalations/", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_resolved_escalations(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/escalations/?resolved=true", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_resolve_escalation(client: AsyncClient, admin_headers):
    # Trigger first to ensure there's something to resolve
    await client.post("/admin/escalations/trigger", headers=admin_headers)
    list_resp = await client.get("/admin/escalations/?resolved=false", headers=admin_headers)
    alerts = list_resp.json()
    if not alerts:
        pytest.skip("No active escalation alerts to resolve")
    alert_id = alerts[0]["id"]
    resp = await client.put(f"/admin/escalations/{alert_id}/resolve", headers=admin_headers)
    assert resp.status_code == 200

    # Verify it's now resolved
    verify_resp = await client.get(f"/admin/escalations/?resolved=true", headers=admin_headers)
    resolved_ids = [a["id"] for a in verify_resp.json()]
    assert alert_id in resolved_ids


async def test_resolve_nonexistent_escalation(client: AsyncClient, admin_headers):
    resp = await client.put("/admin/escalations/999999/resolve", headers=admin_headers)
    assert resp.status_code == 404


async def test_escalation_trigger_non_admin_rejected(client: AsyncClient, employee_headers):
    resp = await client.post("/admin/escalations/trigger", headers=employee_headers)
    assert resp.status_code == 403
