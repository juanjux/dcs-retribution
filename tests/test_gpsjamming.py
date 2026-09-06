"""GPS jamming: which units deny GPS, how far, and which weapons care.

The mechanism itself lives in the Lua plugin; what is testable here is the campaign
side -- that a unit becomes a jammer by declaring a block and by nothing else, that the
bubble falls back to the campaign setting, and that only satellite-guided stores are on
the list.
"""

from __future__ import annotations

from game.dcs.groundunittype import GpsJammingProperties
from game.gpsjamming import GPS_GUIDED_WEAPON_PATTERNS


def test_declaring_no_block_is_not_a_jammer() -> None:
    """The overwhelmingly common case: every other ground unit in the game."""
    assert GpsJammingProperties.from_data(None) is None
    assert GpsJammingProperties.from_data(False) is None


def test_a_bare_block_rides_the_campaign_defaults() -> None:
    """`gps_jamming: true` must be enough -- tuning is optional."""
    props = GpsJammingProperties.from_data(True)
    assert props == GpsJammingProperties(radius_nm=None, miss_radius_m=None)


def test_the_block_carries_its_own_reach_and_miss() -> None:
    props = GpsJammingProperties.from_data({"radius_nm": 15, "miss_radius_m": 250})
    assert props is not None
    assert props.radius_nm == 15.0
    assert props.miss_radius_m == 250.0


def test_a_malformed_value_falls_back_rather_than_raising() -> None:
    """A typo in a unit yaml must not take the whole unit registry down."""
    props = GpsJammingProperties.from_data({"radius_nm": "fifteen"})
    assert props is not None
    assert props.radius_nm is None


def test_only_satellite_guided_weapons_are_degraded() -> None:
    """A Paveway that mysteriously misses is a bug report, not a feature: laser, TV,
    IR and anti-radiation weapons must never be on this list."""
    patterns = [p.upper() for p in GPS_GUIDED_WEAPON_PATTERNS]
    assert any("GBU-31" in p for p in patterns), "JDAM must be covered"
    for never in ("GBU-12", "AGM-65", "AGM-88", "AGM-114", "GBU-16", "GBU-10"):
        assert not any(never in p for p in patterns), f"{never} is not GPS-guided"


def test_the_declared_jammers_carry_a_bubble() -> None:
    """The two DCS GPS spoofer vehicles are what the fork ships as jammers."""
    from game.dcs.groundunittype import GroundUnitType

    for name in ("EW Radio Jammer (Red)", "EW Radio Jammer (Blue)"):
        unit = GroundUnitType.named(name)
        assert unit.gps_jamming is not None, f"{name} should be a jammer"
        assert unit.gps_jamming.radius_nm == 15.0
