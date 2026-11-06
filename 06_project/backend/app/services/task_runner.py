import traceback
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.task_log import TaskLog
from app.models.task_run import TaskRun

LogCallback = Callable[[str, str], None]

_LEVEL_MAP = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARNING": "warning",
    "WARN": "warning",
    "ERROR": "error",
    "CRITICAL": "error",
}


class TaskRunnerService:
    @staticmethod
    def execute_task(
        db: Session,
        task_name: str,
        task_logic_func: Callable[[LogCallback], Any],
        payload: dict[str, Any] | None = None,
    ) -> TaskRun:
        started_at = datetime.now(timezone.utc)

        db_run = TaskRun(
            task_type=task_name,
            status="running",
            started_at=started_at,
            payload=payload or {},
        )
        db.add(db_run)
        db.commit()
        db.refresh(db_run)

        run_id = db_run.id
        TaskRunnerService._log(db, run_id, "INFO", f"Task '{task_name}' started.")

        def log_callback(message: str, level: str = "INFO") -> None:
            TaskRunnerService._log(db, run_id, level, message)

        try:
            summary = task_logic_func(log_callback)

            db_run.status = "success"
            db_run.progress = 100
            db_run.result = (
                summary if isinstance(summary, dict) else {"result": summary}
            )
            db_run.finished_at = datetime.now(timezone.utc)
            TaskRunnerService._log(
                db, run_id, "INFO", f"Task '{task_name}' completed successfully."
            )
        except Exception as exc:
            db.rollback()

            failed_run = db.get(TaskRun, run_id)
            if failed_run is None:
                raise

            failed_run.status = "failed"
            failed_run.error_message = str(exc)
            failed_run.finished_at = datetime.now(timezone.utc)

            error_detail = traceback.format_exc()
            TaskRunnerService._log(
                db,
                run_id,
                "ERROR",
                f"Task failed: {exc}\n{error_detail}",
            )
            db_run = failed_run

        db.commit()
        db.refresh(db_run)
        return db_run

    @staticmethod
    def _log(db: Session, run_id: int, level: str, message: str) -> None:
        normalized_level = _LEVEL_MAP.get(level.upper(), "info")

        log_entry = TaskLog(
            run_id=run_id,
            level=normalized_level,
            message=message,
        )
        db.add(log_entry)
        db.commit()
