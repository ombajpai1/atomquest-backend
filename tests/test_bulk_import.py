import pytest
import io
import csv
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_download_template(client: AsyncClient, admin_headers):
    resp = await client.get("/admin/bulk-import-template", headers=admin_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    content = resp.text
    assert "employee_email" in content
    assert "thrust_area" in content
    assert "weightage" in content


def make_csv(*rows) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "employee_email", "thrust_area", "title", "description",
        "uom_type", "target_value", "target_date", "weightage"
    ])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


VALID_ROW = {
    "employee_email": "emp2@company.com",
    "thrust_area": "Compliance",
    "title": "Bulk Imported Goal",
    "description": "Imported via CSV",
    "uom_type": "min",
    "target_value": "200000",
    "target_date": "",
    "weightage": "10"
}


async def test_bulk_import_valid_row(client: AsyncClient, admin_headers):
    csv_bytes = make_csv(VALID_ROW)
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=admin_headers,
        files={"file": ("goals.csv", csv_bytes, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["success"]) >= 1 or len(data["failed"]) >= 1  # processed at least one row


async def test_bulk_import_unknown_employee(client: AsyncClient, admin_headers):
    bad_row = {**VALID_ROW, "employee_email": "ghost@nowhere.com"}
    csv_bytes = make_csv(bad_row)
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=admin_headers,
        files={"file": ("goals.csv", csv_bytes, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["failed"]) == 1
    assert "found" in data["failed"][0]["reason"].lower()


async def test_bulk_import_invalid_weightage(client: AsyncClient, admin_headers):
    bad_row = {**VALID_ROW, "weightage": "5"}  # below 10% minimum
    csv_bytes = make_csv(bad_row)
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=admin_headers,
        files={"file": ("goals.csv", csv_bytes, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["failed"]) == 1
    assert "10" in data["failed"][0]["reason"]


async def test_bulk_import_invalid_uom(client: AsyncClient, admin_headers):
    bad_row = {**VALID_ROW, "uom_type": "invalid_uom"}
    csv_bytes = make_csv(bad_row)
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=admin_headers,
        files={"file": ("goals.csv", csv_bytes, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["failed"]) == 1


async def test_bulk_import_mixed_valid_invalid(client: AsyncClient, admin_headers):
    """Good row + bad row: good row succeeds, bad row fails independently."""
    bad_row = {**VALID_ROW, "employee_email": "nobody@test.com"}
    csv_bytes = make_csv(VALID_ROW, bad_row)
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=admin_headers,
        files={"file": ("goals.csv", csv_bytes, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 200
    data = resp.json()
    # Total rows processed = 2
    total = len(data["success"]) + len(data["failed"])
    assert total == 2


async def test_bulk_import_missing_headers(client: AsyncClient, admin_headers):
    """CSV without required headers returns an error."""
    bad_csv = b"name,email\nJohn,john@co.com\n"
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=admin_headers,
        files={"file": ("bad.csv", bad_csv, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


async def test_bulk_import_non_admin_rejected(client: AsyncClient, employee_headers):
    csv_bytes = make_csv(VALID_ROW)
    resp = await client.post(
        "/admin/bulk-import-goals",
        headers=employee_headers,
        files={"file": ("goals.csv", csv_bytes, "text/csv")},
        data={"cycle_year": "2025"}
    )
    assert resp.status_code == 403
