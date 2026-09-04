"""Error classes and retry policy.

The classification below comes from probing a live account on 2026-09-04,
not from the documentation:

  409 "Ad Account is missing details." occurred on 8 of 32 calls with no
  relation to the query — q=Berlin failed while Berlin appeared in the
  results of q=Germany. With backoff, all 32 returned HTTP 200.

That is why 409 is retryable here. Other public MCP servers for this API
have no retry logic at all and surface these as hard failures.
"""

from __future__ import annotations

from typing import Any

#: Status codes worth retrying.
RETRYABLE_STATUSES = frozenset({0, 409, 429, 500, 502, 503, 504})

#: Status codes that surface as MCP protocol errors. Everything else is
#: returned as a JSON payload so the model can correct itself.
HARD_STATUSES = frozenset({0, 401})

_FRIENDLY: dict[int, str] = {
    400: "Invalid request. A required field is missing or a value is not allowed.",
    401: "API key invalid or expired. Check OPENAI_ADS_API_KEY.",
    403: (
        "Access denied. On this API that usually means the feature is not "
        "enabled for the account. Enabling it goes through an OpenAI partner "
        "contact."
    ),
    404: (
        "Not found. Note that this API also returns 404 when a feature is not "
        "enabled for the account, not only when a resource is missing."
    ),
    409: (
        "Conflict. Most common case: 'Ad Account is missing details' — the "
        "account profile is incomplete in the Ads Manager. This status also "
        "occurs sporadically and clears on retry."
    ),
    429: "Rate limited (600/min per endpoint, 1200/min overall).",
}


class AdsAPIError(Exception):
    """An API or transport error.

    ``status`` 0 means a network, DNS, TLS or timeout failure.
    """

    def __init__(
        self,
        status: int,
        message: str,
        *,
        body: Any = None,
        request_id: str | None = None,
        path: str | None = None,
        attempts: int = 1,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.body = body
        self.request_id = request_id
        self.path = path
        self.attempts = attempts

    @property
    def is_hard(self) -> bool:
        """Should this surface as an MCP protocol error?"""
        return self.status in HARD_STATUSES or self.status >= 500

    @property
    def is_retryable(self) -> bool:
        return self.status in RETRYABLE_STATUSES

    def explain(self) -> str:
        """Message plus context for the user."""
        hint = _FRIENDLY.get(self.status)
        parts = [f"HTTP {self.status}: {self.message}" if self.status else self.message]
        if hint:
            parts.append(hint)
        if self.request_id:
            parts.append(f"request-id: {self.request_id}")
        return " — ".join(parts)

    def to_payload(self) -> dict[str, Any]:
        """Soft error representation for a tool response."""
        payload: dict[str, Any] = {
            "error": True,
            "status": self.status,
            "message": self.message,
            "hint": _FRIENDLY.get(self.status),
        }
        if self.path:
            payload["path"] = self.path
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.attempts > 1:
            payload["attempts"] = self.attempts
        return payload


def extract_message(body: Any, fallback: str) -> str:
    """Pull the error message out of an API response body.

    Observed shape: {"error": {"message", "type", "param", "code"}}
    """
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            for key in ("message", "detail", "code"):
                value = error.get(key)
                if isinstance(value, str) and value:
                    return value
        if isinstance(error, str) and error:
            return error
        for key in ("message", "detail"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    if isinstance(body, str) and body.strip():
        return body.strip()[:300]
    return fallback
