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


def ground_skill(skill: Skill) -> Skill:
    """Clamp a skill to something a ground unit understands.

    The editor keeps two lists: aircraft get Cadet through Ace, everything else starts
    at ``Average``. The blue coalition shares one setting between its pilots and its
    vehicles, so a coalition set to Cadet would otherwise write a skill onto tanks that
    no ground unit has.
    """
    return Skill.Average if skill is CADET_SKILL else skill


# Experience needed to reach each rung, in the same order as SKILL_LADDER. A pilot flies
# at the highest rung whose threshold he has passed. The steps double, so the climb out of
# cadet is a couple of good sorties and the last one is a campaign.
SKILL_XP_THRESHOLDS: tuple[int, ...] = (0, 1000, 2000, 4000, 8000)


def skill_for_experience(xp: int, floor: Skill = Skill.Average) -> Skill:
    """The rung ``xp`` has earned, never below ``floor``.

    The coalition's skill setting is a floor rather than a starting point: raising the
    difficulty lifts everyone at once, and a veteran is never demoted by it.
    """
    earned = 0
    for rung, threshold in enumerate(SKILL_XP_THRESHOLDS):
        if xp >= threshold:
            earned = rung
    try:
        return SKILL_LADDER[max(earned, SKILL_LADDER.index(floor))]
    except ValueError:
        # Random, Player and Client are skills to DCS but not rungs of anything.
        return SKILL_LADDER[earned]


def experience_for_skill(skill: Skill) -> int:
    """The experience a pilot flying at ``skill`` must have. Used when the feature is
    switched on mid-campaign: a veteran keeps his rank and is seeded with its cost."""
    try:
        return SKILL_XP_THRESHOLDS[SKILL_LADDER.index(skill)]
    except ValueError:
        return 0
