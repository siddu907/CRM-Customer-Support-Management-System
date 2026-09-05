import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import SessionLocal
from app.routers import attachments, audit_logs, auth, categories, comments, customers, dashboard, notifications, sla, tickets
from app.services.sla import ensure_default_slas
from app.services.background import run_scheduled_jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        ensure_default_slas(db)
    finally:
        db.close()
    stop_event = asyncio.Event()
    job = None
    if settings.database_url.startswith("postgresql"):
        job = asyncio.create_task(run_scheduled_jobs(stop_event))
    try:
        yield
    finally:
        if job:
            stop_event.set()
            await job


app = FastAPI(
    title="CRM & Customer Support Management API",
    version="1.0.0",
    description="Secure ticketing, customer management, SLA monitoring, notifications, and audit logging.",
    lifespan=lifespan,
)


app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(customers.router, prefix="/customers", tags=["Customers"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
app.include_router(comments.router, tags=["Comments"])
app.include_router(attachments.router, tags=["Attachments"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(sla.router, prefix="/sla", tags=["SLA"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
