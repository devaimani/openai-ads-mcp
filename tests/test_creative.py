"""Tests for the ad copy validator."""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_creative import (  # noqa: E402
    BODY_MAX,
    TITLE_MAX,
    brand_name_hint,
    check_text,
    grapheme_len,
    shortening_hints,
)


def test_ascii_counting():
    assert grapheme_len("Prozesse automatisieren") == 23


def test_nfd_umlauts_count_as_one():
    """The reason grapheme counting exists.

    "Munchen" with a combining diaeresis is 8 code points but 7 visible
    characters. A validator using len() miscounts and rejects valid copy.
    """
    nfc = unicodedata.normalize("NFC", "München")
    nfd = unicodedata.normalize("NFD", "München")

    assert len(nfd) > len(nfc)  # code points differ
    assert grapheme_len(nfd) == 7  # visible characters do not
    assert grapheme_len(nfc) == 7


def test_emoji_counts_as_one():
    assert grapheme_len("Start 🚀") == 7


def test_flag_emoji_counts_as_one():
    """A flag is two code points but one visible character."""
    assert grapheme_len("🇩🇪") == 1


def test_title_over_limit_is_blocker():
    findings = check_text("x" * 51, field="title", maximum=TITLE_MAX, minimum=3)
    assert any(f["severity"] == "blocker" and f["rule"] == "length" for f in findings)


def test_title_at_limit_passes():
    findings = check_text("x" * 50, field="title", maximum=TITLE_MAX, minimum=3)
    assert not [f for f in findings if f["rule"] == "length"]


def test_title_too_short_is_blocker():
    findings = check_text("ab", field="title", maximum=TITLE_MAX, minimum=3)
    assert any(f["severity"] == "blocker" for f in findings)


def test_body_limit_is_100_not_67():
    """The 67-character figure in circulation is wrong."""
    findings = check_text("x" * 80, field="body", maximum=BODY_MAX)
    assert not [f for f in findings if f["rule"] == "length"]


def test_em_dash_flagged():
    findings = check_text("Schnell — günstig", field="body", maximum=BODY_MAX)
    assert any(f["rule"] == "em_dash" for f in findings)


def test_zero_width_character_is_blocker():
    findings = check_text("Test​wort", field="body", maximum=BODY_MAX)
    assert any(f["rule"] == "invisible_characters" for f in findings)


def test_filler_verb_reported_once():
    """Stems rather than full forms, otherwise "entdecken" reports twice."""
    findings = check_text("Entdecken Sie mehr", field="title", maximum=TITLE_MAX)
    filler = [f for f in findings if f["rule"] == "filler_verb"]
    assert len(filler) == 1
    assert "entdecken" in filler[0]["message"]


def test_rule_of_three_flagged():
    findings = check_text("Schneller, besser und günstiger", field="body", maximum=BODY_MAX)
    assert any(f["rule"] == "rule_of_three" for f in findings)


def test_clean_german_copy_passes():
    findings = check_text("Angebot in 48 Stunden", field="title", maximum=TITLE_MAX, minimum=3)
    assert not [f for f in findings if f["severity"] in ("blocker", "hoch")]


def test_shortening_hints_are_actionable():
    hints = shortening_hints("Die Loesung hilft Ihnen zu sparen und wachsen")
    joined = " ".join(hints)
    assert "articles" in joined.lower()
    assert "verb phrases" in joined.lower()


def test_brand_name_flagged_when_present():
    hints = brand_name_hint("Acme: Prozesse automatisieren", "Acme")
    assert hints and "brand name" in hints[0].lower()


def test_brand_name_not_flagged_when_absent():
    assert brand_name_hint("Prozesse automatisieren", "Acme") == []
