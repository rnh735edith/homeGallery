import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.logging_config import setup_logging, get_logger
from app.config import get_settings
from app.database import init_db
from app.api import api_router
from app.workers.face_worker import FaceWorker
from app.workers.thumbnail_worker import ThumbnailWorker
from app.agents.orchestrator import AgentOrchestrator
from app.agents.metadata_agent import MetadataAgent
import app.api.agents as agents_api

setup_logging()
logger = get_logger(__name__)
access_logger = get_logger("homegallery.access")

settings = get_settings()

face_worker = FaceWorker()
thumbnail_worker = ThumbnailWorker()


def ensure_directories():
    dirs = [
        settings.DATA_DIR,
        settings.PHOTO_DIR,
        settings.THUMBNAIL_DIR,
        settings.FACE_ENCODING_DIR,
        "data/logs",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Starting HomeGallery backend...")
    logger.info(f"Python: {settings}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Photo dir: {settings.PHOTO_DIR}")
    logger.info(f"Thumbnail dir: {settings.THUMBNAIL_DIR}")

    ensure_directories()
    logger.info("Directories ensured")

    init_db()
    logger.info("Database initialized")

    face_worker.start()
    logger.info("Face worker started")

    thumbnail_worker.start()
    logger.info("Thumbnail worker started")

    # Initialize agent orchestrator
    orchestrator = AgentOrchestrator(settings)
    metadata_agent = MetadataAgent(settings)
    orchestrator.register(metadata_agent)
    agents_api.orchestrator = orchestrator
    orchestrator.start_all()
    logger.info("Agent orchestrator started")

    logger.info("=" * 60)
    logger.info("HomeGallery backend ready")

    yield

    logger.info("Shutting down HomeGallery backend...")
    face_worker.stop()
    thumbnail_worker.stop()
    orchestrator.stop_all()
    logger.info("Workers stopped")
    logger.info("Shutdown complete")


app = FastAPI(
    title="HomeGallery",
    description="Home Photo Gallery Application",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    client = request.client.host if request.client else "unknown"
    access_logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - "
        f"{duration:.3f}s - {client}"
    )
    return response


app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
frontend_index = os.path.join(frontend_dist, "index.html")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if os.path.exists(frontend_dist):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        if os.path.isfile(frontend_index):
            return FileResponse(frontend_index)
    return {"status": "ok", "version": "1.0.0"}
