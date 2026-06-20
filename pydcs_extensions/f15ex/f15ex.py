from dcs import task
from dcs.planes import PlaneType
from dcs.weapons_data import Weapons

from game.modsupport import planemod
from pydcs_extensions.weapon_injector import inject_weapons


class WeaponsF15EX:
    AIM_260A_2 = {"clsid": "{F15EX_2xAIM-260A}", "name": "AIM-260A*2", "weight": 0}
    AIM_120D3_2 = {"clsid": "{F15EX_2xAIM-120D-3}", "name": "AIM-120D3*2", "weight": 0}
    AIM_120C8_2 = {"clsid": "{F15EX_2xAIM-120C-8}", "name": "AIM-120C8*2", "weight": 0}
    AIM_120C7_2 = {"clsid": "{F15EX_2xAIM-120C-7}", "name": "AIM-120C7*2", "weight": 0}
    AIM_120C5_2 = {"clsid": "{F15EX_2xAIM-120C-5}", "name": "AIM-120C5*2", "weight": 0}
    AIM_9X2_2 = {"clsid": "{F-15EX_AIM-9X_O}", "name": "AIM-9X2*2", "weight": 0}
    AGM_88F = {"clsid": "{AGM-88F_F15EX}", "name": "AGM-88F", "weight": 0}
    AGM_88G = {"clsid": "{AGM88G_F-15EX}", "name": "AGM-88G", "weight": 0}
    MAKO_2 = {"clsid": "{F-15EX_MAKO_A2G_C}", "name": "MAKO*2", "weight": 0}
    AIM_260A_2_2 = {"clsid": "{LAU_115_2xAIM-260A}", "name": "AIM-260A*2", "weight": 0}
    AIM_120C7_2_2 = {
        "clsid": "{LAU_115_2xAIM-120C-7}",
        "name": "AIM-120C7*2",
        "weight": 0,
    }
    AIM_120C8_2_2 = {
        "clsid": "{F15EX_LAU_115_2xAIM-120C-8}",
        "name": "AIM-120C8*2",
        "weight": 0,
    }
    AIM_120D3_2_2 = {
        "clsid": "{LAU_115_2xAIM-120D-3}",
        "name": "AIM-120D3*2",
        "weight": 0,
    }
    AIM_200_4 = {"clsid": "{AIM200-4XRACK}", "name": "AIM-200*4", "weight": 0}
    APKWS_II_IR_M151_x21 = {
        "clsid": "{APKWS_II_IRx21}",
        "name": "APKWS II-IR M151 x21",
        "weight": 0,
    }
    APKWS_II_IR_M282_x21 = {
        "clsid": "{APKWS_II_IR_x21}",
        "name": "APKWS II-IR M282 x21",
        "weight": 0,
    }
    AGM_88F_2 = {"clsid": "{harmF-15ex}", "name": "AGM-88F", "weight": 0}
    AGM_88G_2 = {"clsid": "{aargm_er}", "name": "AGM-88G", "weight": 0}
    JASSM = {"clsid": "{B21_AGM-158B}", "name": "JASSM", "weight": 0}
    LRASM = {"clsid": "{B21_AGM-158C}", "name": "LRASM", "weight": 0}
    MAKO_A2G_C = {"clsid": "{MAKO_A2G_C}", "name": "MAKO_A2G_C", "weight": 0}
    new = {"clsid": "{BRU_57_MAKO_A2G_C}", "name": "new", "weight": 0}
    MiG_29MU2_ADM_160B = {
        "clsid": "{MiG-29MU2_ADM-160B}",
        "name": "MiG_29MU2_ADM_160B",
        "weight": 0,
    }
    MIG29MU2_JDAM_ER = {
        "clsid": "{MIG29MU2_JDAM-ER}",
        "name": "MIG29MU2_JDAM_ER",
        "weight": 0,
    }
    HB_F4E_BLU_107B_6x = {
        "clsid": "{HB_F4E_BLU-107B_6x}",
        "name": "HB_F4E_BLU_107B_6x",
        "weight": 0,
    }
    JAS39_SDB = {"clsid": "{JAS39_SDB}", "name": "JAS39_SDB", "weight": 0}
    AIM_120C8_2_3 = {
        "clsid": "{F-15EX_AIM-120C8_IN_O}",
        "name": "AIM-120C8*2",
        "weight": 0,
    }
    AIM_120C7_2_3 = {
        "clsid": "{F-15EX_AIM-120C7_IN_O}",
        "name": "AIM-120C7*2",
        "weight": 0,
    }
    AIM_120C5_2_2 = {
        "clsid": "{F-15EX_AIM-120C5_IN_O}",
        "name": "AIM-120C5*2",
        "weight": 0,
    }
    AIM_120D3_2_3 = {
        "clsid": "{F-15EX_AIM-120D3_IN_O}",
        "name": "AIM-120D3*2",
        "weight": 0,
    }
    AIM_260A_2_3 = {
        "clsid": "{F-15EX_AIM-260A_IN_O}",
        "name": "AIM-260A*2",
        "weight": 0,
    }
    AIM_9X_2 = {"clsid": "{F-15EX_AIM-9X_IN_O}", "name": "AIM-9X*2", "weight": 0}
    AIM_120C7 = {"clsid": "{F15EX_AIM-120C-7}", "name": "AIM-120C7", "weight": 0}
    AIM_120D = {
        "clsid": "{SUPERHORNET_PYLON_07_AM_1X_AIM-120D}",
        "name": "AIM-120D",
        "weight": 0,
    }
    AIM_120C8 = {"clsid": "{F15EX_AIM-120C-8}", "name": "AIM-120C8", "weight": 0}
    AIM_120D3 = {"clsid": "{F15EX_AIM-120D-3}", "name": "AIM-120D3", "weight": 0}
    new_2 = {"clsid": "{AIM-260A}", "name": "new", "weight": 0}
    AIM_120C8_2_4 = {"clsid": "{AMBER_2xAIM120C8}", "name": "AIM-120C8*2", "weight": 0}
    AIM_120C7_2_4 = {"clsid": "{AMBER_2xAIM120C7}", "name": "AIM-120C7*2", "weight": 0}
    AIM_120C5_2_3 = {"clsid": "{AMBER_2xAIM120C5}", "name": "AIM-120C5*2", "weight": 0}
    AIM_120D_2 = {"clsid": "{AMBER_2xAIM120D}", "name": "AIM-120D*2", "weight": 0}
    AIM_120D_2_2 = {"clsid": "{AMBER_2xAIM260A}", "name": "AIM-120D*2", "weight": 0}
    AIM_200_2 = {"clsid": "{AIM200_TANDEM}", "name": "AIM-200*2", "weight": 0}
    AIM_200_2_2 = {"clsid": "{AMBER_2xAIM200}", "name": "AIM-200*2", "weight": 0}
    Mk_82_4 = {"clsid": "{F15_MK82FL}", "name": "Mk-82*4", "weight": 0}
    AIM_200 = {"clsid": "{AIM200_SINGLE}", "name": "AIM-200", "weight": 0}
    LegionPod = {"clsid": "{LegionPod}", "name": "LegionPod", "weight": 0}
    F_15EX_pod = {"clsid": "{F-15EX_pod}", "name": "F_15EX_pod", "weight": 0}
    Mk_82_4_2 = {"clsid": "{F15_MK82FR}", "name": "Mk-82*4", "weight": 0}
    AIM_120C8_2_5 = {
        "clsid": "{F-15EX_AIM-120C8_IN}",
        "name": "AIM-120C8*2",
        "weight": 0,
    }
    AIM_120C7_2_5 = {
        "clsid": "{F-15EX_AIM-120C7_IN}",
        "name": "AIM-120C7*2",
        "weight": 0,
    }
    AIM_120C7_2_6 = {
        "clsid": "{F-15EX_AIM-120C5_IN}",
        "name": "AIM-120C7*2",
        "weight": 0,
    }
    AIM_120D3_2_4 = {
        "clsid": "{F-15EX_AIM-120D3_IN}",
        "name": "AIM-120D3*2",
        "weight": 0,
    }
    AIM_260A_2_4 = {"clsid": "{F-15EX_AIM-260A_IN}", "name": "AIM-260A*2", "weight": 0}
    AIM_9X_2_2 = {"clsid": "{F-15EX_AIM-9X_IN}", "name": "AIM-9X*2", "weight": 0}


