from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point

from game.ato.flightplans.capbuilder import (
    MIN_PATROL_ROUTE_LENGTH,
    CapBuilder,
)
from game.utils import Heading, meters


class _Builder(CapBuilder):  # type: ignore[type-arg]
    """CapBuilder is abstract; only the lengthening is under test here."""

    def build(self, dump_debug_info: bool = False) -> Any:
        raise NotImplementedError


def _builder(field: Point) -> Any:
    builder = _Builder.__new__(_Builder)
    at_field = SimpleNamespace(position=field)
    flight: Any = SimpleNamespace(departure=at_field, arrival=at_field)
    builder.flight = flight
    return builder


def _route(field: Point, start: Point, end: Point) -> float:
    return (
        field.distance_to_point(start)
        + start.distance_to_point(end)
        + end.distance_to_point(field)
    )


def _points(terrain: Any) -> tuple[Point, Point, Point]:
    """A CAP guarding its own field, the shape the cold war doctrine can produce.

    The end of the track sits 8 nm north of the field with a 12 nm track, which
    puts the start 4 nm south of it: a 24 nm round trip.
    """
    field = Point(0, 0, terrain)
    end = field.point_from_heading(0, meters(14816).meters)  # 8 nm north
    start = end.point_from_heading(180, meters(22224).meters)  # 12 nm track
    return field, start, end


def test_a_short_patrol_route_is_lengthened(terrain: Any = None) -> None:
    """DCS deletes an air-started flight on spawn if its route is short enough."""
    field, start, end = _points(terrain)
    assert _route(field, start, end) < MIN_PATROL_ROUTE_LENGTH.meters

    new_start, new_end = _builder(field)._lengthened_to_minimum(
        start, end, Heading.from_degrees(0)
    )
    assert _route(field, new_start, new_end) >= MIN_PATROL_ROUTE_LENGTH.meters


def test_the_station_end_does_not_move(terrain: Any = None) -> None:
    """Only the far end is pushed back, so the track never creeps toward the enemy."""
    field, start, end = _points(terrain)
    _, new_end = _builder(field)._lengthened_to_minimum(
        start, end, Heading.from_degrees(0)
    )
    assert new_end == end


def test_a_long_enough_route_is_left_alone(terrain: Any = None) -> None:
    field = Point(0, 0, terrain)
    end = field.point_from_heading(0, meters(74080).meters)  # 40 nm north
    start = end.point_from_heading(180, meters(44448).meters)  # 24 nm track
    assert _route(field, start, end) >= MIN_PATROL_ROUTE_LENGTH.meters

    new_start, new_end = _builder(field)._lengthened_to_minimum(
        start, end, Heading.from_degrees(0)
    )
    assert (new_start, new_end) == (start, end)
