from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.complaint_categories import router as complaint_categories_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.cyber_saathi import router as cyber_saathi_router
from app.api.v1.cyber_warriors import router as cyber_warriors_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.resume import router as resume_router
from app.api.v1.suspects import router as suspects_router
from app.api.v1.users import router as users_router
from app.api.v1.warrior_applications import router as warrior_applications_router
from app.api.v1.warrior_reports import router as warrior_reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(complaint_categories_router)
api_router.include_router(complaints_router)
api_router.include_router(cyber_saathi_router)
api_router.include_router(evidence_router)
api_router.include_router(notifications_router)
api_router.include_router(suspects_router)
api_router.include_router(cyber_warriors_router)
api_router.include_router(resume_router)
api_router.include_router(warrior_applications_router)
api_router.include_router(warrior_reports_router)
api_router.include_router(admin_router)
