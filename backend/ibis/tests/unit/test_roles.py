from domain.months import auto_close_date, clamp_day
from domain.roles import Role, has_role, is_participant, member_sort_key


def test_role_hierarchy():
    assert has_role(Role.MANAGER, Role.RESIDENT)
    assert has_role(Role.RESIDENT, Role.GUEST)
    assert has_role(Role.GUEST, Role.VIEWER)
    assert not has_role(Role.VIEWER, Role.GUEST)
    assert not has_role(Role.GUEST, Role.RESIDENT)
    assert not has_role("resident", "manager")


def test_participants():
    assert is_participant(Role.GUEST)
    assert not is_participant(Role.VIEWER)


def test_member_order_residents_first_then_guests():
    people = [
        ("guest", "alice"),
        ("resident", "Zoe"),
        ("manager", "bob"),
        ("viewer", "Aaron"),
        ("guest", "Carl"),
    ]
    ordered = [name for role, name in sorted(people, key=lambda p: member_sort_key(*p))]
    assert ordered == ["bob", "Zoe", "alice", "Carl", "Aaron"]


def test_month_helpers():
    assert clamp_day(2026, 2, 31).day == 28
    assert auto_close_date(2026, 1, 5).isoformat() == "2026-02-06"
    assert auto_close_date(2026, 1, None) is None
