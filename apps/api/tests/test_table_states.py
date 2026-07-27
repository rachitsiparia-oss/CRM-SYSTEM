from app.reservations.tables import is_table_transition_allowed


def test_normal_turnover_cycle() -> None:
    assert is_table_transition_allowed("available", "reserved")
    assert is_table_transition_allowed("reserved", "occupied")
    assert is_table_transition_allowed("occupied", "cleaning")
    assert is_table_transition_allowed("cleaning", "available")


def test_direct_available_to_occupied_for_walk_ins() -> None:
    assert is_table_transition_allowed("available", "occupied")


def test_blocking_and_maintenance_reachable_from_normal_states() -> None:
    assert is_table_transition_allowed("available", "blocked")
    assert is_table_transition_allowed("available", "maintenance")
    assert is_table_transition_allowed("occupied", "blocked")
    assert is_table_transition_allowed("cleaning", "maintenance")
    assert is_table_transition_allowed("blocked", "maintenance")
    assert is_table_transition_allowed("blocked", "available")
    assert is_table_transition_allowed("maintenance", "available")


def test_merged_is_unreachable_through_the_generic_transition() -> None:
    for state in (
        "available",
        "reserved",
        "occupied",
        "cleaning",
        "blocked",
        "maintenance",
    ):
        assert not is_table_transition_allowed(state, "merged")


def test_merged_has_no_outbound_transitions_either() -> None:
    for target in (
        "available",
        "reserved",
        "occupied",
        "cleaning",
        "blocked",
        "maintenance",
        "merged",
    ):
        assert not is_table_transition_allowed("merged", target)


def test_unknown_status_has_no_transitions() -> None:
    assert not is_table_transition_allowed("nonexistent", "available")
