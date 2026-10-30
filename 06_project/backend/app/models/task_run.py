from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.task_log import TaskLog


class TaskRun(Base):
    __tablename__ = "task_runs"
    __table_args__ = (
        CheckConstraint(
            "task_type IN ('health_check', 'sync_data', 'process_files', 'e2e_test')",
            name="task_runs_task_type_check",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'cancelled')",
            name="task_runs_status_check",
        ),
        CheckConstraint(
            "progress BETWEEN 0 AND 100",
            name="task_runs_progress_check",
        ),
        Index("idx_task_runs_status_created_at", "status", "created_at"),
        Index("idx_task_runs_task_type_created_at", "task_type", "created_at"),
        Index("idx_task_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="queued",
        server_default=text("'queued'"),
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    logs: Mapped[list[TaskLog]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="TaskLog.id",
        passive_deletes=True,
    )
