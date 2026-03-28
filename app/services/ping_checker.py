import asyncio

import ping3

from app.models.check import CheckStatus
from app.services.check_result import CheckResult


async def check_ping(hostname: str, timeout: int) -> CheckResult:
    try:
        delay = await asyncio.to_thread(ping3.ping, hostname, timeout=timeout)

        if delay is None:
            return CheckResult(CheckStatus.DOWN, None, None, "Request timed out")
        elif delay is False:
            return CheckResult(CheckStatus.DOWN, None, None, "Host unreachable")
        else:
            return CheckResult(CheckStatus.UP, delay * 1000, None, None)
    except PermissionError:
        return CheckResult(
            CheckStatus.DOWN, None, None, "ICMP requires root privileges"
        )
    except Exception as e:
        return CheckResult(CheckStatus.DOWN, None, None, f"Ping error: {e}")
