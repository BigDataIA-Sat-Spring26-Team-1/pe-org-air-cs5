"""
Internal Platform SDK Clients.

Thin async HTTP wrappers around the FastAPI REST endpoints,
allowing the RAG engine to fetch company metadata, signals,
evidence, and scores without importing backend internals.
"""

import httpx
import os
import structlog
from typing import Any, Dict, Optional

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Shared base class
# ---------------------------------------------------------------------------

class SDKClientError(Exception):
    """Raised when an SDK HTTP call returns a non-2xx status."""

    def __init__(self, status_code: int, detail: str, url: str):
        self.status_code = status_code
        self.detail = detail
        self.url = url
        super().__init__(f"[{status_code}] {url}: {detail}")


class BaseSDKClient:
    """
    Async HTTP base shared by cs1/cs2/cs3 clients.

    * Uses ``httpx.AsyncClient`` for non-blocking IO.
    * ``base_url`` defaults to ``http://localhost:8000`` but can be
      overridden via the ``PLATFORM_BASE_URL`` env-var or constructor arg.
    * Every call goes through ``_request`` which handles JSON parsing,
      structured logging, and error wrapping.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url or os.getenv("PLATFORM_BASE_URL", "http://localhost:8000")
        self.timeout = timeout

    # -- internal helpers ---------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Fire an HTTP request and return the parsed JSON response.

        Raises ``SDKClientError`` on non-2xx status codes.
        """
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                )

            if response.status_code >= 400:
                detail = response.text[:500]
                logger.warning(
                    "sdk_request_failed",
                    method=method,
                    url=url,
                    status=response.status_code,
                    detail=detail,
                )
                raise SDKClientError(response.status_code, detail, url)

            return response.json()

        except httpx.RequestError as exc:
            logger.error("sdk_request_error", method=method, url=url, error=str(exc))
            raise SDKClientError(0, str(exc), url) from exc

    # convenience wrappers --------------------------------------------------

    async def _get(self, path: str, **params: Any) -> Any:
        # Strip None values so they don't appear as ?key=None
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", path, params=clean)

    async def _post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        return await self._request("POST", path, json_body=body)
