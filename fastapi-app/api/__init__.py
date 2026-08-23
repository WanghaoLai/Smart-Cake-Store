"""Application API router composition.

Routes are registered explicitly so startup behavior and dependencies remain
visible during review. Endpoint implementations belong in their own modules.
"""

from fastapi import APIRouter

from .address import router as address_router
from .admin import router as admin_router
from .auth import router as auth_router
from .category import router as category_router
from .chat import router as chat_router
from .favorite import router as favorite_router
from .files import router as files_router
from .goods import router as goods_router
from .health import router as health_router
from .index import router as index_router
from .knowledge import router as knowledge_router
from .notice import router as notice_router
from .notification import router as notification_router
from .ops import router as ops_router
from .orders import router as orders_router
from .region import router as region_router
from .reviews import router as reviews_router
from .stats import router as stats_router
from .user import router as user_router


api_router = APIRouter()

for router in (
    auth_router,
    address_router,
    admin_router,
    category_router,
    chat_router,
    favorite_router,
    files_router,
    goods_router,
    health_router,
    index_router,
    knowledge_router,
    notice_router,
    notification_router,
    ops_router,
    orders_router,
    region_router,
    reviews_router,
    stats_router,
    user_router,
):
    api_router.include_router(router)


__all__ = ["api_router"]
