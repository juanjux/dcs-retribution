"""Minimum engagement ranges for the launchers that arm missile sites.

pydcs exposes ``threat_range`` but not the minimum, and several of these launchers have
one that nothing in Retribution has ever respected: a DF-21D battery cannot engage
anything inside 300 km, an ATACMS or Iskander battery nothing inside 75. Tasked at a
closer target they fire anyway and the rounds go nowhere.

Values are the ``ThreatRangeMin`` each unit declares in its own mod files. A launcher
with no entry has no minimum -- the Scud is the common case, and the reason a Scud site
lands its rounds somewhere near the target while an ATACMS site does not.
"""

MISSILE_SITE_MIN_RANGE_M: dict[str, int] = {
    "CH_M270A1_ATACMS": 75000,
    "CHAP_9K720_HE": 75000,
    "CHAP_9K720_Cluster": 75000,
    "CH_DF21D": 300000,
    "CH_CJ10": 20000,
    "CH_IskanderK": 20000,
    "CH_YJ12B": 10000,
}
