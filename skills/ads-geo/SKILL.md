---
name: ads-geo
description: >
  Set up location targeting for OpenAI Ads — postcodes, regions, countries.
  Use this skill for geo targeting, local customers, catchment area, service
  radius, location, region, postcode, or whenever ads should only appear in
  certain areas.
user-invocable: true
license: MIT
metadata:
  version: "0.1.0"
  category: ads
---

# Location targeting

## Available levels

Verified against the live API on 2026-09-04 for Germany:

| Type | Example | ID |
|---|---|---|
| `country` | Germany | `1000056` |
| `region` | Baden-Württemberg | `2000346` |
| **`postal_code`** | 10115 Berlin | `10015849` |

**`postal_code` appears in no documentation but works.** Postcode-level
targeting is therefore possible.

**`dma` does not exist for Germany.** It never appeared in any query and looks
US-specific.

**Radius targeting does not exist.** Model a catchment area as a list of
postcodes. In practice that is more precise, because it follows municipal
boundaries rather than a circle.

With no location set, the campaign runs across every available area.

## Three pitfalls

**Umlauts are mandatory.**

| Input | Results |
|---|---|
| `Muenchen` | 0 |
| `München` | 78 |
| `Koeln` | 0 |
| `Köln` | 48 |

The `search_geo` tool rewrites ae/oe/ue automatically and tries both forms.
Calling the API directly requires handling this yourself.

**English exonyms find nothing German.** `Munich` returns two results, none
with `country_code: DE`. Same for `Cologne`.

**Districts and localities do not exist.** A German `Landkreis` returns no
results, and neither do sub-municipal localities — those are covered by the
parent town's postcode.

**Duplicate names.** `Birkenfeld` exists three times: 55765, 75217 and 97834.
Always select by postcode, never by name.

## Procedure

```
1. search_geo("Karlsruhe", country="DE")  -> collect IDs
2. Verify the postcodes match the intended place
3. create_campaign(location_ids=[...])
```

The resulting targeting object:

```json
{"targeting": {"locations": {"include": [{"id": "10020757"}]}}}
```

## Building a catchment area

Three tiers, from tight to wide. Pick by whether the service needs physical
proximity.

**Tier 1 — immediate surroundings.** The postcodes of the home town and its
neighbours. Suitable when someone has to travel to the customer.

**Tier 2 — economic area.** The nearest cities, each as a set of postcodes.
A mid-sized German city typically has 7 to 15 postcode entries; large cities
have 35 to 99.

**Tier 3 — region or country.** One region ID, or the country. Suitable when
the service is delivered remotely.

| Service type | Recommendation | Reason |
|---|---|---|
| Delivered remotely | Tier 3 or nationwide | proximity is irrelevant |
| Online-only product | nationwide | no travel involved |
| Requires an on-site visit | Tier 1–2 | travel time is the constraint |

**A tight area is not automatically better.** On a young platform with thin
volume, narrow targeting can mean almost nothing gets delivered. If the
service can be delivered remotely, there is little reason to restrict — unless
the copy deliberately plays on local proximity.

Sensible approach: **start wide, then narrow based on results.** Reporting with
`segment="country"` shows where delivery lands. There is no breakdown by
postcode.

## Local proximity in the copy

Because delivery can only be steered coarsely, proximity mostly works through
wording:

- "Based in <region>", "On site in <city>", "Serving <area> since <year>"

This excludes nobody, but speaks to the people who care about proximity — and
unlike narrow targeting, it costs no reach.
