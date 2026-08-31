from fastapi import FastAPI, Depends
from sqlalchemy import text
from app.core.database import get_db
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine
from sqlalchemy.orm import Session
from app.models.base import Base
from app.routers import setup, auth, clinics, members, schedules, patients, appointments, billing, reminders, reports, audit
from app.routers import prescriptions, contact, departments
from app.core.logging import setup_logging, setup_db_logging, register_logging_app

setup_logging(debug=False)
setup_db_logging(engine, slow_query_threshold_ms=300.0)

# Development convenience: create tables automatically when running with SQLite.
# Production should use Alembic migrations and PostgreSQL.
if settings.database_url.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)

# Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name, version="1.0.0")
register_logging_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(setup.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clinics.router, prefix="/api/v1")
app.include_router(members.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(patients.router, prefix="/api/v1")
app.include_router(appointments.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(prescriptions.router, prefix="/api/v1")
app.include_router(contact.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/db")
def check_db_connection(db: Session = Depends(get_db)):
    try:
        # Executes a simple SQL ping query
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "connected",
            "database": "PostgreSQL",
            "ping_result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "setup": "/api/v1/setup/status",
    }
