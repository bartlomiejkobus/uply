from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.models import Monitor, Check  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/")
async def root():
    return {"name": "Uply", "status": "ok"}
