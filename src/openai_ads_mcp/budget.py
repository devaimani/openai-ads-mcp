"""Token budget for tool responses.

Insights allow up to 2000 rows, and serialising that verbatim fills the
context window before the model can evaluate anything. This module trims the
longest lists and records what was trimmed.
"""

from __future__ import annotations

import json
from typing import Any

#: Approximate upper bound for a tool response, in characters.
CHAR_BUDGET = 60_000

#: Fields that never belong in a response — large and of no use to the model.
HEAVY_FIELDS = frozenset({"raw", "raw_response", "html", "request", "response"})

_MAX_PASSES = 80


def compact(value: Any) -> Any:
    """Recursively drop None values and heavy fields."""
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items() if v is not None and k not in HEAVY_FIELDS}
    if isinstance(value, list):
        return [compact(v) for v in value]
    return value


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _largest_list(
    node: Any, path: tuple[str, ...] = ()
) -> tuple[list[Any] | None, tuple[str, ...], int]:
    """Find the longest list anywhere in the object tree."""
    best: list[Any] | None = None
    best_path = path
    best_len = 0

    if isinstance(node, list):
        best, best_path, best_len = node, path, len(node)
        for index, item in enumerate(node):
            found, found_path, found_len = _largest_list(item, path + (str(index),))
            if found_len > best_len:
                best, best_path, best_len = found, found_path, found_len
    elif isinstance(node, dict):
        for key, item in node.items():
            found, found_path, found_len = _largest_list(item, path + (key,))
            if found_len > best_len:
                best, best_path, best_len = found, found_path, found_len

    return best, best_path, best_len


def enforce(payload: Any, *, budget: int = CHAR_BUDGET) -> str:
    """Serialise while staying within the character budget.

    Repeatedly halves the longest list until the response fits, then appends a
    note describing what was trimmed and how to fetch the rest.
    """
    data = compact(payload)
    text = _serialize(data)
    if len(text) <= budget:
        return text

    truncated: dict[str, int] = {}
    for _ in range(_MAX_PASSES):
        target, path, length = _largest_list(data)
        if target is None or length <= 1:
            break

        keep = max(1, length // 2)
        del target[keep:]
        truncated[".".join(path) or "data"] = keep

        note = {
            "truncated": truncated,
            "reason": f"Response exceeded {budget} characters; longest lists were trimmed.",
            "how_to_get_the_rest": (
                "Use a smaller 'limit', page with the 'after' cursor, or narrow "
                "the result with 'filters'."
            ),
        }
        if isinstance(data, dict):
            data["_response"] = note
            candidate = data
        else:
            candidate = {"data": data, "_response": note}

        text = _serialize(candidate)
        if len(text) <= budget:
            return text

    return text[:budget]
