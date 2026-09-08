from dataclasses import dataclass, field
from typing import Any, Callable, Optional

SETTING_DESCRIPTION_KEY = "DCS_LIBERATION_SETTING_DESCRIPTION_KEY"


@dataclass(frozen=True)
class OptionDescription:
    page: str
    section: str
    text: str
    detail: Optional[str]
    tooltip: Optional[str]
    causes_expensive_game_update: bool

    #: When set, the setting is only shown while this returns True for the current
    #: Settings. For options that are meaningless unless another one is set a certain
    #: way: showing them anyway invites the player to configure something that will
    #: quietly do nothing. Keyword-only so it does not disturb the positional fields
    #: each option subclass adds after these.
    visible_when: Optional[Callable[[Any], bool]] = field(default=None, kw_only=True)

    #: A box within the section, for the settings that are a detail of it rather than
    #: a section in their own right. They sit after the section's own rows.
    subsection: Optional[str] = field(default=None, kw_only=True)

    #: This setting owns another section, reached by a gear beside it rather than by
    #: a page of its own -- for the tuning knobs behind a switch, which are noise
    #: until you have gone looking for them.
    opens_section: Optional[str] = field(default=None, kw_only=True)
