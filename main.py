from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from routers import auth_router, goals_router, checkins_router, admin_router, reports_router
from routers.bulk_router import router as bulk_router
from routers.escalation_router import router as escalation_router
from scheduler import scheduler, run_escalation_check

# Create DB tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from seed import seed_data
    seed_data()
    run_escalation_check()   # run once immediately on startup
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="AtomQuest Hackathon - Goal Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174","https://atomquest-frontend-orpin.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(goals_router.emp_router)
app.include_router(goals_router.mgr_router)
app.include_router(checkins_router.router)
app.include_router(admin_router.router)
app.include_router(reports_router.router)
app.include_router(bulk_router)
app.include_router(escalation_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to AtomQuest Hackathon API"}
