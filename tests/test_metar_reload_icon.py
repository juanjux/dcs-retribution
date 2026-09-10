"""The METAR refresh button draws an icon, so the icon has to be there.

It used to be the text glyph U+27F3, which fell back to whatever font had it: wrong
weight, and off the button's centre. A drawn icon fixes that and introduces a new way
to fail -- a missing file paints nothing at all, and an empty button looks like a bug
rather than a missing asset.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qt_ui.widgets.conditions.QWeatherWidget import BUTTON_PX, ICON_PX

MISC = Path(__file__).resolve().parent.parent / "resources/ui/misc"


@pytest.mark.parametrize("theme", sorted(p.name for p in MISC.iterdir() if p.is_dir()))
def test_every_theme_has_the_reload_icon(theme: str) -> None:
    icon = MISC / theme / "reload.png"
    assert icon.is_file(), f"{theme} has no reload.png"
    assert icon.stat().st_size > 0


def test_the_icon_is_inset_in_the_button() -> None:
    """A button that is all icon reads as a glyph again."""
    assert ICON_PX < BUTTON_PX
