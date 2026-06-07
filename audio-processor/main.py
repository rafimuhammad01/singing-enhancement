import os

from fastapi import FastAPI

from logging_config import setup_logging
from routers import search as search_router

setup_logging(os.environ.get("LOG_LEVEL", "info"))

app = FastAPI(title="cantus audio-processor")
app.include_router(search_router.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
