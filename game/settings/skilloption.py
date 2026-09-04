from typing import Any, Optional

from .choicesoption import choices_option

# The mission editor keeps two skill lists (MissionEditor/modules/me_crutches.lua):
# aircraft get a fifth rung below Average, displayed as Cadet, and everything else
# starts at Average. Offering Cadet for vehicles would write a skill no ground unit
# has, so the two lists stay apart here as well.
GROUND_SKILL_CHOICES = ["Average", "Good", "High", "Excellent"]
PILOT_SKILL_CHOICES = ["Cadet"] + GROUND_SKILL_CHOICES


def skill_option(
    text: str,
    page: str,
    section: str,
    default: str,
    detail: Optional[str] = None,
    tooltip: Optional[str] = None,
    **kwargs: Any,
) -> str:
    return choices_option(
        text,
        page,
        section,
        default,
        GROUND_SKILL_CHOICES,
        detail=detail,
        tooltip=tooltip,
        **kwargs,
    )


def pilot_skill_option(
    text: str,
    page: str,
    section: str,
    default: str,
    detail: Optional[str] = None,
    tooltip: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """A skill setting that also offers Cadet, the bottom rung only aircraft have."""
    return choices_option(
        text,
        page,
        section,
        default,
        PILOT_SKILL_CHOICES,
        detail=detail,
        tooltip=tooltip,
        **kwargs,
    )
