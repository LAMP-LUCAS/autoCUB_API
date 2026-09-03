from autocub.api.routers.cub import router as cub_router
from autocub.api.routers.metadata import router as metadata_router
from autocub.api.routers.admin import router as admin_router
from autocub.api.routers.kb import router as kb_router
from autocub.api.routers.calc import router as calc_router

__all__ = ["cub_router", "metadata_router", "admin_router", "kb_router", "calc_router"]
