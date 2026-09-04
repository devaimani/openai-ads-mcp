"""Tests for micros conversion, response budgeting, geo lookup and retries."""

from __future__ import annotations

import json

import httpx
import pytest

from openai_ads_mcp import budget, geo, micros
from openai_ads_mcp.client import AdsClient, _endpoint_key
from openai_ads_mcp.config import Config, ConfigError, _validate_base_url
from openai_ads_mcp.errors import AdsAPIError

# --------------------------------------------------------------------- micros


def test_to_micros_basic():
    assert micros.to_micros(1.00) == 1_000_000
    assert micros.to_micros("0.06") == 60_000
    assert micros.to_micros(0) == 0


def test_to_micros_rejects_negative():
    with pytest.raises(micros.MicrosError):
        micros.to_micros(-1)


def test_budget_enforces_minimum():
    assert micros.budget_to_micros(1.00) == 1_000_000
    with pytest.raises(micros.MicrosError, match="too small"):
        micros.budget_to_micros(0.99)


def test_cpm_bid_explains_per_impression_semantics():
    """A 60.00 CPM is 0.06 per impression; the factor of 1000 is the trap."""
    value, note = micros.bid_to_micros(0.06, billing_event="impression")
    assert value == 60_000
    assert "CPM" in note


def test_ocpc_bid_is_cpa_and_requires_click_billing():
    value, note = micros.bid_to_micros(100.0, billing_event="click", bidding_type="conversions")
    assert value == 100_000_000
    assert "CPA" in note

    with pytest.raises(micros.MicrosError, match="billing_event must be 'click'"):
        micros.bid_to_micros(100.0, billing_event="impression", bidding_type="conversions")


def test_from_micros_roundtrip():
    assert str(micros.from_micros(1_000_000)) == "1.00"
    assert str(micros.from_micros(60_000)) == "0.06"


# --------------------------------------------------------------------- budget


def test_budget_passes_small_payload_through():
    text = budget.enforce({"data": [1, 2, 3]})
    assert json.loads(text) == {"data": [1, 2, 3]}


def test_budget_truncates_large_list_and_explains():
    payload = {"data": [{"id": f"row-{i}", "text": "x" * 200} for i in range(5000)]}
    text = budget.enforce(payload, budget=5_000)
    parsed = json.loads(text)

    assert len(text) <= 5_000
    assert len(parsed["data"]) < 5000
    assert "_response" in parsed
    assert "truncated" in parsed["_response"]


def test_compact_drops_none_and_heavy_fields():
    result = budget.compact({"keep": 1, "drop": None, "html": "<huge>"})
    assert result == {"keep": 1}


# ------------------------------------------------------------------------ geo


def test_umlaut_variants_generated():
    """Live finding: "Muenchen" returns nothing, "Munchen" with umlaut returns 78."""
    assert "München" in geo.query_variants("Muenchen")
    assert "Köln" in geo.query_variants("Koeln")
    assert "Düsseldorf" in geo.query_variants("Duesseldorf")
    assert "Nürnberg" in geo.query_variants("Nuernberg")


def test_ss_is_not_rewritten_to_eszett():
    """ "Duesseldorf" must not become an eszett spelling.

    An ss->eszett rule would misfire mid-word and destroy the very match the
    ue->umlaut rule just produced.
    """
    assert "Düßeldorf" not in geo.query_variants("Duesseldorf")


def test_english_names_mapped():
    """Live finding: "Munich" returns nothing with country_code DE."""
    assert "München" in geo.query_variants("Munich")
    assert "Köln" in geo.query_variants("Cologne")


def test_unsupported_types_flagged():
    assert geo.unsupported_hint("Enzkreis") is not None
    assert geo.unsupported_hint("Landkreis Karlsruhe") is not None
    assert geo.unsupported_hint("Karlsruhe") is None


