import time

import httpx

from app.models.check import CheckStatus
from app.services.check_result import CheckResult


async def check_http(url: str, timeout: int, client: httpx.AsyncClient) -> CheckResult:
    try:
        start = time.monotonic()
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        elapsed_ms = (time.monotonic() - start) * 1000

        if response.status_code < 400:
            return CheckResult(
                CheckStatus.UP, elapsed_ms, response.status_code, None
            )
        else:
            return CheckResult(
                CheckStatus.DOWN,
                elapsed_ms,
                response.status_code,
                f"HTTP {response.status_code}",
            )
    except httpx.TimeoutException:
        return CheckResult(CheckStatus.DOWN, None, None, f"Timeout after {timeout}s")
    except httpx.ConnectError as e:
        return CheckResult(CheckStatus.DOWN, None, None, f"Connection error: {e}")
    except Exception as e:
        return CheckResult(CheckStatus.DOWN, None, None, f"Error: {e}")
