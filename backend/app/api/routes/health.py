from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.database.connection import get_db
from app.schemas.common import HealthResponse, HealthReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Liveness probe: returns status of the service."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/health/ready", response_model=HealthReadyResponse, tags=["Health"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe: validates database connectivity and storage volume availability."""
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "ready"
    except Exception as e:
        db_status = f"error: {str(e)}"

    storage_status = "unhealthy"
    try:
        storage_path = settings.resolved_storage_path
        test_file = storage_path / ".healthcheck"
        test_file.write_text("ok")
        test_file.unlink()
        storage_status = "ready"
    except Exception as e:
        storage_status = f"error: {str(e)}"

    is_ready = db_status == "ready" and storage_status == "ready"

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": db_status,
                "storage": storage_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    return HealthReadyResponse(
        status="ready",
        database=db_status,
        storage=storage_status,
        timestamp=datetime.now(timezone.utc)
    )

