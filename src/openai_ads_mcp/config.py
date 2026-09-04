"""Configuration from environment variables.

The API key is never logged and never included in error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

ADS_BASE_URL = "https://api.ads.openai.com/v1"
CONVERSIONS_BASE_URL = "https://bzr.openai.com/v1"

# The key may appear under several names. First match wins.
_KEY_NAMES = (
    "OPENAI_ADS_API_KEY",
    "OPENAI_ADS_KEY",
    "OpenAI-Ads-Key",
    "OPENAI-ADS-KEY",
)


class ConfigError(RuntimeError):
    """Misconfiguration the user has to fix."""


def _validate_base_url(url: str) -> str:
    """Harden an overridden base URL.

    Requires https, rejects embedded credentials, rejects query and fragment.
    Without this, a tampered environment variable could send the bearer token
    to a foreign host.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ConfigError(f"Base URL must use https, got: {parsed.scheme!r}")
    if not parsed.hostname:
        raise ConfigError("Base URL has no hostname")
    if parsed.username or parsed.password:
        raise ConfigError("Base URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ConfigError("Base URL must not contain a query or fragment")
    return url.rstrip("/")


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} is not a number: {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    api_key: str
    ads_base_url: str = ADS_BASE_URL
    conversions_base_url: str = CONVERSIONS_BASE_URL

    #: When true, no write tools are registered.
    readonly: bool = False

    #: Campaign budgets above this need explicit confirmation.
    budget_ceiling: float = 500.0

    #: Account currency. Read from /ad_account once the account profile is
    #: complete; until then taken from the environment.
    currency: str = "EUR"

    timeout: float = 60.0
    max_retries: int = 4

    @classmethod
    def from_env(cls) -> Config:
        key = ""
        for name in _KEY_NAMES:
            value = os.environ.get(name, "").strip()
            if value:
                key = value
                break
        if not key:
            raise ConfigError(
                "No API key found. Set OPENAI_ADS_API_KEY in the environment or in a .env file."
            )

        base = os.environ.get("OPENAI_ADS_API_BASE_URL", "").strip()
        return cls(
            api_key=key,
            ads_base_url=_validate_base_url(base) if base else ADS_BASE_URL,
            readonly=_env_flag("OPENAI_ADS_MCP_READONLY"),
            budget_ceiling=_env_float("OPENAI_ADS_BUDGET_CEILING", 500.0),
            currency=os.environ.get("OPENAI_ADS_CURRENCY", "EUR").strip() or "EUR",
            timeout=_env_float("OPENAI_ADS_TIMEOUT", 60.0),
            max_retries=int(_env_float("OPENAI_ADS_MAX_RETRIES", 4)),
        )
