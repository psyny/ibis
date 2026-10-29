"""Who-pays-whom settlement with the fewest transfers.

1. Each cost adds what every payer paid and subtracts what every coverer owes
   (equal shares, see `money.split_cents`). The result is a net balance per
   person: positive = should receive money, negative = should pay.
2. Balances are settled with as few transfers as possible. A group of k people
   whose balances sum to zero can always be settled with k - 1 transfers, so the
   minimum number of transfers is `n - (max number of disjoint zero-sum groups)`.
   For households (small n) we find that partition exactly with a bitmask DP;
   for very large groups we fall back to the greedy method (at most n - 1).

Example: A owes B 15, B owes C 15, C owes A 3  ->  A: -12, B: 0, C: +12
         -> a single transfer: A pays C 12.
"""
from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable, Sequence

from domain.money import split_cents

EXACT_LIMIT = 12  # 2^12 subsets: instant; above that use greedy


@dataclass(frozen=True)
class CostShares:
    amount_cents: int
    payers: Sequence[Hashable]
    coverers: Sequence[Hashable]


@dataclass(frozen=True)
class Transfer:
    debtor: Hashable
    creditor: Hashable
    amount_cents: int


@dataclass
class PersonTotals:
    paid: int = 0
    covered: int = 0

    @property
    def net(self) -> int:
        return self.paid - self.covered


def compute_totals(costs: Iterable[CostShares]) -> dict[Hashable, PersonTotals]:
    totals: dict[Hashable, PersonTotals] = defaultdict(PersonTotals)
    for cost in costs:
        if not cost.payers or not cost.coverers:
            continue
        for person, share in zip(cost.payers, split_cents(cost.amount_cents, len(cost.payers))):
            totals[person].paid += share
        for person, share in zip(cost.coverers, split_cents(cost.amount_cents, len(cost.coverers))):
            totals[person].covered += share
    return dict(totals)


def settle(balances: dict[Hashable, int]) -> list[Transfer]:
    """Return the transfers that settle `balances` (which must sum to zero)."""
    items = [(person, amount) for person, amount in balances.items() if amount != 0]
    if sum(amount for _, amount in items) != 0:
        raise ValueError("balances must sum to zero")
    if not items:
        return []

    groups = _zero_sum_groups(items) if len(items) <= EXACT_LIMIT else [items]
    transfers: list[Transfer] = []
    for group in groups:
        transfers.extend(_settle_greedy(group))
    return transfers


def _zero_sum_groups(items: list[tuple[Hashable, int]]) -> list[list[tuple[Hashable, int]]]:
    """Split items into the maximum number of disjoint groups that each sum to zero."""
    n = len(items)
    full = (1 << n) - 1
    values = [amount for _, amount in items]

    sums = [0] * (full + 1)
    for mask in range(1, full + 1):
        low = mask & -mask
        sums[mask] = sums[mask ^ low] + values[low.bit_length() - 1]

    # best[mask] = most zero-sum "prefix closings" when adding the people of mask one by one
    best = [0] * (full + 1)
    for mask in range(1, full + 1):
        top = 0
        bits = mask
        while bits:
            low = bits & -bits
            candidate = best[mask ^ low]
            if candidate > top:
                top = candidate
            bits ^= low
        best[mask] = top + (1 if sums[mask] == 0 else 0)

    # Walk back to recover the order people were added in.
    order: list[int] = []
    mask = full
    while mask:
        target = best[mask] - (1 if sums[mask] == 0 else 0)
        bits = mask
        while bits:
            low = bits & -bits
            if best[mask ^ low] == target:
                order.append(low.bit_length() - 1)
                mask ^= low
                break
            bits ^= low
    order.reverse()

    # Cut the sequence every time the running total returns to zero.
    groups: list[list[tuple[Hashable, int]]] = []
    current: list[tuple[Hashable, int]] = []
    running = 0
    for index in order:
        current.append(items[index])
        running += values[index]
        if running == 0:
            groups.append(current)
            current = []
    if current:  # cannot happen when the total is zero, kept for safety
        groups.append(current)
    return groups


def _settle_greedy(group: list[tuple[Hashable, int]]) -> list[Transfer]:
    """Largest debtor pays largest creditor until everyone is even (k - 1 transfers max)."""
    debtors = [[person, -amount] for person, amount in group if amount < 0]
    creditors = [[person, amount] for person, amount in group if amount > 0]
    transfers: list[Transfer] = []
    while debtors and creditors:
        debtors.sort(key=lambda entry: -entry[1])
        creditors.sort(key=lambda entry: -entry[1])
        debtor, creditor = debtors[0], creditors[0]
        amount = min(debtor[1], creditor[1])
        transfers.append(Transfer(debtor=debtor[0], creditor=creditor[0], amount_cents=amount))
        debtor[1] -= amount
        creditor[1] -= amount
        if debtor[1] == 0:
            debtors.pop(0)
        if creditor[1] == 0:
            creditors.pop(0)
    return transfers
