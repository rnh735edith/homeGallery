import os
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.logging_config import setup_logging, get_logger
from app.config import get_settings
from app.database import init_db, SessionFactory
from app.api import api_router
from app.workers.face_worker import FaceWorker
from app.workers.thumbnail_worker import ThumbnailWorker
from app.agents.orchestrator import AgentOrchestrator
from app.agents.metadata_agent import MetadataAgent
from app.agents.organization_agent import OrganizationAgent
from app.agents.enhancement_agent import EnhancementAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.search_agent import SearchAgent
from app.services.notification_hub import NotificationHub
from app.services.telegram_service import TelegramService
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
    organization_agent = OrganizationAgent(settings)
    orchestrator.register(organization_agent)
    enhancement_agent = EnhancementAgent(settings)
    orchestrator.register(enhancement_agent)
    analysis_agent = AnalysisAgent(settings)
    orchestrator.register(analysis_agent)
    search_agent = SearchAgent(settings)
    orchestrator.register(search_agent)
    agents_api.orchestrator = orchestrator
    orchestrator.start_all()
    logger.info("Agent orchestrator started")

    notification_hub = NotificationHub()
    try:
        db = SessionFactory()
        telegram_service = TelegramService.from_db(db)
        notification_hub.register("telegram", telegram_service)
        db.close()
    except Exception as e:
        logger.warning(f"Failed to initialize Telegram notifications: {e}")

    async def _notify_startup():
        try:
            settings = get_settings()
            await notification_hub.notify_async(
                "server_start",
                server_url=f"http://{settings.HOST}:{settings.PORT}",
            )
        except Exception as e:
            logger.debug(f"Startup notification error: {e}")

    asyncio.create_task(_notify_startup())
    app.state.notification_hub = notification_hub

    logger.info("=" * 60)
    logger.info("HomeGallery backend ready")

    yield

    logger.info("Shutting down HomeGallery backend...")
    try:
        await notification_hub.notify_async("server_shutdown")
    except Exception:
        pass
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
        # Prevent directory traversal
        if ".." in full_path or full_path.startswith("/"):
            if os.path.isfile(frontend_index):
                return FileResponse(frontend_index)
        file_path = os.path.realpath(os.path.join(frontend_dist, full_path))
        frontend_dist_real = os.path.realpath(frontend_dist)
        # Ensure the resolved path is within the frontend dist directory
        if not file_path.startswith(frontend_dist_real + os.sep) and file_path != frontend_dist_real:
            if os.path.isfile(frontend_index):
                return FileResponse(frontend_index)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        if os.path.isfile(frontend_index):
            return FileResponse(frontend_index)
    return {"status": "ok", "version": "1.0.0"}
