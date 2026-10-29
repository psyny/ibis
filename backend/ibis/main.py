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
from db.session import SessionLocal
from infrastructure.config.settings import settings
from services.errors import DomainError
from services.month_service import MonthService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print(f"Configured CORS origins: {settings.cors_origin_list}")
    # Create current/next month tables and apply auto-close for every household.
    db = SessionLocal()
    try:
        MonthService(db).sync_all()
    except Exception as exc:  # never block startup (e.g. migrations not applied yet)
        print(f"Startup month sync skipped: {exc}")
    finally:
        db.close()
    yield


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
