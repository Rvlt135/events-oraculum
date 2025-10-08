from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.odds_service.api.routes import health, events, admin
from services.odds_service.config import get_odds_service_config

config = get_odds_service_config()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print(f"Starting {config.service_name}...")
    yield
    print(f"Shutting down {config.service_name}...")


app = FastAPI(
    title="Odds Service API",
    description="Internal API for odds collection and normalization",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": config.service_name,
        "version": "0.1.0",
        "status": "running",
    }
