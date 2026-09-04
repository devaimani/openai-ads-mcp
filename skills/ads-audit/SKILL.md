---
name: ads-audit
description: >
  Analyse running OpenAI Ads campaigns and derive actions — check metrics,
  assess whether the data supports a judgement, detect regressions. Use this
  skill for reporting, analysis, performance, how is the campaign doing,
  optimisation, cost review, or whenever figures from the ad account need
  interpreting.
user-invocable: true
license: MIT
metadata:
  version: "0.1.0"
  category: ads
---

# Reviewing campaigns

## First: is there enough data?

Check before any assessment. From `ads/references/benchmarks.md`:

| Metric | Minimum |
|---|---|
| CTR | 1,000 impressions |
| CPC | 100 clicks |
| Conversion rate | 100 clicks and 10 conversions |
| CPA | 30 conversions |
| Trend | 14 days |
| Comparison of two groups | 100 clicks each |

If fewer than four of seven are supported, **output no overall figure**. Say
this instead:

```
Overall assessment: NOT POSSIBLE (2/7 metrics supported)
Supported:     impressions (3,400), clicks (47)
Not supported: CTR, CPC, CVR, CPA, ROAS
Reason:        47 clicks is below the threshold of 100.
Recommendation: keep running for another 10 days.
```

This is the most important part of this skill. A number built on thin data
looks like poor performance when data is merely missing — and that is how
working campaigns get switched off.

## Fetching data

```
get_insights(scope="account", time_granularity="daily", since=..., until=...)
get_insights(scope="campaign", entity_id=..., time_granularity="daily")
get_insights(scope="ad_group", entity_id=..., time_granularity="none")
```

For breakdowns: `segment="device"` or `segment="country"`. Exactly one — the
API allows no more, and none in combination with `hourly`.

Available metrics: `impressions`, `clicks`, `spend`, `ctr`, `cpc`, `cpm`,
`conversions`, `cpa`, `post_click_cvr`, `order_created_roas`.

For ROAS use **only** `order_created_roas` — `roas` and `attributed_sales_*`
are deprecated.

Note: `conversions` equals click-through conversions. View-through is **not**
added and is a reporting figure only. Bidding and billing follow click-through
conversions exclusively. Figures for the current account day are provisional.

## What to measure against

Not industry benchmarks — none exist for this platform. Instead:

1. **Your own maximum tolerable CPA.** If the CPA is below it, the campaign
   works, regardless of how the number compares elsewhere.
2. **Your own previous period**, once there is one.
3. **The other ad groups** in the same campaign, given sufficient data.

## Regression rules

Comparison, threshold, action:

| Observation | Threshold | Action |
|---|---|---|
| Spend without conversion | 3× max CPA spent, 0 conversions | Pause the group, check landing page and measurement |
| CPA rising | +25 % week over week, ≥30 conversions | Lower the bid, review the weakest group's hints |
| CTR falling | −30 % week over week, ≥1,000 impressions | Ad fatigue, introduce a new variant |
| No delivery | 0 impressions over 48 h while active | Check all three status levels, then the bid, then the area |
| Budget spent early | Daily budget gone before midday | Bid too high, or demand higher than expected |
| Ad rejected | `review_status: rejected` | Read `reason_code` — a `crawler_*` code points at the landing page |
| One group dominates | >70 % of spend | Check whether the others are scoped too narrowly |

## What to report

Four things per finding, otherwise it is not a recommendation:

1. **Observation** with a number and a period
2. **Dependency** — what has to happen first
3. **Falsification** — how would you know the action did not work?
4. **Leading indicator** — what moves first

Example:

> **Group "Chatbot website": CPA 210 across 34 conversions (14 days).**
> Above the tolerable 150 for that service.
> *Dependency:* none, can be changed immediately.
> *Action:* lower the bid from 2.50 to 1.80.
> *Falsification:* if the CPA does not drop below 180 within 10 days, the bid
> is not the cause — look at the landing page.
> *Leading indicator:* average CPC within 3 days.

## Restraint

- **Do not change several things at once.** The effect cannot be attributed.
- **Wait 10 to 14 days after a change.**
- **Small differences are noise.** 2.1 % versus 2.3 % CTR at 800 impressions
  each means nothing.
- **When conversion data is missing, check measurement first**, not the
  campaign. A campaign that appears to deliver nothing often has a tracking
  problem.
