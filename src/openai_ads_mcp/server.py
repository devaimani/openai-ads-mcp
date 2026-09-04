"""MCP server for the OpenAI Ads Advertiser API.

Safety model:

* Every create tool forces ``status="paused"`` at the type level. Activation
  only happens through the dedicated ``set_*_state`` tools, so a campaign
  cannot start spending by accident.
* Budgets above the configured ceiling require ``confirm_budget=True``.
* ``archive`` is irreversible and requires ``confirm_archive=True``.
* ``OPENAI_ADS_MCP_READONLY=1`` registers no write tools at all.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import budget as budget_mod
from . import geo as geo_mod
from .client import AdsClient
from .config import Config
from .errors import AdsAPIError
from .micros import bid_to_micros, budget_to_micros, from_micros

MICROS_NOTE = (
    "Fields ending in '_micros' are millionths of the account currency "
    "(1,000,000 = 1.00). Insights fields spend/cpc/cpm are decimal amounts, "
    "not micros."
)

_config = Config.from_env()
_client = AdsClient(_config)

mcp = FastMCP(
    "openai-ads",
    instructions=(
        "Access to the OpenAI Ads Advertiser API (ChatGPT Ads).\n\n"
        "Call 'get_account' before making any change — it reports currency, "
        "timezone and review status.\n\n"
        "Platform specifics worth knowing:\n"
        "- There is NO keyword targeting and there are no match types. "
        "Delivery is steered through 'context_hints' (free text) plus geo.\n"
        "- Geo supports country, region and postal_code. There is no dma for "
        "Germany. Radius targeting does not exist — model a catchment area as "
        "a list of postcodes.\n"
        "- There is no reporting dimension per context hint. The ad group is "
        "the smallest unit of measurement, so keep hints few and thematically "
        "tight per group.\n"
        "- Updates are POST, not PATCH. Nested objects must be sent in full; "
        "partial objects overwrite the rest.\n"
        f"- {MICROS_NOTE}"
    ),
)


def _ok(payload: Any) -> str:
    return budget_mod.enforce(payload)


def _fail(exc: AdsAPIError) -> str:
    """Soft errors as JSON so the model can correct itself."""
    if exc.is_hard:
        raise exc
    return json.dumps(exc.to_payload(), ensure_ascii=False, indent=2)


def _error(message: str) -> str:
    return json.dumps({"error": True, "message": message}, ensure_ascii=False)


# --------------------------------------------------------------------------
# Account
# --------------------------------------------------------------------------


@mcp.tool()
async def get_account() -> str:
    """Fetch the ad account: currency, timezone, status, negative keywords.

    The first call to make after connecting; it also verifies the API key.
    A 409 "Ad Account is missing details" means the account profile is
    incomplete in the Ads Manager.
    """
    try:
        return _ok(await _client.get("/ad_account"))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def list_accounts() -> str:
    """List every account this API key can reach."""
    try:
        return _ok(await _client.get("/ad_accounts"))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def check_feature_access() -> str:
    """Report which features are enabled for this account.

    Useful because this API answers 403, and sometimes 404, when a feature is
    not enabled — not only when a resource is missing.
    """
    checks = {
        "ad_account": "/ad_account",
        "campaigns": "/campaigns",
        "conversions_pixels": "/conversions/pixels",
        "custom_audiences": "/custom_audiences",
        "product_feeds": "/feeds",
        "business_agents": "/business_agents",
        "lead_forms": "/lead_forms",
    }
    report: dict[str, Any] = {}
    for name, path in checks.items():
        try:
            await _client.get(path, limit=1)
            report[name] = {"available": True}
        except AdsAPIError as exc:
            report[name] = {
                "available": False,
                "status": exc.status,
                "message": exc.message,
                "meaning": (
                    "feature not enabled for this account"
                    if exc.status in (403, 404)
                    else exc.explain()
                ),
            }
    return _ok(report)


# --------------------------------------------------------------------------
# Geo
# --------------------------------------------------------------------------


@mcp.tool()
async def search_geo(
    query: Annotated[str, Field(description="Place, region, country or postcode")],
    limit: Annotated[int, Field(ge=1, le=100)] = 50,
    country: Annotated[str | None, Field(description="ISO country code filter, e.g. 'DE'")] = None,
) -> str:
    """Look up location IDs for targeting.

    Handles three quirks of the German dataset automatically:

    - Place names without umlauts return nothing. "Muenchen" is rewritten to
      "München", "Koeln" to "Köln", and both spellings are tried.
    - English exonyms return no German results. "Munich" becomes "München".
    - Districts and sub-municipal localities do not exist as a location type;
      the response says so instead of returning an empty list silently.

    Types available for Germany: country, region (16 federal states) and
    postal_code. No dma, no radius.
    """
    hint = geo_mod.unsupported_hint(query)
    tried: list[str] = []

    try:
        for variant in geo_mod.query_variants(query):
            tried.append(variant)
            body = await _client.get("/geo_lookup/search", q=variant, limit=limit)
            results = body.get("results", []) if isinstance(body, dict) else []
            if country:
                results = [r for r in results if r.get("country_code") == country.upper()]
            if results:
                summary = geo_mod.summarize(results)
                summary["query"] = variant
                if variant != query:
                    summary["spelling_note"] = (
                        f"'{query}' returned nothing, '{variant}' did. Umlauts are "
                        "required in this dataset."
                    )
                if hint:
                    summary["hint"] = hint
                return _ok(summary)

        return _ok(
            {
                "count": 0,
                "results": [],
                "spellings_tried": tried,
                "hint": hint
                or (
                    "No results. Districts and sub-municipal localities are not a "
                    "location type — search for the town's postcode instead."
                ),
            }
        )
    except AdsAPIError as exc:
        return _fail(exc)


# --------------------------------------------------------------------------
# Campaigns
# --------------------------------------------------------------------------


@mcp.tool()
async def list_campaigns(
    limit: Annotated[int, Field(ge=1, le=500)] = 20,
    fetch_all: Annotated[bool, Field(description="Follow all pages")] = False,
    max_items: Annotated[int, Field(ge=1, le=2000)] = 500,
    order: Literal["asc", "desc"] = "desc",
) -> str:
    """List campaigns. With fetch_all the cursor is followed automatically."""
    try:
        if fetch_all:
            return _ok(
                await _client.paginate("/campaigns", limit=limit, max_items=max_items, order=order)
            )
        return _ok(await _client.get("/campaigns", limit=limit, order=order))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def get_campaign(campaign_id: str) -> str:
    """Fetch a single campaign."""
    try:
        return _ok(await _client.get(f"/campaigns/{campaign_id}"))
    except AdsAPIError as exc:
        return _fail(exc)


# --------------------------------------------------------------------------
# Ad groups and ads
# --------------------------------------------------------------------------


@mcp.tool()
async def list_ad_groups(
    campaign_id: str,
    limit: Annotated[int, Field(ge=1, le=500)] = 20,
    fetch_all: bool = False,
) -> str:
    """List the ad groups of a campaign."""
    try:
        if fetch_all:
            return _ok(await _client.paginate("/ad_groups", limit=limit, campaign_id=campaign_id))
        return _ok(await _client.get("/ad_groups", campaign_id=campaign_id, limit=limit))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def get_ad_group(ad_group_id: str) -> str:
    """Fetch a single ad group, including its context hints and bid."""
    try:
        return _ok(await _client.get(f"/ad_groups/{ad_group_id}"))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def list_ads(
    ad_group_id: str,
    limit: Annotated[int, Field(ge=1, le=500)] = 20,
    fetch_all: bool = False,
) -> str:
    """List the ads of an ad group, including review status."""
    try:
        if fetch_all:
            return _ok(await _client.paginate("/ads", limit=limit, ad_group_id=ad_group_id))
        return _ok(await _client.get("/ads", ad_group_id=ad_group_id, limit=limit))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def get_ad(ad_id: str) -> str:
    """Fetch a single ad.

    When review_status is 'rejected', the cause is in review.reason_code —
    for example crawl_failed, crawler_403, robots_txt or missing_favicon.
    """
    try:
        return _ok(await _client.get(f"/ads/{ad_id}"))
    except AdsAPIError as exc:
        return _fail(exc)


# --------------------------------------------------------------------------
# Insights
# --------------------------------------------------------------------------


@mcp.tool()
async def get_insights(
    scope: Literal["account", "campaign", "ad_group", "ad"] = "account",
    entity_id: Annotated[str | None, Field(description="Required unless scope='account'")] = None,
    time_granularity: Literal["hourly", "daily", "monthly", "none"] = "daily",
    since: Annotated[str | None, Field(description="Start date, YYYY-MM-DD")] = None,
    until: Annotated[str | None, Field(description="End date, YYYY-MM-DD")] = None,
    aggregation_level: Literal["ad_account", "campaign", "ad_group", "ad"] | None = None,
    segment: Annotated[
        Literal["product", "country", "device"] | None,
        Field(description="Exactly one segment; the API allows no more"),
    ] = None,
    fields: list[str] | None = None,
    limit: Annotated[int, Field(ge=1, le=2000)] = 50,
) -> str:
    """Fetch performance data.

    Metrics: impressions, clicks, spend, ctr, cpc, cpm, conversions, cpa,
    post_click_cvr, order_created_roas.

    For ROAS use order_created_roas only — the roas and attributed_sales_*
    fields are deprecated and scheduled for removal.

    Time window: at most 5 years back, never in the future.
    """
    paths = {
        "account": "/ad_account/insights",
        "campaign": f"/campaigns/{entity_id}/insights",
        "ad_group": f"/ad_groups/{entity_id}/insights",
        "ad": f"/ads/{entity_id}/insights",
    }
    if scope != "account" and not entity_id:
        return _error(f"entity_id is required when scope='{scope}'.")

    params: dict[str, Any] = {"time_granularity": time_granularity, "limit": limit}
    if aggregation_level:
        params["aggregation_level"] = aggregation_level
    if since and until:
        params["time_ranges[]"] = json.dumps({"type": "date_range", "since": since, "until": until})
    if segment:
        if time_granularity == "hourly":
            return _error("Segments cannot be combined with time_granularity='hourly'.")
        params["segments[]"] = segment
    if fields:
        params["fields[]"] = fields

    try:
        return _ok(await _client.get(paths[scope], **params))
    except AdsAPIError as exc:
        return _fail(exc)


# --------------------------------------------------------------------------
# Audiences and conversions
# --------------------------------------------------------------------------


@mcp.tool()
async def list_audiences(limit: Annotated[int, Field(ge=1, le=500)] = 20) -> str:
    """List custom audiences.

    Personalised ads are not available for campaigns targeting the EEA or
    Switzerland, so audiences cannot be used to steer delivery there.
    """
    try:
        return _ok(await _client.get("/custom_audiences", limit=limit))
    except AdsAPIError as exc:
        return _fail(exc)


@mcp.tool()
async def list_conversion_setup() -> str:
    """Show the account's pixels and conversion event settings.

    Prerequisite for bidding_type='conversions' (oCPC): exactly one active
    standard event setting and an active conversion source.
    """
    result: dict[str, Any] = {}
    for key, path in (
        ("pixels", "/conversions/pixels"),
        ("event_settings", "/conversions/event_settings"),
    ):
        try:
            result[key] = await _client.get(path)
        except AdsAPIError as exc:
            result[key] = exc.to_payload()
    return _ok(result)


@mcp.tool()
async def explain_micros(
    amount: Annotated[float, Field(description="Amount in the account currency")],
    context: Literal["budget", "cpc_bid", "cpm_bid", "cpa_bid"] = "cpc_bid",
) -> str:
    """Convert an amount to micros and explain what the value means.

    The two costly traps on this API:
    - CPM: max_bid_micros is the price per single impression, not per 1000.
    - oCPC: max_bid_micros is a CPA bid, yet billing happens per click.
    """
    try:
        if context == "budget":
            micros = budget_to_micros(amount)
            note = f"Lifetime budget of {amount} {_config.currency}. Minimum is 1.00."
        elif context == "cpm_bid":
            micros, note = bid_to_micros(amount, billing_event="impression")
        elif context == "cpa_bid":
            micros, note = bid_to_micros(amount, billing_event="click", bidding_type="conversions")
        else:
            micros, note = bid_to_micros(amount, billing_event="click")
    except ValueError as exc:
        return _error(str(exc))

    return _ok(
        {
            "input": amount,
            "micros": micros,
            "converted_back": str(from_micros(micros)),
            "currency": _config.currency,
            "meaning": note,
        }
    )


def _register_write_tools() -> None:
    """Register write tools unless running in read-only mode."""

    @mcp.tool()
    async def create_campaign(
        name: Annotated[str, Field(min_length=3, max_length=1000)],
        budget: Annotated[float, Field(gt=0, description="Lifetime budget in account currency")],
        bidding_type: Annotated[
            Literal["impressions", "clicks", "conversions"],
            Field(description="Cannot be changed after creation"),
        ] = "clicks",
        location_ids: Annotated[
            list[str] | None, Field(description="Location IDs from search_geo")
        ] = None,
        daily_budget: Annotated[float | None, Field(gt=0)] = None,
        conversion_event_setting_ids: list[str] | None = None,
        confirm_budget: bool = False,
        idempotency_key: str | None = None,
    ) -> str:
        """Create a campaign — always paused.

        The campaign spends nothing until set_campaign_state activates it.

        bidding_type is immutable after creation. With 'conversions' (oCPC) the
        target event is immutable too, and child ad groups must use
        billing_event='click'.
        """
        if budget > _config.budget_ceiling and not confirm_budget:
            return _error(
                f"Budget {budget} {_config.currency} exceeds the ceiling of "
                f"{_config.budget_ceiling}. Pass confirm_budget=True to proceed."
            )

        body: dict[str, Any] = {
            "name": name,
            "status": "paused",
            "bidding_type": bidding_type,
            "budget": {"lifetime_spend_limit_micros": budget_to_micros(budget)},
        }
        if daily_budget:
            body["budget"]["daily_spend_limit_micros"] = budget_to_micros(daily_budget)
        if location_ids:
            body["targeting"] = geo_mod.to_targeting(location_ids)
        if conversion_event_setting_ids:
            body["conversion_event_setting_ids"] = conversion_event_setting_ids

        try:
            created = await _client.post("/campaigns", body, idempotency_key=idempotency_key)
            return _ok(
                {
                    "campaign": created,
                    "status": "Created paused. Activate with set_campaign_state.",
                }
            )
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def create_ad_group(
        campaign_id: str,
        name: Annotated[str, Field(min_length=3, max_length=1000)],
        max_bid: Annotated[float, Field(gt=0)],
        billing_event: Literal["impression", "click"] = "click",
        context_hints: Annotated[
            list[str] | None,
            Field(description="Topics where the ad fits. Keep them few and tightly scoped."),
        ] = None,
        bidding_type: Annotated[
            str | None, Field(description="The campaign's bidding_type, for bid validation")
        ] = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Create an ad group — always paused.

        On context_hints: the API accepts up to 2000, but there is no reporting
        dimension per hint. Putting 2000 hints in one group means never learning
        which of them produced conversions. Prefer few hints per group and
        several thematically separate groups.
        """
        if context_hints and len(context_hints) > 2000:
            return _error(f"At most 2000 context hints, received {len(context_hints)}.")

        try:
            micros, note = bid_to_micros(
                max_bid, billing_event=billing_event, bidding_type=bidding_type
            )
        except ValueError as exc:
            return _error(str(exc))

        body: dict[str, Any] = {
            "campaign_id": campaign_id,
            "name": name,
            "status": "paused",
            "bidding_config": {"billing_event_type": billing_event, "max_bid_micros": micros},
        }
        if context_hints:
            body["context_hints"] = context_hints

        try:
            created = await _client.post("/ad_groups", body, idempotency_key=idempotency_key)
            result: dict[str, Any] = {
                "ad_group": created,
                "bid": note,
                "status": "Created paused. Activate with set_ad_group_state.",
            }
            if context_hints and len(context_hints) > 50:
                result["warning"] = (
                    f"{len(context_hints)} context hints in one group. There is no "
                    "per-hint reporting, so at this size it is no longer possible to "
                    "tell which topics work."
                )
            return _ok(result)
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def create_ad(
        ad_group_id: str,
        name: Annotated[str, Field(min_length=3, max_length=1000)],
        title: Annotated[
            str, Field(min_length=3, max_length=50, description="Headline, 3-50 chars")
        ],
        body_text: Annotated[str, Field(max_length=100, description="Description, max 100 chars")],
        target_url: Annotated[str, Field(max_length=2048)],
        file_id: Annotated[str, Field(description="Image ID from upload_creative")],
        idempotency_key: str | None = None,
    ) -> str:
        """Create an ad — always paused.

        Character limits per OpenAPI spec v2.3.0: title 3-50, body at most 100.
        The figures 35 and 67 that circulate elsewhere are unsourced and
        contradict the spec.

        Keep the brand name out of the title: the logo is shown anyway and the
        characters are better spent on substance.
        """
        body: dict[str, Any] = {
            "ad_group_id": ad_group_id,
            "name": name,
            "status": "paused",
            "creative": {
                "type": "chat_card",
                "title": title,
                "body": body_text,
                "target_url": target_url,
                "file_id": file_id,
            },
        }
        try:
            created = await _client.post("/ads", body, idempotency_key=idempotency_key)
            return _ok(
                {
                    "ad": created,
                    "status": "Created paused and submitted for review.",
                    "next_step": "Check with preview_ad, then activate with set_ad_state.",
                }
            )
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def upload_creative(
        image_url: Annotated[str | None, Field(description="Publicly reachable image URL")] = None,
        purpose: Annotated[
            Literal["account_favicon"] | None,
            Field(description="Set to account_favicon for the account brand icon"),
        ] = None,
    ) -> str:
        """Upload an image and return the file_id for create_ad.

        For an account favicon pass purpose='account_favicon'; the image must
        be at least 128x128 pixels.
        """
        if not image_url:
            return _error("image_url is required.")
        payload: dict[str, Any] = {"image_url": image_url}
        if purpose:
            payload["purpose"] = purpose
        try:
            return _ok(await _client.post("/upload", payload))
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def set_account_brand(favicon_file_id: str) -> str:
        """Assign a favicon to the account and start the brand review.

        Required when get_account reports review.reason 'missing_favicon'.
        Upload the image first with upload_creative(purpose='account_favicon').
        """
        try:
            return _ok(
                await _client.post("/ad_account/brand", {"favicon_file_id": favicon_file_id})
            )
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def preview_ad(ad_id: str) -> str:
        """Generate a preview. The link is valid for 24 hours."""
        try:
            return _ok(await _client.post(f"/ads/{ad_id}/preview"))
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def set_campaign_state(
        campaign_id: str,
        state: Literal["activate", "pause", "archive"],
        confirm_archive: bool = False,
    ) -> str:
        """Activate, pause or archive a campaign.

        'activate' starts delivery and therefore spending.
        'archive' is irreversible — there is no way back.
        """
        if state == "archive" and not confirm_archive:
            return _error("Archiving cannot be undone. Pass confirm_archive=True to proceed.")
        try:
            return _ok(await _client.post(f"/campaigns/{campaign_id}/{state}"))
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def set_ad_group_state(
        ad_group_id: str,
        state: Literal["activate", "pause", "archive"],
        confirm_archive: bool = False,
    ) -> str:
        """Activate, pause or archive an ad group. Archiving is permanent."""
        if state == "archive" and not confirm_archive:
            return _error("Archiving is permanent. Pass confirm_archive=True to proceed.")
        try:
            return _ok(await _client.post(f"/ad_groups/{ad_group_id}/{state}"))
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def set_ad_state(
        ad_id: str,
        state: Literal["activate", "pause", "archive"],
        confirm_archive: bool = False,
    ) -> str:
        """Activate, pause or archive an ad. Archiving is permanent."""
        if state == "archive" and not confirm_archive:
            return _error("Archiving is permanent. Pass confirm_archive=True to proceed.")
        try:
            return _ok(await _client.post(f"/ads/{ad_id}/{state}"))
        except AdsAPIError as exc:
            return _fail(exc)

    @mcp.tool()
    async def set_negative_keywords(
        keywords: Annotated[list[str], Field(max_length=100)],
    ) -> str:
        """Set the account-wide negative keywords.

        Replaces the existing list entirely. At most 100 entries of 1-100
        characters each, so pick terms that are broadly effective. There is no
        per-campaign or per-ad-group scoping.
        """
        if len(keywords) > 100:
            return _error(f"At most 100 negative keywords, received {len(keywords)}.")
        too_long = [k for k in keywords if not 1 <= len(k) <= 100]
        if too_long:
            return _error(f"These entries violate the 1-100 character limit: {too_long[:5]}")
        try:
            return _ok(
                await _client.post("/ad_account/negative_keywords", {"negative_keywords": keywords})
            )
        except AdsAPIError as exc:
            return _fail(exc)


if not _config.readonly:
    _register_write_tools()
