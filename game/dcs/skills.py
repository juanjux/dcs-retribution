"""The Cadet AI skill, which DCS has and pydcs does not.

The mission editor offers five skills for aircraft -- Cadet, Rookie, Trained, Veteran
and Ace -- and writes them into the .miz as ``Cadet``, ``Average``, ``Good``, ``High``
and ``Excellent`` (see ``MissionEditor/modules/me_crutches.lua``, where the display
names and the ids are two parallel lists). pydcs' ``Skill`` enum starts at ``Average``,
so the bottom rung had no way of reaching a mission file.

A unit serialises its skill as ``self.skill.value``, so a member carrying the literal
string is the whole of what the engine needs. ``Cadet`` appears in no script outside the
editor, so whether the AI actually flies differently at that setting is a question for a
test flight, not for the files.
"""

from dcs.unit import Skill

CADET = "Cadet"


def inject_cadet_skill() -> Skill:
    """Add ``Skill.Cadet`` to pydcs' enum, or return it if already present."""
    existing = Skill._value2member_map_.get(CADET)
    if isinstance(existing, Skill):
        return existing

    member = object.__new__(Skill)
    member._name_ = CADET
    member._value_ = CADET
    Skill._member_map_[CADET] = member
    Skill._value2member_map_[CADET] = member
    Skill._member_names_.append(CADET)
    return member


CADET_SKILL = inject_cadet_skill()


# The five AI rungs in ascending order of competence, which is also the promotion
# ladder: the mission editor labels them Cadet, Rookie, Trained, Veteran and Ace.
SKILL_LADDER: tuple[Skill, ...] = (
    CADET_SKILL,
    Skill.Average,
    Skill.Good,
    Skill.High,
    Skill.Excellent,
)
