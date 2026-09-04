"""Location lookup, including the quirks of the German dataset.

Everything here comes from probing the live API on 2026-09-04, not from the
documentation. The docs list only ``country``, ``region`` and ``dma``, which
is misleading in three ways:

* There is a fourth type, ``postal_code``. Postcode-level targeting works —
  Berlin returned 99 entries, Munich 78, Cologne 48.
* ``dma`` never appeared for Germany at all. That type looks US-specific.
* Place names without umlauts return nothing. "Muenchen" finds nothing;
  only "München" works. English exonyms ("Munich", "Cologne") return no
  German results either.

Not resolvable because they are absent from the dataset: districts
("Landkreis", "Enzkreis" -> 0 results) and sub-municipal localities, which are
covered by their parent town's postcode.
"""

from __future__ import annotations

from typing import Any

#: Reverse mapping of ASCII transliterations.
#:
#: "ss" -> "ß" is deliberately NOT included. It does more harm than good:
#: "Duesseldorf" would become "Düßeldorf" because the "ss" in the middle of
#: that word is not an eszett. Place names with a genuine "ss" (Giessen,
#: Neuss) are rare enough to resolve via postcode instead.
_UMLAUT_MAP = (
    ("ae", "ä"),
    ("oe", "ö"),
    ("ue", "ü"),
    ("Ae", "Ä"),
    ("Oe", "Ö"),
    ("Ue", "Ü"),
)

#: English exonyms that return no German results.
_EXONYMS = {
    "munich": "München",
    "cologne": "Köln",
    "nuremberg": "Nürnberg",
    "hanover": "Hannover",
    "brunswick": "Braunschweig",
    "vienna": "Wien",
    "zurich": "Zürich",
    "geneva": "Genf",
    "bavaria": "Bayern",
    "saxony": "Sachsen",
    "hesse": "Hessen",
    "thuringia": "Thüringen",
    "lower saxony": "Niedersachsen",
    "north rhine-westphalia": "Nordrhein-Westfalen",
    "rhineland-palatinate": "Rheinland-Pfalz",
    "saxony-anhalt": "Sachsen-Anhalt",
    "mecklenburg-western pomerania": "Mecklenburg-Vorpommern",
}

#: Terms that do not exist as a location type. Verified against the live API.
_UNSUPPORTED_HINTS = {
    "kreis": (
        "Districts are not a location type (for example 'Enzkreis' returns no "
        "results). Target the postcodes of the towns inside instead."
    ),
    "landkreis": (
        "Districts are not a location type. Target the postcodes of the towns inside instead."
    ),
    "ortsteil": (
        "Sub-municipal localities have no separate entry. They are covered by "
        "the parent town's postcode."
    ),
}


def query_variants(query: str) -> list[str]:
    """Produce search variants in order of preference.

    >>> query_variants("Muenchen")
    ['Muenchen', 'München']
    >>> query_variants("Munich")
    ['Munich', 'München']
    """
    variants = [query]

    exonym = _EXONYMS.get(query.strip().lower())
    if exonym and exonym not in variants:
        variants.append(exonym)

    umlaut = query
    for ascii_form, umlaut_form in _UMLAUT_MAP:
        umlaut = umlaut.replace(ascii_form, umlaut_form)
    if umlaut != query and umlaut not in variants:
        variants.append(umlaut)

    return variants


def unsupported_hint(query: str) -> str | None:
    """Warn about queries that are not a supported location type."""
    lowered = query.strip().lower()
    for needle, hint in _UNSUPPORTED_HINTS.items():
        if needle in lowered:
            return hint
    return None


def summarize(results: list[dict[str, Any]], *, country: str | None = None) -> dict[str, Any]:
    """Group results by type and surface ambiguous names."""
    if country:
        results = [r for r in results if r.get("country_code") == country.upper()]

    by_type: dict[str, list[dict[str, Any]]] = {}
    for entry in results:
        by_type.setdefault(entry.get("type", "unknown"), []).append(entry)

    summary: dict[str, Any] = {
        "count": len(results),
        "types": {name: len(items) for name, items in by_type.items()},
        "results": results,
    }

    # The same name in several regions means the caller has to pick by postcode.
    names: dict[str, list[str]] = {}
    for entry in results:
        names.setdefault(entry.get("name", ""), []).append(entry.get("canonical_name", ""))
    ambiguous = {n: c for n, c in names.items() if len(c) > 1 and n}
    if ambiguous:
        summary["ambiguous"] = {
            "names": ambiguous,
            "hint": (
                "Several places share this name. Select by postcode rather than "
                "by name — for example 'Birkenfeld' exists in 55765, 75217 and "
                "97834."
            ),
        }

    return summary


def to_targeting(location_ids: list[str]) -> dict[str, Any]:
    """Build the ``targeting.locations`` object for campaign create/update."""
    return {"locations": {"include": [{"id": str(i)} for i in location_ids]}}
