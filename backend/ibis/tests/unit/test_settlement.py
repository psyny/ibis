import random
from functools import lru_cache

import pytest

from domain.money import split_cents, to_cents
from domain.settlement import CostShares, compute_totals, settle


def apply(balances: dict, transfers) -> dict:
    result = dict(balances)
    for t in transfers:
        result[t.debtor] += t.amount_cents
        result[t.creditor] -= t.amount_cents
    return result


def brute_force_min_transfers(values: tuple[int, ...]) -> int:
    """n - (max number of disjoint zero-sum groups), by exhaustive search."""
    values = tuple(v for v in values if v != 0)
    n = len(values)

    @lru_cache(maxsize=None)
    def max_groups(mask: int) -> int:
        if mask == 0:
            return 0
        first = (mask & -mask).bit_length() - 1
        rest = mask & ~(1 << first)
        best = 0
        sub = rest
        while True:
            group = sub | (1 << first)
            if sum(values[i] for i in range(n) if group >> i & 1) == 0:
                best = max(best, 1 + max_groups(mask & ~group))
            if sub == 0:
                break
            sub = (sub - 1) & rest
        return best

    return n - max_groups((1 << n) - 1)


def test_example_from_spec():
    # A owes B 15, B owes C 15, C owes A 3  ->  A pays C 12
    costs = [
        CostShares(1500, payers=["B"], coverers=["A"]),
        CostShares(1500, payers=["C"], coverers=["B"]),
        CostShares(300, payers=["A"], coverers=["C"]),
    ]
    totals = compute_totals(costs)
    transfers = settle({p: t.net for p, t in totals.items()})
    assert len(transfers) == 1
    assert (transfers[0].debtor, transfers[0].creditor, transfers[0].amount_cents) == ("A", "C", 1200)


def test_equal_split_between_multiple_payers_and_coverers():
    totals = compute_totals([CostShares(9000, payers=["A", "B"], coverers=["A", "B", "C"])])
    assert totals["A"].paid == 4500 and totals["A"].covered == 3000
    assert totals["C"].net == -3000
    assert sum(t.net for t in totals.values()) == 0


def test_rounding_never_loses_cents():
    assert split_cents(1000, 3) == [334, 333, 333]
    assert sum(split_cents(1, 7)) == 1
    totals = compute_totals([CostShares(1000, payers=["A"], coverers=["A", "B", "C"])])
    assert sum(t.net for t in totals.values()) == 0


def test_to_cents():
    assert to_cents("10.005") == 1001
    assert to_cents(12.3) == 1230


def test_no_costs_no_transfers():
    assert settle({}) == []
    assert settle({"A": 0, "B": 0}) == []


def test_unbalanced_input_raises():
    with pytest.raises(ValueError):
        settle({"A": 10, "B": -5})


def test_prefers_independent_pairs():
    # Plain greedy (largest first) needs 4 transfers here; splitting into
    # {A, D, E} and {B, C} needs only 3.
    balances = {"A": 500, "B": 400, "C": -400, "D": -300, "E": -200}
    transfers = settle(balances)
    assert len(transfers) == 3
    assert all(v == 0 for v in apply(balances, transfers).values())


@pytest.mark.parametrize("seed", range(150))
def test_random_balances_are_settled_optimally(seed):
    rng = random.Random(seed)
    people = [f"P{i}" for i in range(rng.randint(2, 8))]
    costs = []
    for _ in range(rng.randint(1, 10)):
        payers = rng.sample(people, rng.randint(1, 2))
        coverers = rng.sample(people, rng.randint(1, len(people)))
        costs.append(CostShares(rng.choice([500, 1000, 1500, 2000, 3333]), payers, coverers))
    balances = {p: t.net for p, t in compute_totals(costs).items()}

    transfers = settle(balances)

    assert all(v == 0 for v in apply(balances, transfers).values())
    assert all(t.amount_cents > 0 for t in transfers)
    assert len(transfers) == brute_force_min_transfers(tuple(balances.values()))


def test_large_groups_fall_back_to_greedy():
    balances = {f"P{i}": (100 if i % 2 else -100) for i in range(30)}
    transfers = settle(balances)
    assert all(v == 0 for v in apply(balances, transfers).values())
    assert len(transfers) <= 29