def test_ambiguous_names_surfaced():
    """Birkenfeld exists three times, so selection must go by postcode."""
    summary = geo.summarize(
        [
            {
                "id": "1",
                "name": "Birkenfeld",
                "canonical_name": "55765, Birkenfeld, Germany",
                "type": "postal_code",
                "country_code": "DE",
            },
            {
                "id": "2",
                "name": "Birkenfeld",
                "canonical_name": "75217, Birkenfeld, Germany",
                "type": "postal_code",
                "country_code": "DE",
            },
        ]
    )
    assert "ambiguous" in summary
    assert summary["types"]["postal_code"] == 2


def test_country_filter_applied():
    summary = geo.summarize(
        [
            {"id": "1", "name": "Stuttgart", "type": "postal_code", "country_code": "DE"},
            {"id": "2", "name": "Stuttgart", "type": "postal_code", "country_code": "US"},
        ],
        country="DE",
    )
    assert summary["count"] == 1


def test_targeting_payload_shape():
    assert geo.to_targeting(["10015849", "2000346"]) == {
        "locations": {"include": [{"id": "10015849"}, {"id": "2000346"}]}
    }


# --------------------------------------------------------------------- config


def test_base_url_must_be_https():
    with pytest.raises(ConfigError):
        _validate_base_url("http://api.ads.openai.com/v1")


def test_base_url_rejects_credentials():
    with pytest.raises(ConfigError):
        _validate_base_url("https://user:pw@api.ads.openai.com/v1")


def test_endpoint_key_normalises_ids():
    assert _endpoint_key("/campaigns/camp_123/insights") == "/campaigns/{id}/insights"
    assert _endpoint_key("/ad_account") == "/ad_account"


# --------------------------------------------------------------------- client


def _config() -> Config:
    return Config(api_key="test-key", max_retries=4, timeout=5.0)


async def test_409_is_retried_and_then_succeeds():
    """Live finding: 409 occurs sporadically and clears on retry."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(
                409, json={"error": {"message": "Ad Account is missing details."}}
            )
        return httpx.Response(200, json={"count": 1, "results": [{"id": "10015849"}]})

    client = AdsClient(_config(), transport=httpx.MockTransport(handler))
    try:
        body = await client.get("/geo_lookup/search", q="Karlsruhe")
    finally:
        await client.aclose()

    assert calls["n"] == 3
    assert body["results"][0]["id"] == "10015849"


async def test_400_is_not_retried():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": {"message": "Missing parameter"}})

    client = AdsClient(_config(), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(AdsAPIError) as excinfo:
            await client.get("/campaigns")
    finally:
        await client.aclose()

    assert calls["n"] == 1
    assert not excinfo.value.is_hard


async def test_401_is_hard_error():
    client = AdsClient(
        _config(),
        transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "bad key"})),
    )
    try:
        with pytest.raises(AdsAPIError) as excinfo:
            await client.get("/ad_account")
    finally:
        await client.aclose()

    assert excinfo.value.is_hard


async def test_auto_pagination_follows_cursor():
    pages = [
        {"object": "list", "data": [{"id": "a"}], "last_id": "a", "has_more": True},
        {"object": "list", "data": [{"id": "b"}], "last_id": "b", "has_more": False},
    ]
    state = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page = pages[state["i"]]
        state["i"] += 1
        return httpx.Response(200, json=page)

    client = AdsClient(_config(), transport=httpx.MockTransport(handler))
    try:
        result = await client.paginate("/campaigns", limit=1, max_items=10)
    finally:
        await client.aclose()

    assert [row["id"] for row in result["data"]] == ["a", "b"]
    assert result["pages_fetched"] == 2


async def test_pagination_respects_max_items():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"object": "list", "data": [{"id": "x"}], "last_id": "x", "has_more": True},
        )

    client = AdsClient(_config(), transport=httpx.MockTransport(handler))
    try:
        result = await client.paginate("/campaigns", limit=1, max_items=3)
    finally:
        await client.aclose()

    assert len(result["data"]) == 3
    assert result["has_more"] is True
