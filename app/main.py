from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.core.config import settings
from app.routers import ai, dashboard, dev, health, inputs, materials, progress, quality

BASE_DIR = Path(__file__).resolve().parents[1]
INDEX_PATH = BASE_DIR / "app" / "static" / "index.html"

app = FastAPI(title=settings.app_name)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(ai.router, prefix=settings.api_prefix)
app.include_router(dev.router, prefix=settings.api_prefix)
app.include_router(inputs.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(dashboard.events_router, prefix=settings.api_prefix)
app.include_router(progress.router, prefix=settings.api_prefix)
app.include_router(materials.router, prefix=settings.api_prefix)
app.include_router(quality.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(INDEX_PATH)
