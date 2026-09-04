<!-- Verified: 2026-09-04 against OpenAPI spec v2.3.0 and a live account -->
# OpenAI Ads platform facts

Every figure here comes either from OpenAPI spec v2.3.0 or from a live call on
2026-09-04. Nothing unsourced is included.

## Hard limits

| Field | Limit | Source |
|---|---|---|
| `creative.title` | **3–50 characters** | spec |
| `creative.body` | **max 100 characters** | spec |
| `creative.target_url` | max 2048 | spec |
| `name` (internal, not shown) | 3–1000 | spec |
| `context_hints[]` | max 2000 per ad group | spec |
| Negative keywords | max 100 **account-wide**, 1–100 chars each | spec |
| Budget (lifetime) | min 1,000,000 micros = 1.00 | spec |
| `max_bid_micros` | 1 to 30,400,000,000,000 | spec |
| Insights `limit` | 1–2000 (default 20) | spec |
| List `limit` | 1–500 (default 20) | spec |
| Insights time window | max 5 years back, never future | docs |
| Favicon | at least 128×128 | docs |
| Ad preview | valid 24 hours | docs |
| Rate limit | 600/min per endpoint, 1200/min overall | docs |

## Ad formats

Exactly two creative types:

- **`chat_card`** — the standard ad. Requires both `file_id` and `target_url`.
- **`product_ad_template`** — for product feed campaigns. Image and target URL
  come from the feed item. At most one non-archived per ad group.

Terms like "sponsored results", "inline ads" or "shopping ads" do not appear in
the documentation.

## Bidding

| `bidding_type` | Billing | Ad group `billing_event_type` |
|---|---|---|
| `impressions` (default) | per 1000 impressions | `impression` |
| `clicks` | per valid click | `click` |
| `conversions` (oCPC) | **per valid click** | `click` (mandatory) |

**`bidding_type` is immutable after creation.** With oCPC that also applies to
`conversion_event_setting_ids`. Switching requires a new campaign.

## Two arithmetic traps

**CPM:** `max_bid_micros` is the price per *single* impression, not per mille.
A 60.00 CPM is `60000` micros, not `60000000`. Factor of 1000.

**oCPC:** `max_bid_micros` is a *CPA* bid even though billing is per click.
From the docs: "The bid is a CPA input even though OpenAI bills the child ad
group per click."

Only fields with the `_micros` suffix are micros. The insights fields `spend`,
`cpc` and `cpm` are decimal amounts.

## Prerequisites for oCPC

1. Account enabled (otherwise `403 "Conversion bidding is not enabled"`)
2. Exactly **one** active **standard** event setting — custom events are not
   valid targets
3. An active conversion source

Valid optimisation targets for lead generation: `lead_created`,
`appointment_scheduled`, `registration_completed`, `trial_started`.

## Conversion events (13 standard types)

`app_installed`, `app_opened` (both only via the Conversions API with
`action_source: mobile_app`), `appointment_scheduled`, `checkout_started`,
`contents_viewed`, `custom`, `items_added`, `lead_created`, `order_created`,
`page_viewed`, `registration_completed`, `subscription_created`,
`trial_started`.

Monetary values as integers in ISO 4217 minor units: `12999` = 129.99.

## Review

`review_status`: `in_review` | `approved` | `rejected`

Rejection reasons (`review.reason_code`): `crawl_failed`, `crawler_400`,
`crawler_401`, `crawler_403`, `crawler_404`, `crawler_408`, `crawler_410`,
`crawler_429`, `crawler_500`, `crawler_502`, `crawler_503`, `crawler_504`,
`robots_txt`, `unsupported_content_type`,
`landing_page_image_processing_failed`, `missing_favicon`.

Delivery requires campaign **and** ad group **and** ad to be active.

## Status codes

| Code | Meaning on this API |
|---|---|
| 400 | required field missing, empty list, unknown field |
| 401 | invalid key |
| **403** | **usually: feature not enabled for this account** |
| **404** | resource missing **or** feature not enabled |
| **409** | account profile incomplete — **also occurs sporadically**, clears on retry |
| 429 | rate limit |
| 503 | on custom audiences: retry, not a failure |

## Mutation semantics

- Updates are **POST**, not PATCH or PUT.
- Nested objects (`budget`, `bidding_config`, `creative`, `product_set`) must
  be sent **in full**. Partial objects overwrite the rest.
- There is **no DELETE**. Deleting means `archive`, which is **irreversible**.
- Build order: check account → favicon/brand review → (conversions) → campaign
  `paused` → ad group → upload → ad → verify → activate.
