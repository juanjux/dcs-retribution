"""What Skynet will do with each site, worked out before the mission runs.

The state a site ends up in -- part of the network, on its own, or switched off -- is
decided inside DCS and never comes back out. It is not guesswork, though: Skynet reaches
it from things Retribution already knows, so the same answer can be reached here.

The rules below are lifted from the plugin, function by function:

* ``goLive`` refuses outright unless ``hasWorkingPowerSource()``, so a site with no
  power is dark whatever else is true of it.
* ``genericCheckOneObjectIsAlive`` starts at ``#objects == 0``, so a site with no power
  or comms dependency at all counts as having both. That is why a battery with its own
  generator is left without a power dependency rather than given a dead one.
* ``setToCorrectAutonomousState`` keeps a SAM in the network only while its own comms
  are up, the coalition still has a usable command centre, and at least one parent radar
  that covers it is itself alive, powered and connected.
* ``buildRadarCoverage`` makes that parent relationship by range: an early-warning radar
  is the parent of every SAM inside its detection range.

What cannot be known from here is written down rather than guessed at: ammunition, HARM
silence, and anything that happens once the mission is running. This is the state the
site will be in when the mission starts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Iterator, Optional

from game.theater.iadsnetwork.iadsrole import IadsRole

if TYPE_CHECKING:
    from game.theater.iadsnetwork.iadsnetwork import IadsNetwork, IadsNetworkNode
    from game.theater.theatergroundobject import TheaterGroundObject
    from game.theater.theatergroup import IadsGroundGroup


#: Skynet's own name for "go autonomous and stay switched off". No stock unit asks for
#: it, but a mod can, and then losing the network switches the site off rather than
#: setting it loose.
AUTONOMOUS_STATE_DARK = "SkynetIADSAbstractRadarElement.AUTONOMOUS_STATE_DARK"


class IadsState(Enum):
    #: Fed by an early-warning radar and under a command centre. It holds its fire
    #: until the network hands it a target, and that is when it is most dangerous.
    NETWORKED = "networked"

    #: Cut off from the network but still powered. It fights on whatever its own radar
    #: can see, which is a good deal less than the network was giving it.
    AUTONOMOUS = "autonomous"

    #: Switched off. Skynet will not bring the radar up, so the site is silent for the
    #: whole mission unless it is repaired first.
    DARK = "dark"


@dataclass(frozen=True)
class IadsStatus:
    state: IadsState

    #: Why, in a line, ready to put in a tooltip or hand to a planner.
    reason: str

    #: Nothing left that can find a target for itself. A networked site can still be
    #: handed one; an autonomous one has nothing to look with.
    blind: bool

    @property
    def notable(self) -> bool:
        """Worth saying out loud: anything but a site working as designed."""
        return self.state is not IadsState.NETWORKED or self.blind


def _brings_its_own_power(group: IadsGroundGroup) -> bool:
    from game.theater.iadsnetwork.iadsnetwork import brings_its_own_power

    return brings_its_own_power(group)


def _detection_range(group: IadsGroundGroup) -> float:
    """Metres this site can see for itself.

    Asked of the range rather than of a list of radar classes, because the classes
    answer the wrong question: a HAWK whose AN/MPQ-50 is rubble still has an MPQ-46
    with 90 km on it, and a NASAMS that has lost its MPQ-64 has launchers and a
    command post and sees nothing. TheaterUnit.detection_range is already zero for a
    wreck, so this counts only what is standing.
    """
    return max((unit.detection_range.meters for unit in group.units), default=0.0)


def _goes_dark_when_autonomous(group: IadsGroundGroup) -> bool:
    for unit in group.units:
        if unit.unit_type is None:
            continue
        properties = getattr(unit.unit_type, "skynet_properties", None)
        if properties is None:
            continue
        if getattr(properties, "autonomous_behaviour", None) == AUTONOMOUS_STATE_DARK:
            return True
    return False


class IadsStateMap:
    """The state of every site in one network, worked out in one pass."""

    def __init__(self, network: IadsNetwork) -> None:
        self._by_tgo: dict[TheaterGroundObject, IadsStatus] = {}
        self._build(network)

    def status_for(self, tgo: TheaterGroundObject) -> Optional[IadsStatus]:
        """The site's state, or None if it is not part of an IADS at all."""
        return self._by_tgo.get(tgo)

    def __iter__(self) -> Iterator[tuple[TheaterGroundObject, IadsStatus]]:
        return iter(self._by_tgo.items())

    # ---------------------------------------------------------------- internals

    @staticmethod
    def _powered(node: IadsNetworkNode) -> bool:
        if _brings_its_own_power(node.group):
            return True
        sources = [
            group
            for group in node.connections.values()
            if group.iads_role is IadsRole.POWER_SOURCE
        ]
        return not sources or any(group.alive_units > 0 for group in sources)

    @staticmethod
    def _connected(node: IadsNetworkNode) -> bool:
        comms = [
            group
            for group in node.connections.values()
            if group.iads_role is IadsRole.CONNECTION_NODE
        ]
        return not comms or any(group.alive_units > 0 for group in comms)

    def _build(self, network: IadsNetwork) -> None:
        by_side: dict[bool, list[IadsNetworkNode]] = {}
        for node in network.nodes:
            side = node.group.ground_object.control_point.captured.is_blue
            by_side.setdefault(side, []).append(node)
        for nodes in by_side.values():
            self._build_side(nodes)

    def _build_side(self, nodes: list[IadsNetworkNode]) -> None:
        powered = {id(node): self._powered(node) for node in nodes}
        connected = {id(node): self._connected(node) for node in nodes}

        command_centres = [
            node for node in nodes if node.group.iads_role is IadsRole.COMMAND_CENTER
        ]
        # No command centre at all reads as "command is fine": an empty table is what
        # isCommandCenterUsable() answers true to.
        has_command = not command_centres or any(
            node.group.alive_units > 0 and powered[id(node)] and connected[id(node)]
            for node in command_centres
        )

        parents = [
            node
            for node in nodes
            if node.group.iads_role in (IadsRole.EWR, IadsRole.SAM_AS_EWR)
            and node.group.alive_units > 0
            and powered[id(node)]
            and connected[id(node)]
        ]

        for node in nodes:
            if node.group.iads_role in (
                IadsRole.CONNECTION_NODE,
                IadsRole.POWER_SOURCE,
            ):
                # Infrastructure. It has no radar to switch on or off.
                continue
            self._by_tgo[node.group.ground_object] = self._status_for_node(
                node, powered[id(node)], connected[id(node)], has_command, parents
            )

    def _status_for_node(
        self,
        node: IadsNetworkNode,
        powered: bool,
        connected: bool,
        has_command: bool,
        parents: list[IadsNetworkNode],
    ) -> IadsStatus:
        role = node.group.iads_role
        # A command centre is a building. It never had a radar, so having none is not
        # news about it.
        blind = (
            role is not IadsRole.COMMAND_CENTER and _detection_range(node.group) <= 0
        )

        if node.group.alive_units == 0:
            return IadsStatus(IadsState.DARK, "Destroyed.", blind)

        if not powered:
            # Skynet's goLive() refuses outright without power, so this is the one
            # answer that needs nothing else asked about the site.
            consequence = (
                "so it directs nobody"
                if role is IadsRole.COMMAND_CENTER
                else "so the radar never comes up"
            )
            return IadsStatus(
                IadsState.DARK,
                "No power: its substation is down and it carries no generator, "
                f"{consequence}.",
                blind,
            )

        if role is IadsRole.COMMAND_CENTER:
            return IadsStatus(IadsState.NETWORKED, "Directing the network.", blind)

        if role is IadsRole.EWR:
            if not connected:
                return IadsStatus(
                    IadsState.AUTONOMOUS,
                    "Comms cut: it still sees, but what it sees reaches nobody.",
                    blind,
                )
            return IadsStatus(IadsState.NETWORKED, "Feeding the network.", blind)

        # A SAM, or a SAM standing in for an early-warning radar.
        if not connected:
            reason = "Comms cut: nothing reaches it from the network."
        elif not has_command:
            reason = "No command centre left standing to direct it."
        else:
            covering = sorted(
                self._name(parent)
                for parent in parents
                if parent is not node and self._covers(parent, node)
            )
            if covering:
                return IadsStatus(
                    IadsState.NETWORKED, f"Cued by {', '.join(covering)}.", blind
                )
            reason = "No early-warning radar covers it any more."

        if _goes_dark_when_autonomous(node.group):
            return IadsStatus(
                IadsState.DARK,
                f"{reason} Set to stay dark when it loses the network.",
                blind,
            )
        if blind:
            return IadsStatus(
                IadsState.AUTONOMOUS,
                f"{reason} Its own search radar is gone, so it has nothing to look "
                "with.",
                blind,
            )
        return IadsStatus(
            IadsState.AUTONOMOUS, f"{reason} Fighting on its own radar.", blind
        )

    @staticmethod
    def _name(node: IadsNetworkNode) -> str:
        return node.group.ground_object.name

    @staticmethod
    def _covers(parent: IadsNetworkNode, child: IadsNetworkNode) -> bool:
        reach = _detection_range(parent.group)
        if reach <= 0:
            return False
        return reach >= parent.group.ground_object.position.distance_to_point(
            child.group.ground_object.position
        )
