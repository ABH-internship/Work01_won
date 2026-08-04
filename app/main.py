from fastapi import FastAPI

from app.core.config import settings
from app.routers import health, inputs

app = FastAPI(title=settings.app_name)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(inputs.router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.app_name}
