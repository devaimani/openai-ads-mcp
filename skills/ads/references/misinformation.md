<!-- Verified: 2026-09-04 -->
# What gets claimed about OpenAI Ads that is not true

This file lists statements that circulate and **do not hold**. Training data
and blog posts are full of them, and several originate in widely shared
repositories. Do not adopt them, however plausible they sound.

## Character limits

> "Headline 35 characters, description 67 characters"

**Wrong.** The spec says `title` 3–50 and `body` at most 100. The 35/67 figures
come from a public skill repository where they are given without a source.
Writing to them wastes 15 and 33 characters per ad respectively.

## Keywords

> "Broad match / phrase match / exact match for ChatGPT Ads"
> "Keyword bids", "keyword planner", "search volume for ChatGPT"

**None of this exists.** The word "keyword" appears once in the entire
documentation; "match type" does not appear at all. There is no keyword object
in the API.

Delivery is steered through `context_hints[]` — free text, evaluated
semantically, with no per-hint bid and no per-hint reporting dimension.

There is no keyword planner equivalent. No endpoint returns search volume,
competition density or click price estimates.

## Geo

> "Radius targeting", "target within X km", "city targeting"

**Radius does not exist.** A catchment area is modelled as a list of postcodes.

> "Only country, region and dma"

**Incomplete.** There is a fourth type, `postal_code`, which the documentation
does not mention. Verified live on 2026-09-04: Berlin 99 postcodes, Munich 78,
Cologne 48.

Conversely: **`dma` never appeared for Germany.** That type looks restricted to
the US.

> "Target a district"

Districts are not a location type. Sub-municipal localities are not either —
they are covered by the parent town's postcode.

## Benchmarks

> "The average CTR on ChatGPT Ads is X %"
> "A typical CPC is Y"

**OpenAI publishes no benchmarks.** No CTR, no CPC, no CPM, no industry
figures. Any such number is unsourced.

In markets where self-service opened recently there is an additional problem:
an auction needs bidders, and prices only settle over weeks. A "current CPC"
for such a market cannot exist yet.

Click prices from search advertising are **not** a substitute: different
auction, different participants, different inventory, different ranking.

## Personalisation

> "Custom audiences / retargeting in the EEA"

Personalised ads are **not available** in the EEA or Switzerland. Delivery
there is steered by conversation context, coarse location, time of day and
device type.

## Metrics

> "roas", "attributed_sales_amount", "attributed_sales_count"

**Deprecated**, with removal scheduled for 2026-08-17. Use
`order_created_roas` and `order_created_attributed_sales` instead.

## Environment

> "Sandbox", "test mode"

**Does not exist.** Substitutes: create everything paused, use
`validate_only: true` on bulk jobs, and `POST /ads/{id}/preview` for a visual
check.

> "Official Python SDK"

**Does not exist.** On PyPI, `openai-ads`, `openai_ads`, `chatgpt-ads` and
`openai-advertising` are all absent. The documentation shows `curl` only.
