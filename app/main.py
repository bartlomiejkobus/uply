from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.models import Monitor, Check  # noqa: F401
from app.routers import monitors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup, dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Uply",
    description="Web service availability monitor",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(monitors.router)


@app.get("/")
async def root():
    return {"name": "Uply", "status": "ok"}
