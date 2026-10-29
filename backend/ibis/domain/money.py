"""Money helpers. All split math is done in integer cents to avoid rounding drift."""
from decimal import ROUND_HALF_UP, Decimal


def to_cents(amount: Decimal | float | int | str) -> int:
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_cents(cents: int) -> float:
    return cents / 100


def split_cents(total: int, parts: int) -> list[int]:
    """Split `total` into `parts` near-equal integers that add up exactly to `total`.

    The leftover cents go to the first entries, so callers should pass people
    in a stable order.
    """
    if parts <= 0:
        raise ValueError("parts must be positive")
    base, remainder = divmod(total, parts)
    return [base + 1 if i < remainder else base for i in range(parts)]
