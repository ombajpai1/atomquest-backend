import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
from seed import seed_data

# Use a fresh in-memory SQLite DB for every test session
TEST_DATABASE_URL = "sqlite:///./test_atomquest.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables and seed demo data once for the test session."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    # Seed using the test DB session
    db = TestingSessionLocal()
    from models import User
    if db.query(User).count() == 0:
        seed_data(db)  # pass db session if needed, otherwise fix seed.py logic later
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("test_atomquest.db"):
        try:
            os.remove("test_atomquest.db")
        except PermissionError:
            pass


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Auth helpers ─────────────────────────────────────────────────────────────

async def get_token(client, email: str, password: str) -> str:
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


async def auth_headers(client, email: str, password: str) -> dict:
    token = await get_token(client, email, password)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def employee_headers(client):
    return await auth_headers(client, "emp1@company.com", "Emp@123")


@pytest_asyncio.fixture
async def employee2_headers(client):
    return await auth_headers(client, "emp2@company.com", "Emp@123")


@pytest_asyncio.fixture
async def manager_headers(client):
    return await auth_headers(client, "manager@company.com", "Manager@123")


@pytest_asyncio.fixture
async def admin_headers(client):
    return await auth_headers(client, "admin@company.com", "Admin@123")
