from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import models  # noqa: F401  (registers all tables/relationships)
from api.admin import router as admin_router
from api.auth import router as auth_router
from api.catalog import router as catalog_router
from api.costs import router as costs_router
from api.deps import REFRESHED_TOKEN_HEADER
from api.health import router as health_router
from api.households import router as households_router
from api.months import router as months_router
from api.notifications import router as notifications_router
from api.tasks import router as tasks_router
from api.whatsapp import router as whatsapp_router
from infrastructure.config.settings import settings
from scheduler import Scheduler
from services.errors import DomainError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print(f"Configured CORS origins: {settings.cors_origin_list}")
    # Time-based work (months, auto-close, recurring tasks, reminders, WhatsApp delivery): see scheduler/
    scheduler = Scheduler() if settings.scheduler_enabled else None
    if scheduler:
        scheduler.start()
    yield
    if scheduler:
        await scheduler.stop()


app = FastAPI(title="Ibis", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # The frontend reads renewed sign-in tokens from this header (sliding sessions)
    expose_headers=[REFRESHED_TOKEN_HEADER],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(households_router)
app.include_router(catalog_router)
app.include_router(months_router)
app.include_router(costs_router)
app.include_router(notifications_router)
app.include_router(tasks_router)
app.include_router(whatsapp_router)
