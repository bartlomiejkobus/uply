from dataclasses import dataclass
from datetime import datetime

from app.models.check import CheckStatus, CheckType, Check


@dataclass
class CheckResult:
    status: CheckStatus
    response_time_ms: float | None
    status_code: int | None
    error_message: str | None

    def to_check(self, monitor_id: int, check_type: CheckType, checked_at: datetime) -> Check:
        """Convert this result into a Check ORM instance."""
        return Check(
            monitor_id=monitor_id,
            check_type=check_type,
            status=self.status,
            response_time_ms=self.response_time_ms,
            status_code=self.status_code,
            error_message=self.error_message,
            checked_at=checked_at,
        )
