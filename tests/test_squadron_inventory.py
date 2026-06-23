"""Regression tests for squadron aircraft inventory accounting.

The bug these pin: ``return_all_pilots_and_aircraft`` (run on every turn
re-initialisation via ``AirWing.reset``) used to reset ``untasked_aircraft`` to
``owned_aircraft``, ignoring ``pending_deliveries``. After selling aircraft
(which decrements both ``untasked_aircraft`` and ``pending_deliveries``), a
re-initialisation therefore made the just-sold aircraft taskable -- and
sellable -- again, letting the player refund their price repeatedly and driving
``owned_aircraft`` negative once ``deliver_orders`` applied the accumulated
negative ``pending_deliveries`` at end of turn.
"""

from game.squadrons.squadron import Squadron


def _bare_squadron(owned: int, untasked: int, pending: int) -> Squadron:
    sq = Squadron.__new__(Squadron)
    sq.current_roster = []  # active_pilots reads this; empty is fine here
    sq.owned_aircraft = owned
    sq.untasked_aircraft = untasked
    sq.pending_deliveries = pending
    return sq


def test_reset_keeps_sold_aircraft_out_of_the_pool() -> None:
    # Sold 3 of 5 this turn: untasked already down to 2, pending == -3.
    sq = _bare_squadron(owned=5, untasked=2, pending=-3)
    sq.return_all_pilots_and_aircraft()
    assert sq.untasked_aircraft == 2


def test_reset_restores_full_pool_when_nothing_sold() -> None:
    sq = _bare_squadron(owned=5, untasked=0, pending=0)
    sq.return_all_pilots_and_aircraft()
    assert sq.untasked_aircraft == 5


def test_pending_purchases_do_not_inflate_the_pool() -> None:
    # Bought 4 (pending == +4), not yet delivered: only the owned 5 fly now.
    sq = _bare_squadron(owned=5, untasked=0, pending=4)
    sq.return_all_pilots_and_aircraft()
    assert sq.untasked_aircraft == 5
