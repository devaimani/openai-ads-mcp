#!/usr/bin/env python3
"""Validate ad copy against platform limits and style rules.

Two differences from comparable validators:

1. **Counting.** ``len()`` over Python code points miscounts composed
   characters. "Munchen" with a combining diaeresis is 8 code points but 7
   visible characters. This script normalises to NFC and counts grapheme
   clusters.

2. **It checks the rules language models actually break.** A model usually
   manages the length limit on its own; em dashes, rules of three and filler
   verbs are what slip through.

Output is JSON. Exit 0 = clean, 1 = violation, 2 = no input.

The style rules are written for German ad copy, which is the harder case
because compound nouns make a 50-character headline tight. The length and
structural checks are language-independent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

# Limits from OpenAPI spec v2.3.0. Not 35/67 — that is an unsourced figure
# in circulation that contradicts the spec.
TITLE_MIN, TITLE_MAX = 3, 50
BODY_MAX = 100

# Regional indicator symbols (flags) are two code points forming one glyph.
_RI = range(0x1F1E6, 0x1F200)
_ZWJ = "‍"
_VARIATION = range(0xFE00, 0xFE10)
_SKIN_TONES = range(0x1F3FB, 0x1F400)

# German filler verbs, matched as stems so one entry covers all inflections.
FILLER_VERB_STEMS = (
    "entdeck",
    "erleb",
    "revolutionier",
    "transformier",
    "freischalt",
    "durchstart",
    "boost",
    "maximier",
)

ABSTRACT_NOUNS = ("Lösungen", "Erlebnisse", "Journey", "Ökosystem", "Synergien")

VAGUE_ADJECTIVES = (
    "innovativ",
    "ganzheitlich",
    "maßgeschneidert",
    "zukunftsweisend",
    "hochmodern",
    "erstklassig",
)

ZERO_WIDTH = ("​", "﻿", "‌")


def grapheme_len(text: str) -> int:
    """Count visible characters rather than code points."""
    normalized = unicodedata.normalize("NFC", text)
    chars = list(normalized)
    count = 0
    index = 0

    while index < len(chars):
        char = chars[index]
        code = ord(char)

        # Combining marks attach to the previous cluster.
        if unicodedata.combining(char) or code in _VARIATION or code in _SKIN_TONES:
            index += 1
            continue

        # A flag is two regional indicators forming one glyph.
        if code in _RI and index + 1 < len(chars) and ord(chars[index + 1]) in _RI:
            count += 1
            index += 2
            continue

        count += 1
        index += 1

        # Everything joined by a ZWJ belongs to the same cluster.
        while index + 1 < len(chars) and chars[index] == _ZWJ:
            index += 2

    return count


def check_text(text: str, *, field: str, maximum: int, minimum: int = 0) -> list[dict]:
    """Return a list of findings for one field."""
    findings: list[dict] = []
    length = grapheme_len(text)

    if length > maximum:
        findings.append(
            {
                "severity": "blocker",
                "rule": "length",
                "message": f"{field}: {length} characters, limit is {maximum}. "
                f"{length - maximum} too many.",
            }
        )
    if minimum and length < minimum:
        findings.append(
            {
                "severity": "blocker",
                "rule": "length",
                "message": f"{field}: {length} characters, at least {minimum} required.",
            }
        )

    if "—" in text or "–" in text:
        findings.append(
            {
                "severity": "high",
                "rule": "em_dash",
                "message": f"{field}: dash found. Use a comma or colon instead — it also "
                "saves a character.",
            }
        )

    if any(q in text for q in ('"', "„", "“")):
        findings.append(
            {
                "severity": "low",
                "rule": "quotes",
                "message": f"{field}: quotation marks cost two characters and rarely earn them.",
            }
        )

    if "  " in text:
        findings.append(
            {
                "severity": "high",
                "rule": "whitespace",
                "message": f"{field}: double space.",
            }
        )

    if any(z in text for z in ZERO_WIDTH):
        findings.append(
            {
                "severity": "blocker",
                "rule": "invisible_characters",
                "message": f"{field}: contains an invisible character. Remove it.",
            }
        )

    lowered = text.lower()

    for stem in FILLER_VERB_STEMS:
        match = re.search(rf"\b\w*{re.escape(stem)}\w*", lowered)
        if match:
            findings.append(
                {
                    "severity": "medium",
                    "rule": "filler_verb",
                    "message": f"{field}: '{match.group()}' says nothing concrete. Replace it "
                    "with the actual action.",
                }
            )

    for noun in ABSTRACT_NOUNS:
        if noun.lower() in lowered:
            findings.append(
                {
                    "severity": "medium",
                    "rule": "abstract_noun",
                    "message": f"{field}: '{noun}' is vague.",
                }
            )

    for word in VAGUE_ADJECTIVES:
        if word.lower() in lowered:
            findings.append(
                {
                    "severity": "medium",
                    "rule": "empty_adjective",
                    "message": f"{field}: '{word}' is a phrase any competitor could write too.",
                }
            )

    # A rule of three reads as machine-generated and costs too much space at
    # 50 characters.
    if re.search(r"\w+,\s*\w+\s+und\s+\w+", text):
        findings.append(
            {
                "severity": "medium",
                "rule": "rule_of_three",
                "message": f"{field}: three-part list. Two beats land harder and save characters.",
            }
        )

    if re.search(r"\b(vier|fünf|sechs|sieben|acht|neun|zehn|zwölf)\b", lowered):
        findings.append(
            {
                "severity": "low",
                "rule": "spelled_number",
                "message": f"{field}: write the number as a digit to save characters.",
            }
        )

    return findings


def shortening_hints(text: str) -> list[str]:
    """Concrete shortening suggestions for German ad copy."""
    hints: list[str] = []
    lowered = text.lower()

    if re.search(r"\b(der|die|das|den|dem|des)\b", lowered):
        hints.append(
            "Drop articles: 'Die Prozesse automatisieren' -> 'Prozesse automatisieren' (4 chars)"
        )
    if re.search(r"\bhilft (ihnen )?(dabei )?zu\b|\bermöglicht es\b", lowered):
        hints.append("Collapse verb phrases: 'hilft Ihnen zu sparen' -> 'spart' (15 chars)")
    if re.search(r"\b(oft|meist|in der regel|typischerweise|normalerweise)\b", lowered):
        hints.append("Cut hedges: 'oft in 4 Wochen' -> 'in 4 Wochen' (4 chars)")
    if " und " in lowered:
        hints.append("Replace 'und' with a comma (2 chars)")
    if re.search(r"\bzum beispiel\b|\bunter anderem\b", lowered):
        hints.append("'zum Beispiel' -> 'z. B.' or drop it entirely")

    return hints


def brand_name_hint(text: str, brand: str | None) -> list[str]:
    """Flag the brand name in copy — the logo already carries it."""
    if brand and brand.lower() in text.lower():
        return [
            f"Drop the brand name '{brand}': the logo is shown anyway. "
            f"Frees {len(brand)} characters for substance."
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OpenAI Ads creative copy.")
    parser.add_argument("--title", help="Headline, 3-50 characters")
    parser.add_argument("--body", help="Description, at most 100 characters")
    parser.add_argument("--brand", help="Brand name to flag if it appears in the copy")
    args = parser.parse_args()

    if not args.title and not args.body:
        parser.print_usage(sys.stderr)
        print("Provide --title and/or --body.", file=sys.stderr)
        return 2

    findings: list[dict] = []
    measured: dict[str, dict] = {}
    hints: list[str] = []

    for value, field, maximum, minimum in (
        (args.title, "title", TITLE_MAX, TITLE_MIN),
        (args.body, "body", BODY_MAX, 0),
    ):
        if not value:
            continue
        findings += check_text(value, field=field, maximum=maximum, minimum=minimum)
        length = grapheme_len(value)
        measured[field] = {
            "text": value,
            "characters": length,
            "limit": maximum,
            "remaining": maximum - length,
        }
        if length > maximum:
            hints += shortening_hints(value)
        hints += brand_name_hint(value, args.brand)

    blockers = [f for f in findings if f["severity"] == "blocker"]
    report = {
        "fields": measured,
        "findings": findings,
        "shortening_hints": sorted(set(hints)),
        "passed": not blockers,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
