<!-- Created: 2026-09-04 — grows with real data -->
# Benchmarks

## The starting point: there are none

OpenAI publishes no benchmark figures for ChatGPT Ads. No CTR, no CPC, no CPM,
no industry values. For markets where self-service opened recently there is no
history to derive anything from either.

**So benchmarks here come from your own data.** This file is meant to be
extended after every measurement period. Until then the fields stay empty
rather than being filled with figures from other platforms that do not carry
over.

## Data sufficiency — when a number means something

Check before every assessment. The thresholds are deliberately conservative,
because a wrong call here costs real budget.

| Metric | Minimum data | Below that |
|---|---|---|
| CTR | 1,000 impressions | no judgement, report the raw number only |
| CPC | 100 clicks | the value is sampling noise |
| Conversion rate | 100 clicks and 10 conversions | no judgement |
| CPA | 30 conversions | no bid recommendation |
| ROAS | 30 conversions with revenue | no judgement |
| Trend over time | 14 days of delivery | too short, weekday effects dominate |
| A/B comparison of two ad groups | 100 clicks each | difference is not meaningful |

**Rule:** if fewer than four of seven metrics are sufficiently supported, do
**not** output an overall score. Output this instead:

```
Overall assessment: NOT POSSIBLE (3/7 metrics sufficiently supported)
Supported:     impressions, clicks, spend
Not supported: CTR, CPA, conversion rate, ROAS
Recommendation: keep running for another 10 days, then reassess.
```

Reason: a score built on too little data looks like poor performance when in
truth data is simply missing. That is how working campaigns get switched off
too early.

## Your own measured values

One row per measurement period. Meaningful ranges emerge from three periods
onward.

| Period | Ad group | Impr. | Clicks | CTR | CPC | Conv. | CPA | Note |
|---|---|---|---|---|---|---|---|---|
| _(no data yet)_ | | | | | | | | |

## Commercial thresholds

These numbers do **not** come from the platform but from your own business
model. They are usable from day one and matter more than any platform
benchmark.

Deriving the maximum tolerable CPA:

```
order value (net)  ×  close rate  ×  target margin  =  max CPA
```

Worked example for a service business:

| Order value | Close rate | Target margin | max CPA |
|---|---|---|---|
| 2,500 | 20 % | 50 % | 250 |
| 1,500 | 20 % | 50 % | 150 |
| 200 | 20 % | 50 % | 20 |

**The close rate is an assumption until measured.** Replace it with your own
figure as soon as leads exist. Until then, be conservative: at a 10 % close
rate every value above halves.

Where there is recurring revenue, the first order justifies a higher CPA than a
one-off view suggests. A 1,000 setup fee plus 200 per month over twelve months
is 3,400, not 1,000.

## Where external data helps and where it does not

| Source | Useful for | Not useful for |
|---|---|---|
| ChatGPT scraping APIs | vocabulary, phrasing, whether local businesses get named at all | volume forecasting |
| Search intent classification | splitting ad groups by intent | bid levels |
| Search volume from web search | **relative** ranking of topics | absolute expectations, forecasts |
| CPC from web search advertising | **none of this** | bids, budget planning, success criteria |

On that last row: search-advertising click prices describe a different auction
with different participants and different inventory. A CPC of 8 there says
nothing about the click price here. Using it as a starting bid means adopting a
number with false precision.

## Working without benchmarks

1. Start small, create everything paused, activate one thing at a time
2. Measure for two to three weeks without intervening
3. Only then assess — against your own max CPA, not against foreign figures
4. Record the results in the table above
5. From the third period onward you have your own ranges, and those are more
   reliable than any industry figure
