"""A preset group's ``hide_on_mfd: true`` YAML must reach the generated
TheaterGroundObject.

The mobile SAM group YAMLs (SA-6/SA-11/SA-17/BUK M3) set ``hide_on_mfd: true`` so
the player must acquire them visually / with a HARM rather than target them off
the F10/MFD datalink. That is only honored if the ForceGroup loader reads the key
and forwards it -- otherwise it is silent config. This pins the loader + forward.
"""

import pytest

from game import persistency
from game.armedforces.forcegroup import ForceGroup


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # ForceGroup/layout preset loading reads from the DCS saved-game folder,
    # which is only configured once the app boots. Point it at an empty temp
    # dir so loading falls back to the bundled resources/ presets.
    persistency.setup(
        str(tmp_path_factory.mktemp("saved_games")),
        prefer_liberation_payloads=False,
        port=16899,
    )


def test_hide_on_mfd_defaults_false() -> None:
    # Explicit opt-in only: a group with no hide_on_mfd key is not hidden.
    assert ForceGroup(name="x", units=[], statics=[]).hide_on_mfd is False


def test_hide_on_mfd_true_loads_from_preset_yaml() -> None:
    # SA-6.yaml sets `hide_on_mfd: true`; the loaded preset ForceGroup must carry
    # it so create_ground_object_for_layout forwards it onto the ground object.
    assert ForceGroup.from_preset_group("SA-6").hide_on_mfd is True
