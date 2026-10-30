from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.task_run import TaskRun


class TaskLog(Base):
    __tablename__ = "task_logs"
    __table_args__ = (
        CheckConstraint(
            "level IN ('debug', 'info', 'warning', 'error')",
            name="task_logs_level_check",
        ),
        Index("idx_task_logs_run_id_id", "run_id", "id"),
        Index("idx_task_logs_level", "level"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("task_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="info",
        server_default=text("'info'"),
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped[TaskRun] = relationship(back_populates="logs")
