from collections import defaultdict
from http import HTTPStatus

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.check import Check, CheckType, CheckStatus
from app.schemas.check import CheckPairResponse, PaginatedCheckPairs


def _build_http_response(status_code: int | None) -> str | None:
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


async def get_paginated_checks(
    db: AsyncSession, monitor_id: int, limit: int, offset: int
) -> PaginatedCheckPairs:
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
