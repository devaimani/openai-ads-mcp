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

## Creating conversion setup

<!-- Verified: 2026-09-14 against the live API -->

Both create routes exist and take POST, so a pixel does not have to be made in
the dashboard:

| Route | Required fields |
|---|---|
| `/conversions/pixels` | `name`, `client_type` (only `web` is accepted) |
| `/conversions/event_settings` | `name`, `event_type`, `attribution_window_days`, `source_ids` |

**`attribution_window_days` must be 7, 14 or 30.** Anything else is refused
with 422. The allowed set appears in no documentation page; the API states it
in the error.

`source_ids` takes the source's `id` (`cds_…`), **not** its `pixel_id`. The
`pixel_id` is the public value for the browser snippet.

`/conversions/sources` does not exist.

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

## crawl_failed can mean stale asset references

<!-- Verified: 2026-09-14 against a live account -->

`crawl_failed` reads like the landing page was unreachable. It can also mean
the page loaded fine and its JavaScript did not.

Measured on 2026-09-14: one of six ads on the same `target_url` was rejected
with `crawl_failed`. The nginx log showed 12 review crawls, **all HTTP 200
with the full 30 KB of HTML**, and in the same second a wave of 404s on
`/assets/*.js` — files the deployed HTML referenced but that the deploy had
replaced with new hashes. A single-page app that cannot load its bundle
renders nothing, so the crawler saw an empty page.

Two things follow:

- **A 200 on the URL does not clear this.** Check every asset the page
  references, not just the page.
- **The rejection is per ad, not per URL.** Five ads on the same URL passed.
  Whether a crawl lands during the window of stale references is timing.

The `review.screenshot_url` on a rejected ad shows what the crawler saw. A
mostly white image with few distinct colours means the render failed; a normal
colour distribution points elsewhere.

To retry: re-POST the **full** creative object unchanged. Per the
troubleshooting page, "editing ad creative creates a new submitted version and
triggers another creative review". Changing status does not re-review.

## No forecasting, no keyword planning

<!-- Verified: 2026-09-14 against the live API -->

There is no endpoint that predicts volume, reach, cost or conversions before
anything is spent. 28 candidate paths were probed live on 2026-09-14 and every
one answered `Invalid URL`:

`/forecast` `/forecasts` `/reach_estimate` `/delivery_estimate`
`/traffic_estimate` `/keyword_ideas` `/keyword_plan` `/keyword_planner`
`/keywords` `/context_hints` `/context_hint_suggestions` `/context_hint_ideas`
`/suggestions` `/planner` `/audience_size` `/audience_estimate`
`/bid_estimate` `/bid_suggestions` `/benchmarks` `/search_terms`
`/search_term_insights` `/trends` `/topics`, plus the same names under
`/ad_account/`.

The control URL `/ad_account/insights` returned 200 in the same run, so the
probe itself was sound.

There are no search term reports either: you never learn which phrasing
produced an impression. The ad group stays the smallest unit of measurement,
which is why group layout is the whole measurement design.

**When probing this API, go through an HTTP client that sets a normal
User-Agent.** A raw `urllib` request is answered by Cloudflare with 403 before
it reaches the API, including for endpoints that demonstrably work. That makes
every path look absent.

## Mutation semantics

- Updates are **POST**, not PATCH or PUT.
- Nested objects (`budget`, `bidding_config`, `creative`, `product_set`) must
  be sent **in full**. Partial objects overwrite the rest.
- There is **no DELETE**. Deleting means `archive`, which is **irreversible**.
- Build order: check account → favicon/brand review → (conversions) → campaign
  `paused` → ad group → upload → ad → verify → activate.
