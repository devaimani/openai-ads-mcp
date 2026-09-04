"""Async HTTP client for the OpenAI Ads API.

Provides three things other public clients for this API lack:

* **Retry with backoff** — including 409, which occurs sporadically (see
  the note in errors.py).
* **Client-side rate limiting** — the API allows 600 req/min per endpoint and
  1200 req/min overall, counted per account *and* per IP.
* **Auto-pagination** — a cursor loop instead of manual threading.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from typing import Any, Literal

import httpx

from .config import Config
from .errors import AdsAPIError, extract_message

__version__ = "0.1.0"

#: 600 req/min per endpoint, 1200 req/min overall. Deliberately just under.
_PER_ENDPOINT_PER_MIN = 550
_GLOBAL_PER_MIN = 1_100
_WINDOW = 60.0


class RateLimiter:
    """Sliding-window rate limiter, per endpoint and global."""

    def __init__(
        self,
        per_endpoint: int = _PER_ENDPOINT_PER_MIN,
        global_limit: int = _GLOBAL_PER_MIN,
    ) -> None:
        self._per_endpoint = per_endpoint
        self._global_limit = global_limit
        self._endpoint_hits: dict[str, deque[float]] = {}
        self._global_hits: deque[float] = deque()
        self._lock = asyncio.Lock()

    @staticmethod
    def _prune(hits: deque[float], now: float) -> None:
        while hits and now - hits[0] > _WINDOW:
            hits.popleft()

    async def acquire(self, endpoint: str) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                hits = self._endpoint_hits.setdefault(endpoint, deque())
                self._prune(hits, now)
                self._prune(self._global_hits, now)

                waits: list[float] = []
                if len(hits) >= self._per_endpoint:
                    waits.append(_WINDOW - (now - hits[0]))
                if len(self._global_hits) >= self._global_limit:
                    waits.append(_WINDOW - (now - self._global_hits[0]))

                if not waits:
                    hits.append(now)
                    self._global_hits.append(now)
                    return

                delay = max(0.01, min(waits))

            await asyncio.sleep(delay)


#: Fixed path segments. Without this list "/ad_account" would be read as an
#: ID because it contains an underscore.
_KNOWN_SEGMENTS = frozenset(
    {
        "ad_account",
        "ad_accounts",
        "campaigns",
        "ad_groups",
        "ads",
        "insights",
        "geo_lookup",
        "search",
        "custom_audiences",
        "conversions",
        "pixels",
        "api_keys",
        "event_settings",
        "events",
        "feeds",
        "uploads",
        "upload",
        "products",
        "query",
        "business_agents",
        "business_agent_tools",
        "lead_forms",
        "lead_sync_subscriptions",
        "negative_keywords",
        "spend_limit_windows",
        "activate",
        "pause",
        "archive",
        "preview",
        "publish",
        "brand",
        "me",
        "add",
        "remove",
        "replace",
        "merge",
        "operations",
        "test_submissions",
        "sftp_access",
        "bulk_mutation_jobs",
    }
)


def _endpoint_key(path: str) -> str:
    """Normalise a path to its endpoint form.

    ``/campaigns/camp_123/insights`` -> ``/campaigns/{id}/insights``
    ``/ad_account`` -> ``/ad_account`` (fixed path, not an ID)
    """
    parts = []
    for segment in path.strip("/").split("/"):
        if not segment:
            continue
        if segment in _KNOWN_SEGMENTS:
            parts.append(segment)
        elif any(c.isdigit() for c in segment) or "_" in segment:
            parts.append("{id}")
        else:
            parts.append(segment)
    return "/" + "/".join(parts)


class AdsClient:
    """Minimal REST client. There is no official Python SDK for this API."""

    def __init__(
        self, config: Config, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._config = config
        self._limiter = RateLimiter()
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            follow_redirects=False,
            transport=transport,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Accept": "application/json",
                "User-Agent": f"openai-ads-mcp/{__version__}",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AdsClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        idempotency_key: str | None = None,
        base_url: str | None = None,
    ) -> Any:
        """One request with retry. Raises ``AdsAPIError`` on final failure."""
        url = (base_url or self._config.ads_base_url) + path
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key[:255]
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        endpoint = _endpoint_key(path)
        last: AdsAPIError | None = None

        for attempt in range(1, self._config.max_retries + 1):
            await self._limiter.acquire(endpoint)
            try:
                response = await self._client.request(
                    method, url, params=params, json=json_body, headers=headers
                )
            except httpx.HTTPError as exc:
                last = AdsAPIError(0, f"{type(exc).__name__}: {exc}", path=path, attempts=attempt)
            else:
                request_id = response.headers.get("x-request-id")
                body = self._decode(response)

                if response.is_success:
                    return body

                last = AdsAPIError(
                    response.status_code,
                    extract_message(body, response.reason_phrase or "Fehler"),
                    body=body,
                    request_id=request_id,
                    path=path,
                    attempts=attempt,
                )
                if not last.is_retryable:
                    raise last

                retry_after = self._retry_after(response)
                if retry_after is not None:
                    await asyncio.sleep(min(retry_after, 30.0))
                    continue

            if attempt < self._config.max_retries:
                # Exponential with jitter so parallel calls do not retry in
                # lockstep.
                await asyncio.sleep(
                    min(1.5 * (2 ** (attempt - 1)), 20.0) * (0.7 + random.random() * 0.6)
                )

        assert last is not None
        raise last

    async def get(self, path: str, **params: Any) -> Any:
        clean = {k: v for k, v in params.items() if v is not None}
        return await self.request("GET", path, params=clean or None)

    async def post(
        self,
        path: str,
        body: Any = None,
        *,
        idempotency_key: str | None = None,
        base_url: str | None = None,
    ) -> Any:
        return await self.request(
            "POST", path, json_body=body, idempotency_key=idempotency_key, base_url=base_url
        )

    async def paginate(
        self,
        path: str,
        *,
        limit: int = 20,
        max_items: int = 500,
        **params: Any,
    ) -> dict[str, Any]:
        """Follow the ``after`` cursor until ``max_items`` is reached.

        The API returns ``{object, data[], first_id, last_id, has_more}``.
        """
        collected: list[Any] = []
        cursor: str | None = params.pop("after", None)
        pages = 0

        while len(collected) < max_items:
            page_size = min(limit, max_items - len(collected))
            body = await self.get(path, limit=page_size, after=cursor, **params)
            pages += 1

            if not isinstance(body, dict):
                return {"data": body}

            data = body.get("data")
            if not isinstance(data, list):
                return body

            collected.extend(data)
            if not body.get("has_more") or not body.get("last_id"):
                return {
                    "object": "list",
                    "data": collected,
                    "has_more": False,
                    "pages_fetched": pages,
                }
            cursor = body["last_id"]

        return {
            "object": "list",
            "data": collected,
            "has_more": True,
            "pages_fetched": pages,
            "note": f"Stopped at {max_items} items. Raise max_items for more.",
        }

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text[:2000]

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("retry-after")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
