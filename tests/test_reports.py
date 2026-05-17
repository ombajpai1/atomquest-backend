import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

CYCLE_YEAR = 2025


async def test_achievement_report_json(client: AsyncClient, admin_headers):
    resp = await client.get(f"/reports/achievement-report?cycle_year={CYCLE_YEAR}", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_achievement_report_csv_export(client: AsyncClient, admin_headers):
    resp = await client.get(f"/reports/achievement-report/export?cycle_year={CYCLE_YEAR}", headers=admin_headers)
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/csv" in content_type or "application/octet-stream" in content_type
    content = resp.text
    # CSV must have at least a header row
    assert len(content.strip()) > 0
    lines = content.strip().split("\n")
    assert len(lines) >= 1
    # Check expected columns exist in header
    header = lines[0].lower()
    assert "employee" in header or "name" in header


async def test_completion_dashboard(client: AsyncClient, admin_headers):
    resp = await client.get(f"/reports/completion-dashboard?cycle_year={CYCLE_YEAR}&quarter=Q1", headers=admin_headers)
    assert resp.status_code == 200


async def test_reports_non_admin_rejected(client: AsyncClient, employee_headers):
    resp = await client.get(f"/reports/achievement-report?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    assert resp.status_code == 403


async def test_csv_export_non_admin_rejected(client: AsyncClient, employee_headers):
    resp = await client.get(f"/reports/achievement-report/export?cycle_year={CYCLE_YEAR}", headers=employee_headers)
    assert resp.status_code == 403
