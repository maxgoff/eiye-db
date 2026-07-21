"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from eiye_db import __version__, db, pii
from eiye_db.api import router
from eiye_db.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.configure()
    if settings.pii_ner_enabled:
        # Fail loud at boot if the NER model is missing, rather than 500-ing (or
        # worse, silently under-redacting) on the first query.
        pii._load_ner()
    yield


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/status")
def status() -> dict:
    return {
        "app": settings.app_name,
        "version": __version__,
        "debug": settings.debug,
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "eiye_db.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
