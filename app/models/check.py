import enum
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CheckType(str, enum.Enum):
    HTTP = "http"
    PING = "ping"


class CheckStatus(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class Check(Base):
    """Single availability check result for a monitor (HTTP or ping)."""

    __tablename__ = "checks"
    __table_args__ = (
        Index("ix_checks_monitor_checked_at", "monitor_id", "checked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    monitor_id: Mapped[int] = mapped_column(
        ForeignKey("monitors.id", ondelete="CASCADE")
    )
    check_type: Mapped[CheckType] = mapped_column(Enum(CheckType))
    status: Mapped[CheckStatus] = mapped_column(Enum(CheckStatus))
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    monitor = relationship("Monitor", back_populates="checks")
