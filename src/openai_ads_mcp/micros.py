"""Conversion between currency amounts and micros.

Kept in one place because this is where the most expensive mistakes on this
API happen. Both special cases are documented and confirmed:

1. **oCPC:** with ``bidding_type="conversions"``, ``max_bid_micros`` is a CPA
   bid — but billing happens per click. From the docs: "The bid is a CPA input
   even though OpenAI bills the child ad group per click." Passing a CPC value
   here bids orders of magnitude wrong.

2. **CPM:** ``max_bid_micros`` is the price per *single* impression, not per
   mille. A 60.00 CPM is 0.06 per impression, so 60_000 micros — not
   60_000_000. A factor of 1000 in the wrong direction.

Insights return ``spend``/``cpc``/``cpm`` as decimal amounts, not micros. Only
fields with the ``_micros`` suffix are micros.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MICROS_PER_UNIT = 1_000_000

#: Minimum campaign budget accepted by the API (= 1.00).
MIN_BUDGET_MICROS = 1_000_000

#: Maximum max_bid_micros per the OpenAPI spec.
MAX_BID_MICROS = 30_400_000_000_000


class MicrosError(ValueError):
    """Invalid amount."""


def to_micros(amount: float | int | str | Decimal) -> int:
    """Currency amount to micros, rounded half up.

    >>> to_micros(1.00)
    1000000
    >>> to_micros("0.06")
    60000
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise MicrosError(f"Not a valid amount: {amount!r}") from exc
    if value.is_nan() or value.is_infinite():
        raise MicrosError(f"Not a valid amount: {amount!r}")
    if value < 0:
        raise MicrosError(f"Amount must not be negative: {amount!r}")
    micros = (value * MICROS_PER_UNIT).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(micros)


def from_micros(micros: int | float | str) -> Decimal:
    """Micros to a currency amount with two decimal places."""
    try:
        value = Decimal(str(micros))
    except (InvalidOperation, ValueError) as exc:
        raise MicrosError(f"Not a valid micros value: {micros!r}") from exc
    return (value / MICROS_PER_UNIT).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def budget_to_micros(amount: float | int | str) -> int:
    """Campaign budget to micros, enforcing the API minimum."""
    micros = to_micros(amount)
    if micros < MIN_BUDGET_MICROS:
        raise MicrosError(
            f"Budget too small: {amount} is {micros} micros, "
            f"minimum is {MIN_BUDGET_MICROS} (= 1.00)."
        )
    return micros


def bid_to_micros(
    amount: float | int | str,
    *,
    billing_event: str,
    bidding_type: str | None = None,
) -> tuple[int, str]:
    """Bid to micros, with an explanation of what the value means.

    Returns ``(micros, explanation)``. The explanation belongs in the tool
    response so the transcript records what the bid actually represents.
    """
    micros = to_micros(amount)
    if micros < 1:
        raise MicrosError(f"Bid too small: {amount} is {micros} micros, minimum is 1.")
    if micros > MAX_BID_MICROS:
        raise MicrosError(f"Bid too large: {micros} > {MAX_BID_MICROS}.")

    if bidding_type == "conversions":
        note = (
            f"{amount} is a CPA bid (target cost per conversion). Billing still "
            "happens per click — that is intended, not a bug."
        )
        if billing_event != "click":
            raise MicrosError(
                "With bidding_type='conversions', billing_event must be 'click', "
                f"not {billing_event!r}."
            )
    elif billing_event == "impression":
        cpm = from_micros(micros) * 1000
        note = (
            f"{amount} is the price per SINGLE impression, which is a CPM of "
            f"{cpm} (price per 1000). If a CPM of {amount} was intended, the "
            f"correct value is {from_micros(to_micros(amount) // 1000)}."
        )
    else:
        note = f"{amount} is the maximum bid per click (CPC)."

    return micros, note
