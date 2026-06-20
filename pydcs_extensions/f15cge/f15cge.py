from dcs import task
from dcs.planes import PlaneType
from dcs.weapons_data import Weapons

from game.modsupport import planemod
from pydcs_extensions.weapon_injector import inject_weapons


class WeaponsF15CGE:
    AIM_9X_2 = {"clsid": "{AIM-9X2}", "name": "AIM-9X-2", "weight": 0}
    AIM_120C_7 = {"clsid": "{F15EX_AIM-120C-7}", "name": "AIM-120C-7", "weight": 0}
    AIM_120C_8 = {"clsid": "{F15EX_AIM-120C-8}", "name": "AIM-120C-8", "weight": 0}
    AIM_120D_3 = {"clsid": "{F15EX_AIM-120D-3}", "name": "AIM-120D-3", "weight": 0}
    AIM_260A = {"clsid": "{AIM-260A}", "name": "AIM-260A", "weight": 0}
    MAKO_A2G_C = {"clsid": "{MAKO_A2G_C}", "name": "MAKO_A2G_C", "weight": 0}
    LegionPod = {"clsid": "{LegionPod}", "name": "LegionPod", "weight": 0}


inject_weapons(WeaponsF15CGE)


@planemod
class F_15CGE(PlaneType):
    id = "F15CGE"
    flyable = True
    height = 5.63
    width = 13.05
    length = 19.43
    fuel_max = 6103
    max_speed = 2655
    chaff = 120
    flare = 120
    charge_total = 240
    chaff_charge_size = 1
    flare_charge_size = 1
    eplrs = True
    category = "Interceptor"
    radio_frequency = 251

    livery_name = "F15CGE"

    pylons = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}

    class Pylon1:
        AIM_9M_Sidewinder_IR_AAM = (1, Weapons.AIM_9M_Sidewinder_IR_AAM)
        AIM_9X_Sidewinder_IR_AAM = (1, Weapons.AIM_9X_Sidewinder_IR_AAM)
        AIM_9X_2 = (1, WeaponsF15CGE.AIM_9X_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            1,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (1, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (1, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (1, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (1, WeaponsF15CGE.AIM_260A)
        AN_ASQ_T50_TCTS_Pod___ACMI_Pod = (1, Weapons.AN_ASQ_T50_TCTS_Pod___ACMI_Pod)

    class Pylon2:
        Fuel_tank_610_gal = (2, Weapons.Fuel_tank_610_gal)
        MAKO_A2G_C = (2, WeaponsF15CGE.MAKO_A2G_C)

    class Pylon3:
        AIM_9M_Sidewinder_IR_AAM = (3, Weapons.AIM_9M_Sidewinder_IR_AAM)
        AIM_9X_Sidewinder_IR_AAM = (3, Weapons.AIM_9X_Sidewinder_IR_AAM)
        AIM_9X_2 = (3, WeaponsF15CGE.AIM_9X_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            3,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (3, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (3, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (3, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (3, WeaponsF15CGE.AIM_260A)

    class Pylon4:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            4,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (4, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (4, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (4, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (4, WeaponsF15CGE.AIM_260A)

    class Pylon5:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            5,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (5, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (5, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (5, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (5, WeaponsF15CGE.AIM_260A)

    class Pylon6:
        Fuel_tank_610_gal = (6, Weapons.Fuel_tank_610_gal)
        LegionPod = (6, WeaponsF15CGE.LegionPod)
        AN_AAQ_33___Advanced_Targeting_Pod = (
            6,
            Weapons.AN_AAQ_33___Advanced_Targeting_Pod,
        )

    class Pylon7:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            7,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (7, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (7, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (7, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (7, WeaponsF15CGE.AIM_260A)

    class Pylon8:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            8,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (8, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (8, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (8, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (8, WeaponsF15CGE.AIM_260A)

    class Pylon9:
        AIM_9M_Sidewinder_IR_AAM = (9, Weapons.AIM_9M_Sidewinder_IR_AAM)
        AIM_9X_Sidewinder_IR_AAM = (9, Weapons.AIM_9X_Sidewinder_IR_AAM)
        AIM_9X_2 = (9, WeaponsF15CGE.AIM_9X_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            9,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (9, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (9, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (9, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (9, WeaponsF15CGE.AIM_260A)

    class Pylon10:
        Fuel_tank_610_gal = (10, Weapons.Fuel_tank_610_gal)
        MAKO_A2G_C = (10, WeaponsF15CGE.MAKO_A2G_C)

    class Pylon11:
        AIM_9M_Sidewinder_IR_AAM = (11, Weapons.AIM_9M_Sidewinder_IR_AAM)
        AIM_9X_Sidewinder_IR_AAM = (11, Weapons.AIM_9X_Sidewinder_IR_AAM)
        AIM_9X_2 = (11, WeaponsF15CGE.AIM_9X_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            11,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120C_7 = (11, WeaponsF15CGE.AIM_120C_7)
        AIM_120C_8 = (11, WeaponsF15CGE.AIM_120C_8)
        AIM_120D_3 = (11, WeaponsF15CGE.AIM_120D_3)
        AIM_260A = (11, WeaponsF15CGE.AIM_260A)
        AN_ASQ_T50_TCTS_Pod___ACMI_Pod = (11, Weapons.AN_ASQ_T50_TCTS_Pod___ACMI_Pod)

    tasks = [
        task.CAP,
        task.Escort,
        task.FighterSweep,
        task.Intercept,
        task.AFAC,
    ]
    task_default = task.CAP
