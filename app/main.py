import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.models import Monitor, Check  # noqa: F401
from app.routers import monitors, checks, stats, dashboard
from app.services.monitor_engine import monitor_engine

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup, dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await monitor_engine.start()
    yield
    await monitor_engine.stop()
    await engine.dispose()


app = FastAPI(
    title="Uply",
    description="Web service availability monitor",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(monitors.router)
app.include_router(checks.router)
app.include_router(stats.router)
app.include_router(dashboard.router)


@app.get("/")
async def root():
    return {"name": "Uply", "status": "ok"}
