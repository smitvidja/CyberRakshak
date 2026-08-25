from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.complaint_categories import router as complaint_categories_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.suspects import router as suspects_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(complaint_categories_router)
api_router.include_router(complaints_router)
api_router.include_router(evidence_router)
api_router.include_router(notifications_router)
api_router.include_router(suspects_router)
