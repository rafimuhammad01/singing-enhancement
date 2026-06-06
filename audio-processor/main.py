import os

from fastapi import FastAPI

from logging_config import setup_logging

setup_logging(os.environ.get("LOG_LEVEL", "info"))

app = FastAPI(title="cantus audio-processor")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
