---
name: ads-campaign
description: >
  Build a complete OpenAI Ads campaign — from clarifying the goal through
  structure, bidding and copy to creating everything through the MCP server.
  Use this skill when a campaign should be created, planned, set up or
  launched.
user-invocable: true
license: MIT
metadata:
  version: "0.1.0"
  category: ads
---

# Building a campaign

Three stages in order: clarify, decide, create. The first is not skipped —
without it you get campaigns whose results cannot be interpreted.

## 1. Clarify

Ask one topic at a time, conversationally. Skip anything already answered
earlier in the conversation.

1. **Goal.** One, not three. Leads, appointments, sales or awareness? This
   determines `bidding_type`, which is immutable afterwards.
2. **Offer.** What exactly, for whom, at what price, on which landing page?
3. **Proof.** Three to five concrete anchors: numbers, timeframes, references.
   These carry the ad copy later.
4. **Differentiation.** Often sharpest as a negative: without an IT department,
   without a contract term.
5. **Intents.** Three to six clearly separated conversational situations. Each
   becomes an ad group.
6. **Area.** Nationwide or restricted? Can the service be delivered remotely?
7. **Budget.** Total, and a daily cap if wanted.
8. **Measurement.** Is conversion tracking in place? **Settle this before the
   first campaign** — without it you cannot switch to conversion optimisation
   later.

Invent nothing. Mark what the user does not know as open and move on. An
incomplete draft beats a fabricated one.

## 2. Decide

### Choosing the bidding type

| Goal | `bidding_type` | Requirement |
|---|---|---|
| Clicks, gathering first data | `clicks` | none |
| Conversions | `conversions` | enabled account, exactly one active standard event, active source |
| Awareness | `impressions` | none |

**For a start without measurement history: `clicks`.** Conversion optimisation
needs data that does not exist yet. And since `bidding_type` is immutable, the
later switch means a new campaign anyway — so nothing is lost.

### Structure

- One campaign per goal and bidding type
- One ad group per intent, with 10 to 25 `context_hints`
- Two or three ads per group, each with a different angle

Show the structure and confirm it before creating anything. Corrections are
free at this point and expensive later.

### Setting the bid

There are no benchmarks for this platform, so do not guess:

1. Derive the maximum tolerable CPA from the business model (see
   `ads/references/benchmarks.md`)
2. Start cautiously, err low
3. Adjust after two weeks using real numbers

**Click prices from search advertising are not a reference point.** Different
auction, different participants. Transferring them means adopting a number with
false precision.

## 3. Create

Everything is created paused. Nothing spends until explicitly activated.

```
get_account                → check currency, timezone, review.status
check_feature_access       → what is enabled?
search_geo(...)            → location IDs
create_campaign(...)       → paused
create_ad_group(...)       → paused, with context hints
upload_creative(image_url) → file_id
create_ad(...)             → paused, enters review
preview_ad(ad_id)          → look at it (valid 24 hours)
```

Validate the copy before `create_ad`:

```bash
uv run python scripts/validate_creative.py --title "..." --body "..."
```

### Activating

Only once the preview and the review are in order. Top down:

```
set_campaign_state(id, "activate")
set_ad_group_state(id, "activate")
set_ad_state(id, "activate")
```

Delivery requires all three levels to be active.

**On a first campaign, activate one ad group, not all of them.** Watch for two
or three days, then add the next.

## Afterwards

Do not intervene immediately. The first days fluctuate heavily, and every
change resets measurement.

- **Days 1–3:** observe only. Is delivery starting? Are ads serving or stuck in
  review?
- **Days 4–14:** let it run. Intervene only for something clearly broken — an
  ad rejected, the budget gone in a day, zero impressions.
- **From day 14:** assess, using `ads-audit`.

## Common mistakes

| Mistake | Consequence |
|---|---|
| `bidding_type: conversions` without measurement | Campaign cannot optimise; switching requires recreating it |
| All hints in one group | Result cannot be interpreted |
| Activating everything at once | If something goes wrong, the cause is unclear |
| Adjusting after three days | Too little data; reacting to noise |
| Narrow area for a remotely delivered service | Almost no delivery |
| Landing page unchecked | Rejection with a `crawler_*` reason |
