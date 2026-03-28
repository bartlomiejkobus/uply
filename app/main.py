from fastapi import FastAPI

app = FastAPI(
    title="Uply",
    description="Web service availability monitor",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"name": "Uply", "status": "ok"}
