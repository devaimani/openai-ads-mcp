---
name: ads-creative
description: >
  Write and validate ad copy for OpenAI Ads — headline 3-50 characters,
  description up to 100, counted by visible characters rather than code
  points. Use this skill for ad copy, headline, description, creative,
  ad variants, or when copy is too long and needs shortening.
user-invocable: true
license: MIT
metadata:
  version: "0.1.0"
  category: ads
---

# Ad copy

## Limits

| Field | Limit |
|---|---|
| `title` | **3–50 characters** |
| `body` | **up to 100 characters** |

The figures 35 and 67 that circulate are wrong. They come from a repository
without a source and contradict the OpenAPI spec.

Check every draft:

```bash
uv run python scripts/validate_creative.py \
  --title "..." --body "..." --brand "YourBrand"
```

The validator counts visible characters, not code points. With composed
characters — German umlauts in NFD form, emoji, flags — `len()` miscounts and
rejects valid copy.

## The reading situation

The ad appears mid-conversation as a small card. The reader is not searching;
they are occupied with something else. The logo is displayed automatically.

Three consequences:

1. **The brand name does not belong in the headline.** The logo already carries
   it. Spend those six to ten characters on substance.
2. **The first clause carries the ad.** What follows a comma often goes unread.
3. **Concrete beats general.** "In 4 weeks" works; "fast" does not.

## What works

**Contrast.** Makes the difference visible in few characters.
"Automation without an IT department" (35)

**Proof.** A number, a name, a deadline.
"Prototype in 4 weeks" (20)

**Imperative.** Verb first, reads quickly.
"Get a quote in 48 hours" (23)

**Compressed promise.** Subject, verb, outcome. No filler.
"Invoices that file themselves" (29)

**Question.** Works when it names a pain the reader recognises.
"Still writing quotes by hand?" (29)

## What does not

- **Adjective stacks** ("innovative, holistic, scalable") — burn characters,
  say nothing
- **Dashes** — a comma or colon does the job and saves a character
- **Rules of three** ("faster, better, cheaper") — read as machine-generated;
  two beats land harder at 50 characters
- **Empty verbs** ("Discover", "Unlock", "Transform")
- **Abstract nouns** ("solutions", "experiences", "journeys")
- **Brand name as headline** — wasted space

## Shortening

Compound nouns make a 50-character headline tighter in German than in English.
Seven moves, each with the saving:

1. **Drop articles.** "Die Prozesse automatisieren" → "Prozesse automatisieren" (4)
2. **Digits, not words.** "vier Wochen" → "4 Wochen" (3)
3. **Collapse verb phrases.** "hilft Ihnen zu sparen" → "spart" (15)
4. **Cut hedges.** "oft in 4 Wochen" → "in 4 Wochen" (4)
5. **Drop the brand name.** The logo carries it (6–10)
6. **Comma instead of "und".** (2)
7. **Break up or replace compounds.** "Geschäftsprozessautomatisierung" →
   "Abläufe automatisieren" (8)

If that is not enough, the line is trying to do too much. Keep one idea, cut
the rest.

## Variants

Two or three ads per ad group, each with a **different angle** — not the same
claim reworded. Otherwise the comparison is worthless.

A reliable pairing: one ad built on proof, one on contrast. They address
different motives, so a difference in outcome is interpretable.

Record **what each variant is meant to test**, otherwise the result cannot be
read later.

## The image

<!-- Verified: 2026-09-14 against a live account -->

Two measurements change how a motif should be drawn.

**The card crops to a centre strip.** A created ad carries an `image_crop`,
and on a 16:9 upload it read `width: 0.558, height: 1, x: 0.221` — the middle
56 % of the width at full height, which is square. Supplying 16:9 throws away
44 % of the image, 304 px on each side of a 1376 px file. **Upload square.**

**It renders at about 116×116.** Measured in a preview. That is roughly a
thumbnail, so:

- One object, or one relation between two objects. Anything with three or more
  elements turns to texture.
- The signal colour needs area, not a line. A motif that carries it on a thin
  outline loses it entirely; one that fills a whole shape still reads.
- Fine hatching, thin rules and small repeated marks disappear. Contrast
  between large flat areas survives.

Check a draft by downscaling it to 116 px and looking at it at that size. If
you cannot tell what it is, neither can the reader.

## Landing page

The headline has to match what the reader finds after the click. The most
common cause of a good click rate with no conversions is a break between
promise and landing page.

Before creating the ad:
- The landing page is reachable, including for the review crawler
- No redirect between click and destination — link the canonical URL
- The wording of the ad appears on the page in substance

A `review_status: rejected` with a `crawler_*` reason points at the landing
page, not the copy.
