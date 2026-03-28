from collections import defaultdict
from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.check import Check, CheckType, CheckStatus
from app.models.monitor import Monitor
from app.schemas.check import CheckPairResponse, PaginatedCheckPairs

router = APIRouter(prefix="/api/monitors", tags=["checks"])


def _build_http_response(status_code: int | None) -> str | None:
    """Build a human-readable string from an HTTP status code."""
    if status_code is None:
        return None
    try:
        phrase = HTTPStatus(status_code).phrase
        return f"{status_code} {phrase}"
    except ValueError:
        return str(status_code)


def _combined_status(http_status: CheckStatus, ping_status: CheckStatus) -> str:
    up_count = (http_status == CheckStatus.UP) + (ping_status == CheckStatus.UP)
    if up_count == 2:
        return "up"
    elif up_count == 1:
        return "partial"
    return "down"


@router.get("/{monitor_id}/checks", response_model=PaginatedCheckPairs)
async def get_checks(
    monitor_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated check history for a monitor, newest first."""
    monitor = await db.get(Monitor, monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    total = (
        await db.execute(
            select(func.count(func.distinct(Check.checked_at))).where(
                Check.monitor_id == monitor_id
            )
        )
    ).scalar()

    page_timestamps = (
        (
            await db.execute(
                select(Check.checked_at)
                .where(Check.monitor_id == monitor_id)
                .group_by(Check.checked_at)
                .order_by(Check.checked_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )

    if not page_timestamps:
        return PaginatedCheckPairs(items=[], total=total, limit=limit, offset=offset)

    checks = (
        (
            await db.execute(
                select(Check).where(
                    Check.monitor_id == monitor_id,
                    Check.checked_at.in_(page_timestamps),
                )
            )
        )
        .scalars()
        .all()
    )

    groups: dict[object, list[Check]] = defaultdict(list)
    for c in checks:
        groups[c.checked_at].append(c)

    items = []
    for ts in sorted(groups, reverse=True):
        group = groups[ts]
        http_check = next((c for c in group if c.check_type == CheckType.HTTP), None)
        ping_check = next((c for c in group if c.check_type == CheckType.PING), None)

        items.append(
            CheckPairResponse(
                checked_at=ts,
                ping_ms=ping_check.response_time_ms if ping_check else None,
                http_response=_build_http_response(
                    http_check.status_code if http_check else None,
                ),
                combined_status=_combined_status(
                    http_check.status if http_check else CheckStatus.DOWN,
                    ping_check.status if ping_check else CheckStatus.DOWN,
                ),
            )
        )

    return PaginatedCheckPairs(items=items, total=total, limit=limit, offset=offset)
