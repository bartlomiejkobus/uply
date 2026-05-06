import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import engine, Base
from app.models import Monitor, Check  # noqa: F401
from app.routers import monitors, checks, stats, dashboard
from app.services.monitor_engine import monitor_engine

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception:", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
async def root():
    return {"name": "Uply", "status": "ok"}


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/dashboard", include_in_schema=False)
async def dashboard_frontend():
    return FileResponse("app/static/index.html")
