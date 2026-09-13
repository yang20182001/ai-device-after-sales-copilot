from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import repositories, retrieval
from app.config import settings
from app.routes import router
from data.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    repositories.settings = settings
    retrieval.settings = settings
    seed_database(settings.database_path)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

static_directory = Path(__file__).resolve().parent / "static"
if static_directory.exists():
    app.mount("/", StaticFiles(directory=static_directory, html=True), name="static")
