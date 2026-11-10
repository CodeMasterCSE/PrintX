import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.connection import SessionLocal
from app.database.init_db import init_db
from app.api.router import api_router
from app.core.events import event_broadcaster

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting PrintX Backend Service...")
    logger.info(f"Target Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")

    # Register running event loop with SSE event broadcaster
    try:
        loop = asyncio.get_running_loop()
        event_broadcaster.set_loop(loop)
    except RuntimeError:
        pass

    purge_task = None
    # Initialize database tables and initial baseline seed data only in non-test mode
    if settings.ENVIRONMENT != "testing":
        db = SessionLocal()
        try:
            init_db(db)
            from app.services.job_service import JobService
            reconcile_result = JobService.reconcile_stale_jobs(db)
            if reconcile_result["total_processed"] > 0:
                logger.info(f"Startup crash recovery executed: {reconcile_result}")
        finally:
            db.close()

        # Start periodic background privacy shredding worker (every 5 minutes)
        async def periodic_document_purge():
            from app.services.document_service import DocumentService
            while True:
                try:
                    await asyncio.sleep(300)
                    with SessionLocal() as session:
                        result = DocumentService.purge_expired_documents(session, retention_minutes=15)
                        if result["purged_count"] > 0:
                            logger.info(f"Automated Privacy Shredder: purged {result['purged_count']} document(s), freed {result['freed_mb']} MB.")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Periodic privacy purge error: {e}")

        purge_task = asyncio.create_task(periodic_document_purge())

    yield

    if purge_task:
        purge_task.cancel()
        try:
            await purge_task
        except asyncio.CancelledError:
            pass

    logger.info("PrintX Backend Service shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PrintX — Smart Self-Service Printing Platform Core Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration for Frontend Web Client and Kiosk displays
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": "PrintX Backend API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact system administrator."}
    )
