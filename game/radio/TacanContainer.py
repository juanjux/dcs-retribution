from typing import Optional

from game.radio.tacan import TacanChannel


class TacanContainer:
    tacan: Optional[TacanChannel] = None
    tcn_name: Optional[str] = None
    # True while the channel was picked automatically by the mission
    # generator (or no channel has been set yet); False once the user has
    # explicitly chosen one from the base dialog. Used by the UI to show
    # 'AUTO (94X)' vs '94X (KUT)' so the player can tell at a glance whether
    # they own the choice or whether it may change between turns.
    tacan_is_auto: bool = True
