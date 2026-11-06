import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


def check_database(db: Session) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "PostgreSQL connection is healthy"}
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return {"status": "error", "message": "Unable to connect to PostgreSQL"}


def check_disk() -> dict[str, str | int | float]:
    path = settings.upload_dir if settings.upload_dir.exists() else Path("/")

    try:
        usage = shutil.disk_usage(path)
        free_percent = round((usage.free / usage.total) * 100, 2)
        status = "ok" if free_percent >= 10 else "warning"
        return {
            "status": status,
            "path": str(path),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "free_percent": free_percent,
        }
    except OSError:
        logger.exception("Disk health check failed")
        return {"status": "error", "message": "Unable to read disk usage"}


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    database = check_database(db)
    disk = check_disk()

    healthy = database["status"] == "ok"

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "error",
            "service": settings.app_name,
            "environment": settings.app_env,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": database,
                "disk": disk,
            },
        },
    )
