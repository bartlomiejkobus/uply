import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.monitor import Monitor
from app.models.check import CheckType
from app.services.http_checker import check_http
from app.services.ping_checker import check_ping

logger = logging.getLogger(__name__)


class MonitorEngine:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.http_client: httpx.AsyncClient | None = None

    async def start(self):
        """Load active monitors from DB and start the scheduler."""
        self.http_client = httpx.AsyncClient()

        async with async_session_maker() as db:
            result = await db.execute(select(Monitor).where(Monitor.is_active))
            monitors = result.scalars().all()

        for monitor in monitors:
            self._add_job(monitor.id)
            logger.info(f"Loaded monitor: {monitor.url} (id={monitor.id})")

        self.scheduler.start()
        logger.info(f"Scheduler started, {len(monitors)} active monitors")

    async def stop(self):
        self.scheduler.shutdown(wait=False)
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Scheduler stopped")

    @staticmethod
    def _job_id(monitor_id: int) -> str:
        return f"monitor_{monitor_id}"

    def add_monitor(self, monitor_id: int):
        """Add a recurring check job for a monitor."""
        self._add_job(monitor_id)

    def remove_monitor(self, monitor_id: int):
        try:
            self.scheduler.remove_job(self._job_id(monitor_id))
            logger.info(f"Removed job: {self._job_id(monitor_id)}")
        except JobLookupError:
            pass

    def _add_job(self, monitor_id: int):
        self.scheduler.add_job(
            self._run_check,
            "interval",
            seconds=settings.CHECK_INTERVAL_SECONDS,
            args=[monitor_id],
            id=self._job_id(monitor_id),
            replace_existing=True,
        )

    async def _run_check(self, monitor_id: int):
        """Run HTTP + ping checks concurrently and save results to DB."""
        async with async_session_maker() as db:
            monitor = await db.get(Monitor, monitor_id)
            if not monitor:
                logger.warning(f"Monitor {monitor_id} not found, skipping")
                return

            timeout = settings.DEFAULT_TIMEOUT_SECONDS
            hostname = urlparse(monitor.url).hostname
            now = datetime.now(timezone.utc)

            http_result, ping_result = await asyncio.gather(
                check_http(monitor.url, timeout, self.http_client),
                check_ping(hostname, timeout),
            )

            db.add(http_result.to_check(monitor_id, CheckType.HTTP, now))
            db.add(ping_result.to_check(monitor_id, CheckType.PING, now))
            await db.commit()

            http_time = f" ({http_result.response_time_ms:.0f}ms)" if http_result.response_time_ms else ""
            logger.info(
                f"Check {monitor.url}: "
                f"HTTP={http_result.status.value}{http_time} "
                f"Ping={ping_result.status.value}"
            )


monitor_engine = MonitorEngine()
