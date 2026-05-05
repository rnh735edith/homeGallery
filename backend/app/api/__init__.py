from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.photos import router as photos_router
from app.api.albums import router as albums_router
from app.api.faces import router as faces_router
from app.api.search import router as search_router
from app.api.setup import router as setup_router
from app.api.metrics import router as metrics_router
from app.api.settings_api import router as settings_router
from app.api.queue import router as queue_router
from app.api.management import router as management_router
from app.api.agents import router as agents_router
from app.api.metadata import router as metadata_router
from app.api.duplicates import router as duplicates_router
from app.api.enhancement import router as enhancement_router
from app.api.analysis import router as analysis_router
from app.api.visual_search import router as visual_search_router
from app.api.api_keys import router as api_keys_router
from app.api.contact import router as contact_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(photos_router)
api_router.include_router(albums_router)
api_router.include_router(faces_router)
api_router.include_router(search_router)
api_router.include_router(setup_router)
api_router.include_router(metrics_router)
api_router.include_router(settings_router)
api_router.include_router(queue_router)
api_router.include_router(management_router)
api_router.include_router(agents_router)
api_router.include_router(metadata_router)
api_router.include_router(duplicates_router)
api_router.include_router(enhancement_router)
api_router.include_router(analysis_router)
api_router.include_router(visual_search_router)
api_router.include_router(api_keys_router)
api_router.include_router(contact_router)

__all__ = ["api_router"]
