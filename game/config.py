# This should probably be much higher, but the AI doesn't rollover their budget
# and isn't smart enough to save to repair a critical runway anyway, so it has
# to be cheap enough to repair with a single turn's income.
RUNWAY_REPAIR_COST = 100

REWARDS = {
    "warehouse": 2,
    "ware": 2,
    "fuel": 2,
    "ammo": 2,
    "farp": 1,
    # TODO: Should generate no cash once they generate units.
    # https://github.com/dcs-liberation/dcs_liberation/issues/1036
    "factory": 2.5,
    "oil": 10,
    "derrick": 8,
    "village": 0.25,
    "allycamp": 0.5,
}

# IADS infrastructure produces no income, so it has no REWARDS entry -- and repair_cost()
# derives the rebuild price from income, which left every comms tower, power station and
# command centre unrepairable for the rest of the campaign once it was bombed. A network
# you can only ever dismantle is not one worth attacking twice. Price them directly
# instead: rebuildable, still earning nothing.
IADS_REPAIR_COST = {
    "power": 15.0,
    "commandcenter": 10.0,
    "comms": 5.0,
}
