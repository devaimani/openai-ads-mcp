---
name: ads
description: >
  Plan, build, review and optimise OpenAI Ads (ChatGPT Ads) campaigns —
  structure, context hints, ad copy against verified character limits,
  postcode-level geo targeting, bidding, conversion measurement and reporting.
  Use this skill whenever ChatGPT Ads, OpenAI Ads, advertising inside ChatGPT,
  running ads, creating a campaign, ad copy, context hints, ad budget, click
  price or ad performance come up — even when the word "skill" is not used.
  Covers both building new campaigns and analysing running ones.
user-invocable: true
argument-hint: "[audit|campaign|copy|hints|geo]"
license: MIT
metadata:
  version: "0.1.0"
  category: ads
---

# OpenAI Ads

The goal of everything here: **as many clicks and conversions per unit of spend
as possible**, and from those, leads that turn into business. Reach without
conversion is not success.

## Read first

- `references/platform-facts.md` — every hard limit and rule
- `references/misinformation.md` — **always read before quoting a figure or a
  feature.** A lot of false information about this platform is in circulation.
- `references/benchmarks.md` — sufficiency thresholds and your own measured values

Do not load all three at once. Copy work needs `platform-facts`; assessments
add `benchmarks`.

## The one rule that shapes everything

**There is no reporting per `context_hint`.** The API accepts up to 2000 hints
per ad group but never reports which of them produced a conversion.

That determines how every campaign is cut:

> The ad group is the smallest unit of measurement. So: **few hints per group,
> tightly scoped by theme, and more groups instead.**

A group with 200 hints is a black box — it may perform, but you never learn
why, and you cannot repeat it. Five groups with 10 to 20 hints each produce
usable signal.

Guideline: **10 to 25 hints per group.** Warn above 50.

## Routing

| Task | Use |
|---|---|
| New campaign | `ads-campaign` — clarify, decide, create |
| Ad copy | `ads-creative` — character economy, validation |
| Finding topics | `ads-hints` — clustering, negative keywords |
| Location targeting | `ads-geo` — postcode sets instead of a radius |
| Reviewing a running campaign | `ads-audit` |

## Build order

The sequence matters because each step depends on the previous one:

1. **`get_account`** — currency, timezone, `review.status`. If `rejected` with
   `missing_favicon`, fix the account first.
2. **`check_feature_access`** — what is enabled? This API answers 403, and
   sometimes 404, when something is gated.
3. **Conversion measurement** before the first campaign. Without it you cannot
   switch to conversion bidding later — `bidding_type` is immutable.
4. **Check the landing page** — reachable for crawlers, no redirect, favicon
   present.
5. **Create the campaign paused**, then the ad group, then the image, then the ad.
6. **`preview_ad`** and look at it.
7. Only then activate, one thing at a time.

## Structure

- **One campaign per goal and bidding type.** `bidding_type` cannot be changed,
  so anyone planning to move to conversion optimisation later will need a new
  campaign anyway.
- **One ad group per intent.** Not per product, not per audience. Intent
  determines which phrasing lands.
- **Two or three ads per group**, using different angles rather than reworded
  versions of the same claim. Only then is the comparison meaningful.

## Assessing

Run the sufficiency check from `references/benchmarks.md` before quoting any
number. If the data is too thin, output **no score** — state what is missing
and how long to keep measuring.

Assess against the **maximum tolerable CPA** derived from the business model,
not against industry figures. There are none for this platform.

## Every recommendation needs four things

Without these it is a finding, not a recommendation:

1. **Observation** — what it rests on, with a number
2. **Dependency** — what has to happen first
3. **Falsification** — how would you know it did not work?
4. **Leading indicator** — what moves first, without re-running the analysis

Point 3 matters most. Anyone who cannot say how they would notice being wrong
is recommending on a hunch, and here that spends real budget.

## When things go wrong

| Situation | Response |
|---|---|
| 403 on an endpoint | Feature not enabled. Say so, do not work around it. |
| 404 on a resource that exists | Usually the same cause. |
| 409 "missing details" | Account profile incomplete — **or** sporadic. A retry tells you which. |
| Ad `rejected` | Read `review.reason_code`. A `crawler_*` code points at the landing page, not the copy. |
| No conversion data | Do not read as poor performance. Check measurement first, then data volume. |
| Someone wants to use search-ad CPCs as bids | Explain it is a different auction. Start small and measure. |
| Someone quotes 35/67 characters | Correct it: 50 and 100 per the spec. |

## What this platform cannot do

Do not look for, suggest or claim: keyword bidding, match types, keyword
planner, search volume, radius targeting, personalised ads in the EEA, a
sandbox, official benchmarks, a Python SDK.

Details and reasoning in `references/misinformation.md`.