inject_weapons(WeaponsF15EX)


@planemod
class F_15EX(PlaneType):
    id = "F15EX"
    flyable = True
    height = 5.6
    width = 13.05
    length = 19.43
    fuel_max = 13455
    max_speed = 2655
    chaff = 120
    flare = 120
    charge_total = 240
    chaff_charge_size = 1
    flare_charge_size = 1
    eplrs = True
    category = "Multirole fighter"
    radio_frequency = 251

    livery_name = "F15EX"

    pylons = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}

    class Pylon1:
        AIM_260A_2 = (1, WeaponsF15EX.AIM_260A_2)
        AIM_120D3_2 = (1, WeaponsF15EX.AIM_120D3_2)
        AIM_120C8_2 = (1, WeaponsF15EX.AIM_120C8_2)
        AIM_120C7_2 = (1, WeaponsF15EX.AIM_120C7_2)
        AIM_120C5_2 = (1, WeaponsF15EX.AIM_120C5_2)
        AIM_9X2_2 = (1, WeaponsF15EX.AIM_9X2_2)
        AGM_88F = (1, WeaponsF15EX.AGM_88F)
        AGM_88G = (1, WeaponsF15EX.AGM_88G)
        MAKO_2 = (1, WeaponsF15EX.MAKO_2)

    class Pylon2:
        Fuel_tank_610_gal_ = (2, Weapons.Fuel_tank_610_gal_)
        Fuel_tank_610_gal__Empty_ = (2, Weapons.Fuel_tank_610_gal__Empty_)
        AIM_260A_2_2 = (2, WeaponsF15EX.AIM_260A_2_2)
        AIM_120C7_2_2 = (2, WeaponsF15EX.AIM_120C7_2_2)
        AIM_120C8_2_2 = (2, WeaponsF15EX.AIM_120C8_2_2)
        AIM_120D3_2_2 = (2, WeaponsF15EX.AIM_120D3_2_2)
        LAU_115_2_LAU_127_AIM_120C = (2, Weapons.LAU_115_2_LAU_127_AIM_120C)
        AIM_200_4 = (2, WeaponsF15EX.AIM_200_4)
        AIM_120B_AMRAAM___Active_Radar_AAM = (
            2,
            Weapons.AIM_120B_AMRAAM___Active_Radar_AAM,
        )
        APKWS_II_IR_M151_x21 = (2, WeaponsF15EX.APKWS_II_IR_M151_x21)
        APKWS_II_IR_M282_x21 = (2, WeaponsF15EX.APKWS_II_IR_M282_x21)
        AGM_88F_2 = (2, WeaponsF15EX.AGM_88F_2)
        AGM_88G_2 = (2, WeaponsF15EX.AGM_88G_2)
        JASSM = (2, WeaponsF15EX.JASSM)
        LRASM = (2, WeaponsF15EX.LRASM)
        AGM_84H_SLAM_ER__Expanded_Response_ = (
            2,
            Weapons.AGM_84H_SLAM_ER__Expanded_Response_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_ = (
            2,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_,
        )
        MAKO_A2G_C = (2, WeaponsF15EX.MAKO_A2G_C)
        new = (2, WeaponsF15EX.new)
        AGM_154A___JSOW_CEB__CBU_type_ = (2, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        BRU_57_with_2_x_AGM_154A___JSOW_CEB__CBU_type_ = (
            2,
            Weapons.BRU_57_with_2_x_AGM_154A___JSOW_CEB__CBU_type_,
        )
        AGM_154B___JSOW_Anti_Armour = (2, Weapons.AGM_154B___JSOW_Anti_Armour)
        BRU_57_with_2_x_AGM_154B___JSOW_Anti_Armour = (
            2,
            Weapons.BRU_57_with_2_x_AGM_154B___JSOW_Anti_Armour,
        )
        AGM_154C___JSOW_Unitary_BROACH = (2, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        BRU_55_with_2_x_AGM_154C___JSOW_Unitary_BROACH = (
            2,
            Weapons.BRU_55_with_2_x_AGM_154C___JSOW_Unitary_BROACH,
        )
        MiG_29MU2_ADM_160B = (2, WeaponsF15EX.MiG_29MU2_ADM_160B)
        MIG29MU2_JDAM_ER = (2, WeaponsF15EX.MIG29MU2_JDAM_ER)
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            2,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        BRU_33_with_2_x_Mk_20_Rockeye___490lbs_CBU__247_x_HEAT_Bomblets = (
            2,
            Weapons.BRU_33_with_2_x_Mk_20_Rockeye___490lbs_CBU__247_x_HEAT_Bomblets,
        )
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            2,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        BRU_42_with_3_x_Mk_20_Rockeye___490lbs_CBUs__247_x_HEAT_Bomblets = (
            2,
            Weapons.BRU_42_with_3_x_Mk_20_Rockeye___490lbs_CBUs__247_x_HEAT_Bomblets,
        )
        Mk_84___2000lb_GP_Bomb_LD = (2, Weapons.Mk_84___2000lb_GP_Bomb_LD)
        Mk_82___500lb_GP_Bomb_LD = (2, Weapons.Mk_82___500lb_GP_Bomb_LD)
        BRU_42_3_x_LAU_68___7_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE = (
            2,
            Weapons.BRU_42_3_x_LAU_68___7_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE,
        )
        BRU_33_2_x_LAU_61___19_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE = (
            2,
            Weapons.BRU_33_2_x_LAU_61___19_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE,
        )
        HB_F4E_BLU_107B_6x = (2, WeaponsF15EX.HB_F4E_BLU_107B_6x)
        BRU_41A_with_6_x_Mk_82___500lb_GP_Bomb_LD = (
            2,
            Weapons.BRU_41A_with_6_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            2,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_55_with_2_x_GBU_32_V_2_B___JDAM__1000lb_GPS_Guided_Bomb = (
            2,
            Weapons.BRU_55_with_2_x_GBU_32_V_2_B___JDAM__1000lb_GPS_Guided_Bomb,
        )
        GBU_24B_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            2,
            Weapons.GBU_24B_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        GBU_27___2000lb_Laser_Guided_Penetrator_Bomb = (
            2,
            Weapons.GBU_27___2000lb_Laser_Guided_Penetrator_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            2,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        JAS39_SDB = (2, WeaponsF15EX.JAS39_SDB)
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            2,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_31_V_4_B___JDAM__2000lb_GPS_Guided_Penetrator_Bomb = (
            2,
            Weapons.GBU_31_V_4_B___JDAM__2000lb_GPS_Guided_Penetrator_Bomb,
        )

    class Pylon3:
        AIM_120C8_2_3 = (3, WeaponsF15EX.AIM_120C8_2_3)
        AIM_120C7_2_3 = (3, WeaponsF15EX.AIM_120C7_2_3)
        AIM_120C5_2_2 = (3, WeaponsF15EX.AIM_120C5_2_2)
        AIM_120D3_2_3 = (3, WeaponsF15EX.AIM_120D3_2_3)
        AIM_260A_2_3 = (3, WeaponsF15EX.AIM_260A_2_3)
        AIM_9X_2 = (3, WeaponsF15EX.AIM_9X_2)

    class Pylon4:
        AIM_120C7 = (4, WeaponsF15EX.AIM_120C7)
        AIM_120D = (4, WeaponsF15EX.AIM_120D)
        AIM_120C8 = (4, WeaponsF15EX.AIM_120C8)
        AIM_120D3 = (4, WeaponsF15EX.AIM_120D3)
        new_2 = (4, WeaponsF15EX.new_2)
        AIM_120C8_2_4 = (4, WeaponsF15EX.AIM_120C8_2_4)
        AIM_120C7_2_4 = (4, WeaponsF15EX.AIM_120C7_2_4)
        AIM_120C5_2_3 = (4, WeaponsF15EX.AIM_120C5_2_3)
        AIM_120D_2 = (4, WeaponsF15EX.AIM_120D_2)
        AIM_120D_2_2 = (4, WeaponsF15EX.AIM_120D_2_2)
        AIM_200_4 = (4, WeaponsF15EX.AIM_200_4)
        AIM_200_2 = (4, WeaponsF15EX.AIM_200_2)
        AIM_200_2_2 = (4, WeaponsF15EX.AIM_200_2_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            4,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120B_AMRAAM___Active_Radar_AAM = (
            4,
            Weapons.AIM_120B_AMRAAM___Active_Radar_AAM,
        )
        MAKO_A2G_C = (4, WeaponsF15EX.MAKO_A2G_C)
        new = (4, WeaponsF15EX.new)
        JASSM = (4, WeaponsF15EX.JASSM)
        LRASM = (4, WeaponsF15EX.LRASM)
        AGM_154A___JSOW_CEB__CBU_type_ = (4, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        AGM_154B___JSOW_Anti_Armour = (4, Weapons.AGM_154B___JSOW_Anti_Armour)
        AGM_154C___JSOW_Unitary_BROACH = (4, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        CBU_97___10_x_SFW_Cluster_Bomb = (4, Weapons.CBU_97___10_x_SFW_Cluster_Bomb)
        CBU_87___202_x_CEM_Cluster_Bomb = (4, Weapons.CBU_87___202_x_CEM_Cluster_Bomb)
        Mk_82_AIR_Ballute___500lb_GP_Bomb_HD = (
            4,
            Weapons.Mk_82_AIR_Ballute___500lb_GP_Bomb_HD,
        )
        Mk_82_4 = (4, WeaponsF15EX.Mk_82_4)
        BLU_107___6 = (4, Weapons.BLU_107___6)
        CBU_87___6 = (4, Weapons.CBU_87___6)
        CBU_97___6 = (4, Weapons.CBU_97___6)
        Mk_20_Rockeye___6 = (4, Weapons.Mk_20_Rockeye___6)
        Mk_82_AIR___6 = (4, Weapons.Mk_82_AIR___6)
        Mk_82___6 = (4, Weapons.Mk_82___6)
        JAS39_SDB = (4, WeaponsF15EX.JAS39_SDB)
        GBU_12___500lb_Laser_Guided_Bomb = (4, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            4,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD = (
            4,
            Weapons.GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD,
        )
        MiG_29MU2_ADM_160B = (4, WeaponsF15EX.MiG_29MU2_ADM_160B)
        MIG29MU2_JDAM_ER = (4, WeaponsF15EX.MIG29MU2_JDAM_ER)
        GBU_12___4 = (4, Weapons.GBU_12___4)
        GBU_38___3 = (4, Weapons.GBU_38___3)
        GBU_54B___3 = (4, Weapons.GBU_54B___3)
        GBU_31_V_1_B___2 = (4, Weapons.GBU_31_V_1_B___2)

    class Pylon5:
        AIM_120C7 = (5, WeaponsF15EX.AIM_120C7)
        AIM_120C8 = (5, WeaponsF15EX.AIM_120C8)
        AIM_120D3 = (5, WeaponsF15EX.AIM_120D3)
        AIM_200 = (5, WeaponsF15EX.AIM_200)
        new_2 = (5, WeaponsF15EX.new_2)
        AIM_120C8_2_4 = (5, WeaponsF15EX.AIM_120C8_2_4)
        AIM_120C7_2_4 = (5, WeaponsF15EX.AIM_120C7_2_4)
        AIM_120D_2 = (5, WeaponsF15EX.AIM_120D_2)
        AIM_120D_2_2 = (5, WeaponsF15EX.AIM_120D_2_2)
        AIM_200_4 = (5, WeaponsF15EX.AIM_200_4)
        AIM_200_2_2 = (5, WeaponsF15EX.AIM_200_2_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            5,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        MAKO_A2G_C = (5, WeaponsF15EX.MAKO_A2G_C)
        new = (5, WeaponsF15EX.new)
        JASSM = (5, WeaponsF15EX.JASSM)
        LRASM = (5, WeaponsF15EX.LRASM)
        AGM_154A___JSOW_CEB__CBU_type_ = (5, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        AGM_154B___JSOW_Anti_Armour = (5, Weapons.AGM_154B___JSOW_Anti_Armour)
        AGM_154C___JSOW_Unitary_BROACH = (5, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        MiG_29MU2_ADM_160B = (5, WeaponsF15EX.MiG_29MU2_ADM_160B)
        MIG29MU2_JDAM_ER = (5, WeaponsF15EX.MIG29MU2_JDAM_ER)
        CBU_97___10_x_SFW_Cluster_Bomb = (5, Weapons.CBU_97___10_x_SFW_Cluster_Bomb)
        CBU_87___202_x_CEM_Cluster_Bomb = (5, Weapons.CBU_87___202_x_CEM_Cluster_Bomb)
        Mk_82_AIR_Ballute___500lb_GP_Bomb_HD = (
            5,
            Weapons.Mk_82_AIR_Ballute___500lb_GP_Bomb_HD,
        )
        Mk_82___500lb_GP_Bomb_LD = (5, Weapons.Mk_82___500lb_GP_Bomb_LD)
        BLU_107_B_Durandal___219kg_Concrete_Piercing_Chute_Retarded_Bomb_w_Booster = (
            5,
            Weapons.BLU_107_B_Durandal___219kg_Concrete_Piercing_Chute_Retarded_Bomb_w_Booster,
        )
        JAS39_SDB = (5, WeaponsF15EX.JAS39_SDB)
        GBU_12___500lb_Laser_Guided_Bomb = (5, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        GBU_39 = (5, Weapons.GBU_39)
        GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD = (
            5,
            Weapons.GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD,
        )
        AN_AAQ_14_LANTIRN_TGT_Pod = (5, Weapons.AN_AAQ_14_LANTIRN_TGT_Pod)
        AN_AAQ_33___Advanced_Targeting_Pod = (
            5,
            Weapons.AN_AAQ_33___Advanced_Targeting_Pod,
        )

    class Pylon6:
        AIM_120C8_2_4 = (6, WeaponsF15EX.AIM_120C8_2_4)
        AIM_120C7_2_4 = (6, WeaponsF15EX.AIM_120C7_2_4)
        AIM_120C5_2_3 = (6, WeaponsF15EX.AIM_120C5_2_3)
        AIM_120D_2 = (6, WeaponsF15EX.AIM_120D_2)
        AIM_120D_2_2 = (6, WeaponsF15EX.AIM_120D_2_2)
        AIM_200_4 = (6, WeaponsF15EX.AIM_200_4)
        AIM_120B_AMRAAM___Active_Radar_AAM = (
            6,
            Weapons.AIM_120B_AMRAAM___Active_Radar_AAM,
        )
        MAKO_A2G_C = (6, WeaponsF15EX.MAKO_A2G_C)
        new = (6, WeaponsF15EX.new)
        AGM_154A___JSOW_CEB__CBU_type_ = (6, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        AGM_154B___JSOW_Anti_Armour = (6, Weapons.AGM_154B___JSOW_Anti_Armour)
        AGM_154C___JSOW_Unitary_BROACH = (6, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        Fuel_tank_610_gal_ = (6, Weapons.Fuel_tank_610_gal_)
        Fuel_tank_610_gal__Empty_ = (6, Weapons.Fuel_tank_610_gal__Empty_)
        LegionPod = (6, WeaponsF15EX.LegionPod)
        AN_AAQ_33___Advanced_Targeting_Pod = (
            6,
            Weapons.AN_AAQ_33___Advanced_Targeting_Pod,
        )
        F_15EX_pod = (6, WeaponsF15EX.F_15EX_pod)
        JAS39_SDB = (6, WeaponsF15EX.JAS39_SDB)

    class Pylon7:
        AIM_120C7 = (7, WeaponsF15EX.AIM_120C7)
        AIM_120D = (7, WeaponsF15EX.AIM_120D)
        AIM_120C8 = (7, WeaponsF15EX.AIM_120C8)
        AIM_120D3 = (7, WeaponsF15EX.AIM_120D3)
        AIM_200 = (7, WeaponsF15EX.AIM_200)
        new_2 = (7, WeaponsF15EX.new_2)
        AIM_120C5_2_3 = (7, WeaponsF15EX.AIM_120C5_2_3)
        AIM_120C7_2_4 = (7, WeaponsF15EX.AIM_120C7_2_4)
        AIM_120C8_2_4 = (7, WeaponsF15EX.AIM_120C8_2_4)
        AIM_120D_2 = (7, WeaponsF15EX.AIM_120D_2)
        AIM_120D_2_2 = (7, WeaponsF15EX.AIM_120D_2_2)
        AIM_200_4 = (7, WeaponsF15EX.AIM_200_4)
        AIM_200_2_2 = (7, WeaponsF15EX.AIM_200_2_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            7,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        MAKO_A2G_C = (7, WeaponsF15EX.MAKO_A2G_C)
        new = (7, WeaponsF15EX.new)
        JASSM = (7, WeaponsF15EX.JASSM)
        LRASM = (7, WeaponsF15EX.LRASM)
        AGM_154A___JSOW_CEB__CBU_type_ = (7, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        AGM_154B___JSOW_Anti_Armour = (7, Weapons.AGM_154B___JSOW_Anti_Armour)
        AGM_154C___JSOW_Unitary_BROACH = (7, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        MiG_29MU2_ADM_160B = (7, WeaponsF15EX.MiG_29MU2_ADM_160B)
        MIG29MU2_JDAM_ER = (7, WeaponsF15EX.MIG29MU2_JDAM_ER)
        CBU_97___10_x_SFW_Cluster_Bomb = (7, Weapons.CBU_97___10_x_SFW_Cluster_Bomb)
        CBU_87___202_x_CEM_Cluster_Bomb = (7, Weapons.CBU_87___202_x_CEM_Cluster_Bomb)
        Mk_82_AIR_Ballute___500lb_GP_Bomb_HD = (
            7,
            Weapons.Mk_82_AIR_Ballute___500lb_GP_Bomb_HD,
        )
        Mk_82___500lb_GP_Bomb_LD = (7, Weapons.Mk_82___500lb_GP_Bomb_LD)
        BLU_107_B_Durandal___219kg_Concrete_Piercing_Chute_Retarded_Bomb_w_Booster = (
            7,
            Weapons.BLU_107_B_Durandal___219kg_Concrete_Piercing_Chute_Retarded_Bomb_w_Booster,
        )
        JAS39_SDB = (7, WeaponsF15EX.JAS39_SDB)
        GBU_12___500lb_Laser_Guided_Bomb = (7, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        GBU_39 = (7, Weapons.GBU_39)
        GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD = (
            7,
            Weapons.GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD,
        )
        AN_AAQ_13_LANTIRN_NAV_POD = (7, Weapons.AN_AAQ_13_LANTIRN_NAV_POD)
        LegionPod = (7, WeaponsF15EX.LegionPod)

    class Pylon8:
        AIM_120C7 = (8, WeaponsF15EX.AIM_120C7)
        AIM_120D = (8, WeaponsF15EX.AIM_120D)
        AIM_120C8 = (8, WeaponsF15EX.AIM_120C8)
        AIM_120D3 = (8, WeaponsF15EX.AIM_120D3)
        new_2 = (8, WeaponsF15EX.new_2)
        AIM_120C5_2_3 = (8, WeaponsF15EX.AIM_120C5_2_3)
        AIM_120C7_2_4 = (8, WeaponsF15EX.AIM_120C7_2_4)
        AIM_120C8_2_4 = (8, WeaponsF15EX.AIM_120C8_2_4)
        AIM_120D_2 = (8, WeaponsF15EX.AIM_120D_2)
        AIM_120D_2_2 = (8, WeaponsF15EX.AIM_120D_2_2)
        AIM_200_2_2 = (8, WeaponsF15EX.AIM_200_2_2)
        AIM_200_4 = (8, WeaponsF15EX.AIM_200_4)
        AIM_200_2 = (8, WeaponsF15EX.AIM_200_2)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            8,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        AIM_120B_AMRAAM___Active_Radar_AAM = (
            8,
            Weapons.AIM_120B_AMRAAM___Active_Radar_AAM,
        )
        MAKO_A2G_C = (8, WeaponsF15EX.MAKO_A2G_C)
        new = (8, WeaponsF15EX.new)
        JASSM = (8, WeaponsF15EX.JASSM)
        LRASM = (8, WeaponsF15EX.LRASM)
        AGM_154A___JSOW_CEB__CBU_type_ = (8, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        AGM_154B___JSOW_Anti_Armour = (8, Weapons.AGM_154B___JSOW_Anti_Armour)
        AGM_154C___JSOW_Unitary_BROACH = (8, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        MiG_29MU2_ADM_160B = (8, WeaponsF15EX.MiG_29MU2_ADM_160B)
        MIG29MU2_JDAM_ER = (8, WeaponsF15EX.MIG29MU2_JDAM_ER)
        CBU_97___10_x_SFW_Cluster_Bomb = (8, Weapons.CBU_97___10_x_SFW_Cluster_Bomb)
        CBU_87___202_x_CEM_Cluster_Bomb = (8, Weapons.CBU_87___202_x_CEM_Cluster_Bomb)
        Mk_82_AIR_Ballute___500lb_GP_Bomb_HD = (
            8,
            Weapons.Mk_82_AIR_Ballute___500lb_GP_Bomb_HD,
        )
        Mk_82_4_2 = (8, WeaponsF15EX.Mk_82_4_2)
        BLU_107___6_ = (8, Weapons.BLU_107___6_)
        CBU_87___6_ = (8, Weapons.CBU_87___6_)
        CBU_97___6_ = (8, Weapons.CBU_97___6_)
        Mk_20_Rockeye___6_ = (8, Weapons.Mk_20_Rockeye___6_)
        Mk_82_AIR___6_ = (8, Weapons.Mk_82_AIR___6_)
        Mk_82___6_ = (8, Weapons.Mk_82___6_)
        JAS39_SDB = (8, WeaponsF15EX.JAS39_SDB)
        GBU_12___500lb_Laser_Guided_Bomb = (8, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        GBU_39 = (8, Weapons.GBU_39)
        GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD = (
            8,
            Weapons.GBU_54_V_1_B___LJDAM__500lb_Laser__GPS_Guided_Bomb_LD,
        )
        GBU_12___4_ = (8, Weapons.GBU_12___4_)
        GBU_38___3_ = (8, Weapons.GBU_38___3_)
        GBU_54B___3_ = (8, Weapons.GBU_54B___3_)
        GBU_31_V_1_B___2_ = (8, Weapons.GBU_31_V_1_B___2_)

    class Pylon9:
        AIM_120C8_2_5 = (9, WeaponsF15EX.AIM_120C8_2_5)
        AIM_120C7_2_5 = (9, WeaponsF15EX.AIM_120C7_2_5)
        AIM_120C7_2_6 = (9, WeaponsF15EX.AIM_120C7_2_6)
        AIM_120D3_2_4 = (9, WeaponsF15EX.AIM_120D3_2_4)
        AIM_260A_2_4 = (9, WeaponsF15EX.AIM_260A_2_4)
        AIM_9X_2_2 = (9, WeaponsF15EX.AIM_9X_2_2)

    class Pylon10:
        Fuel_tank_610_gal_ = (10, Weapons.Fuel_tank_610_gal_)
        Fuel_tank_610_gal__Empty_ = (10, Weapons.Fuel_tank_610_gal__Empty_)
        AIM_260A_2_2 = (10, WeaponsF15EX.AIM_260A_2_2)
        AIM_120C7_2_2 = (10, WeaponsF15EX.AIM_120C7_2_2)
        AIM_120C8_2_2 = (10, WeaponsF15EX.AIM_120C8_2_2)
        AIM_120D3_2_2 = (10, WeaponsF15EX.AIM_120D3_2_2)
        LAU_115_2_LAU_127_AIM_120C = (10, Weapons.LAU_115_2_LAU_127_AIM_120C)
        AIM_200_4 = (10, WeaponsF15EX.AIM_200_4)
        AIM_120B_AMRAAM___Active_Radar_AAM = (
            10,
            Weapons.AIM_120B_AMRAAM___Active_Radar_AAM,
        )
        APKWS_II_IR_M151_x21 = (10, WeaponsF15EX.APKWS_II_IR_M151_x21)
        APKWS_II_IR_M282_x21 = (10, WeaponsF15EX.APKWS_II_IR_M282_x21)
        AGM_88F_2 = (10, WeaponsF15EX.AGM_88F_2)
        AGM_88G_2 = (10, WeaponsF15EX.AGM_88G_2)
        JASSM = (10, WeaponsF15EX.JASSM)
        LRASM = (10, WeaponsF15EX.LRASM)
        AGM_84H_SLAM_ER__Expanded_Response_ = (
            10,
            Weapons.AGM_84H_SLAM_ER__Expanded_Response_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_ = (
            10,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile_,
        )
        MAKO_A2G_C = (10, WeaponsF15EX.MAKO_A2G_C)
        new = (10, WeaponsF15EX.new)
        AGM_154A___JSOW_CEB__CBU_type_ = (10, Weapons.AGM_154A___JSOW_CEB__CBU_type_)
        BRU_57_with_2_x_AGM_154A___JSOW_CEB__CBU_type_ = (
            10,
            Weapons.BRU_57_with_2_x_AGM_154A___JSOW_CEB__CBU_type_,
        )
        AGM_154B___JSOW_Anti_Armour = (10, Weapons.AGM_154B___JSOW_Anti_Armour)
        BRU_57_with_2_x_AGM_154B___JSOW_Anti_Armour = (
            10,
            Weapons.BRU_57_with_2_x_AGM_154B___JSOW_Anti_Armour,
        )
        AGM_154C___JSOW_Unitary_BROACH = (10, Weapons.AGM_154C___JSOW_Unitary_BROACH)
        BRU_55_with_2_x_AGM_154C___JSOW_Unitary_BROACH = (
            10,
            Weapons.BRU_55_with_2_x_AGM_154C___JSOW_Unitary_BROACH,
        )
        MiG_29MU2_ADM_160B = (10, WeaponsF15EX.MiG_29MU2_ADM_160B)
        MIG29MU2_JDAM_ER = (10, WeaponsF15EX.MIG29MU2_JDAM_ER)
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            10,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        BRU_33_with_2_x_Mk_20_Rockeye___490lbs_CBU__247_x_HEAT_Bomblets = (
            10,
            Weapons.BRU_33_with_2_x_Mk_20_Rockeye___490lbs_CBU__247_x_HEAT_Bomblets,
        )
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            10,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        BRU_42_with_3_x_Mk_20_Rockeye___490lbs_CBUs__247_x_HEAT_Bomblets = (
            10,
            Weapons.BRU_42_with_3_x_Mk_20_Rockeye___490lbs_CBUs__247_x_HEAT_Bomblets,
        )
        Mk_84___2000lb_GP_Bomb_LD = (10, Weapons.Mk_84___2000lb_GP_Bomb_LD)
        Mk_82___500lb_GP_Bomb_LD = (10, Weapons.Mk_82___500lb_GP_Bomb_LD)
        BRU_42_3_x_LAU_68___7_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE = (
            10,
            Weapons.BRU_42_3_x_LAU_68___7_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE,
        )
        BRU_33_2_x_LAU_61___19_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE = (
            10,
            Weapons.BRU_33_2_x_LAU_61___19_x_UnGd_Rkts__70_mm_Hydra_70_M151_HE,
        )
        HB_F4E_BLU_107B_6x = (10, WeaponsF15EX.HB_F4E_BLU_107B_6x)
        BRU_41A_with_6_x_Mk_82___500lb_GP_Bomb_LD = (
            10,
            Weapons.BRU_41A_with_6_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            10,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_55_with_2_x_GBU_32_V_2_B___JDAM__1000lb_GPS_Guided_Bomb = (
            10,
            Weapons.BRU_55_with_2_x_GBU_32_V_2_B___JDAM__1000lb_GPS_Guided_Bomb,
        )
        GBU_24B_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            10,
            Weapons.GBU_24B_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        GBU_27___2000lb_Laser_Guided_Penetrator_Bomb = (
            10,
            Weapons.GBU_27___2000lb_Laser_Guided_Penetrator_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            10,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        JAS39_SDB = (10, WeaponsF15EX.JAS39_SDB)
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            10,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_31_V_4_B___JDAM__2000lb_GPS_Guided_Penetrator_Bomb = (
            10,
            Weapons.GBU_31_V_4_B___JDAM__2000lb_GPS_Guided_Penetrator_Bomb,
        )

    class Pylon11:
        AIM_9X2_2 = (11, WeaponsF15EX.AIM_9X2_2)
        AIM_260A_2 = (11, WeaponsF15EX.AIM_260A_2)
        AIM_120D3_2 = (11, WeaponsF15EX.AIM_120D3_2)
        AIM_120C8_2 = (11, WeaponsF15EX.AIM_120C8_2)
        AIM_120C7_2 = (11, WeaponsF15EX.AIM_120C7_2)
        AIM_120C5_2 = (11, WeaponsF15EX.AIM_120C5_2)
        AGM_88F = (11, WeaponsF15EX.AGM_88F)
        AGM_88G = (11, WeaponsF15EX.AGM_88G)
        MAKO_2 = (11, WeaponsF15EX.MAKO_2)

    tasks = [
        task.CAP,
        task.Escort,
        task.FighterSweep,
        task.Intercept,
        task.SEAD,
        task.AntishipStrike,
        task.CAS,
        task.PinpointStrike,
        task.GroundAttack,
        task.RunwayAttack,
        task.AFAC,
    ]
    task_default = task.CAP
