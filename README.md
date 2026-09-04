# chatgpt-ads-mcp

An MCP server plus Claude skills for the
[OpenAI Ads Advertiser API](https://developers.openai.com/ads) (ChatGPT Ads).
Python, uv, Docker.

Built because the existing servers miss three things that cost money in
practice: they do not retry failed requests, they do not bound their responses,
and they do not know the quirks of the location dataset.

## What this does differently

**Retries on 409.** The API sporadically answers
`409 "Ad Account is missing details."` with no relation to the request. In a
probe on 2026-09-04 that hit 8 of 32 calls; with backoff all 32 succeeded.
Other servers surface this as a failure when nothing is wrong.

**Response budgeting.** Insights return up to 2000 rows. Serialised verbatim
that fills the context window before the model can evaluate anything. This
server trims the longest lists and records what it trimmed and how to fetch the
rest.

**Location lookup that works.** Three pitfalls, all verified live:

| Input | Results | Reason |
|---|---|---|
| `Muenchen` | 0 | umlauts are mandatory |
| `München` | 78 | |
| `Munich` | 0 with `country_code: DE` | exonyms do not resolve |
| a German `Landkreis` | 0 | districts are not a location type |

The server rewrites ASCII transliterations, maps English exonyms, and says so
when a query names something that is not a location type.

**Postcode targeting.** The documentation lists `country`, `region` and `dma`.
There is a fourth type:

```json
{"id": "10015849", "type": "postal_code",
 "canonical_name": "10115, Berlin, Germany", "country_code": "DE"}
```

Conversely, `dma` never appeared for Germany in any query.

**Micros with an explanation.** Two expensive traps:

- CPM: `max_bid_micros` is the price per *single* impression, not per 1000.
  A 60.00 CPM is `60000`, not `60000000`.
- oCPC: `max_bid_micros` is a *CPA* bid, yet billing happens per click.

`explain_micros` converts a value and states what it means.

## Safety

- Every create tool forces `status="paused"` at the type level. A newly created
  campaign cannot spend until it is explicitly activated.
- Budgets above the ceiling require `confirm_budget=True`.
- `archive` is irreversible and requires `confirm_archive=True`.
- `OPENAI_ADS_MCP_READONLY=1` registers no write tools at all.
- The API key is never logged and never appears in error messages.

## Install

```bash
uv sync --group dev
uv run pytest
```

PyPI: [`chatgpt-ads-mcp`](https://pypi.org/project/chatgpt-ads-mcp/)

### Configuration

Copy `.env.example` to `.env`:

```
OPENAI_ADS_API_KEY=sk-...      # from https://ads.openai.com → Settings
OPENAI_ADS_BUDGET_CEILING=500  # confirmation threshold
OPENAI_ADS_CURRENCY=EUR
OPENAI_ADS_MCP_READONLY=0
```

One key covers exactly one ad account; there is no `account_id` parameter.

### Add it to Claude Code

One command, no clone and no install — `uvx` fetches the package on first run:

```bash
claude mcp add chatgpt-ads -e OPENAI_ADS_API_KEY=sk-... -- uvx chatgpt-ads-mcp
```

Read-only, if you want to look before you touch anything:

```bash
claude mcp add chatgpt-ads \
  -e OPENAI_ADS_API_KEY=sk-... \
  -e OPENAI_ADS_MCP_READONLY=1 \
  -- uvx chatgpt-ads-mcp
```

Verify with `claude mcp list`, then ask the assistant to call `get_account`.

### Other MCP clients

Any client that speaks stdio takes the same command:

```json
{
  "mcpServers": {
    "chatgpt-ads": {
      "command": "uvx",
      "args": ["chatgpt-ads-mcp"],
      "env": { "OPENAI_ADS_API_KEY": "sk-..." }
    }
  }
}
```

To run from a checkout instead, use `"command": "uv"` with
`"args": ["run", "--directory", "/path/to/openai-ads-tools", "chatgpt-ads-mcp"]`.

### Docker

```bash
docker build -t openai-ads-mcp .
docker run --rm -i --env-file .env openai-ads-mcp
```

## Tools

**Read:** `get_account`, `list_accounts`, `check_feature_access`, `search_geo`,
`list_campaigns`, `get_campaign`, `list_ad_groups`, `get_ad_group`, `list_ads`,
`get_ad`, `get_insights`, `list_audiences`, `list_conversion_setup`,
`explain_micros`

**Write:** `create_campaign`, `create_ad_group`, `create_ad`, `upload_creative`,
`set_account_brand`, `preview_ad`, `set_campaign_state`, `set_ad_group_state`,
`set_ad_state`, `set_negative_keywords`

`check_feature_access` is the quickest way in: it reports which features the
account has. This API answers 403, and sometimes 404, when a feature is gated —
not only when something is missing.

## Skills

`skills/` holds Claude skills covering the judgement the API does not:

| Skill | Purpose |
|---|---|
| `ads` | Orchestrator, shared reference files |
| `ads-campaign` | Clarify, decide, create |
| `ads-creative` | Copy, character economy, validation |
| `ads-hints` | Topic clusters, negative keywords |
| `ads-geo` | Postcode sets instead of a radius |
| `ads-audit` | Reporting with a data sufficiency gate |

The three reference files under `skills/ads/references/` are the substance:
`platform-facts.md` (only what is sourced), `misinformation.md` (what is
falsely claimed, with corrections), `benchmarks.md` (sufficiency thresholds and
how to derive a tolerable CPA).

### Copy validator

```bash
uv run python scripts/validate_creative.py \
  --title "Prototype in 4 weeks" --body "..." --brand "YourBrand"
```

Counts grapheme clusters rather than code points, and checks the rules language
models actually break: dashes, rules of three, filler verbs, invisible
characters. The style rules target German copy, which is the harder case; the
length and structural checks are language-independent.

## What the platform cannot do

So nobody goes looking:

- **No keyword targeting, no match types, no keyword planner.** Delivery is
  steered through `context_hints` — free text, evaluated semantically.
- **No reporting per context hint.** The ad group is the smallest unit of
  measurement. Put 2000 hints in one group and you will never learn which
  worked. Keep hints few per group and use more groups.
- **No radius targeting.** Model a catchment area as a list of postcodes.
- **No personalised ads in the EEA or Switzerland.**
- **No published benchmarks.** There is no official average CTR or reference
  CPC. Figures circulating as such are unsourced.
- **No sandbox.** Create everything paused and use `preview_ad`.

Character limits per OpenAPI spec v2.3.0: `title` 3–50, `body` at most 100.
The 35 and 67 figures in circulation contradict the spec.

## Status

Early. The read path and the safety model are exercised against a live account;
the write path is implemented and unit-tested but has seen limited production
use. Treat `create_*` as beta and check the preview before activating anything.

## License

MIT. See `NOTICE` for patterns adopted from other projects.
