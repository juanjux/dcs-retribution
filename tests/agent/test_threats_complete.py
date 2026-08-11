"""``threats`` must list every umbrella, not the strongest few.

It was capped at the top 12. GeneraLLM reported an intact Hawk battery (FAWN, 24 nm,
six launchers, undamaged) missing from the list, and it was right to call that a serious
intel bug: on that campaign 54 sites qualified, 42 were dropped, and the cut fell inside
a nine-way tie at 24 nm — BEAR was listed, eight identical batteries were not.

The planner is instructed to route around ``threats``. A list that quietly ends reads as
"these are all the bubbles", so the omitted ones get flown through.
"""

from __future__ import annotations

from game.agent.views import TargetView, build_threats


def _sam(name: str, nm: int | None, kind: str = "sam") -> TargetView:
    return TargetView(
        id=f"id-{name}",
        name=name,
        kind=kind,
        suggested_task="DEAD",
        pos=[0.0, 0.0],
        threat_nm=nm,
    )


def test_no_cap() -> None:
    targets = [_sam(f"site{i}", 50 - i) for i in range(40)]
    assert len(build_threats(targets)) == 40


def test_a_tie_is_never_cut_in_half() -> None:
    """The failure GeneraLLM hit: nine batteries at 24 nm, one listed, eight dropped."""
    targets = [_sam(f"long{i}", 53) for i in range(12)] + [
        _sam(f"tied{i}", 24) for i in range(9)
    ]
    listed = {t.name for t in build_threats(targets)}
    assert {f"tied{i}" for i in range(9)} <= listed


def test_ranked_by_reach_descending() -> None:
    threats = build_threats([_sam("small", 8), _sam("huge", 80), _sam("mid", 24)])
    assert [t.name for t in threats] == ["huge", "mid", "small"]


def test_only_umbrellas_with_reach_left() -> None:
    """A site with no threat range projects nothing; a building is not an umbrella."""
    targets = [
        _sam("alive", 24),
        _sam("burnt", 0),
        _sam("unknown", None),
        _sam("depot", 40, kind="building"),
        _sam("frigate", 80, kind="ship"),
    ]
    assert [t.name for t in build_threats(targets)] == ["frigate", "alive"]
