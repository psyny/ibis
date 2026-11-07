"""Who pays whom for a list of costs. Shared by the month summary and the month-closed notifications."""
from typing import Iterable

from domain.money import to_cents
from domain.settlement import CostShares, compute_totals, settle
from models.cost import Cost
from services.member_service import sort_members


def split_costs(costs: Iterable[Cost]):
    """Returns (per-member totals, fewest transfers) for these costs."""
    totals = compute_totals(
        CostShares(
            amount_cents=to_cents(cost.amount),
            payers=[m.id for m in sort_members(cost.payers)],
            coverers=[m.id for m in sort_members(cost.coverers)],
        )
        for cost in costs
    )
    return totals, settle({member_id: t.net for member_id, t in totals.items()})
