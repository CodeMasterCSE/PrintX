from fastapi import APIRouter
from app.api.routes import health, auth, pricing, printers, kiosks, documents, jobs, payments, admin

api_router = APIRouter()

# Core system routes
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(pricing.router)
api_router.include_router(printers.router)
api_router.include_router(kiosks.router)
api_router.include_router(jobs.router)
api_router.include_router(payments.router)
api_router.include_router(admin.router)

