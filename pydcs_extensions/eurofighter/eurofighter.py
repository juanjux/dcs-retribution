from dcs import task
from dcs.planes import PlaneType
from dcs.weapons_data import Weapons

from game.modsupport import planemod
from pydcs_extensions.weapon_injector import inject_weapons


class WeaponsEurofighter:
    irist = {"clsid": "{irist}", "name": "irist", "weight": 0}
    aim132 = {"clsid": "{aim132}", "name": "aim132", "weight": 0}
    GBU_12_X3 = {"clsid": "{BRU-42_3*GBU-12}", "name": "GBU-12 X3", "weight": 0}
    MK_82_SNAKEAYE_X3 = {
        "clsid": "{BRU-42_3*Mk-82SNAKEYE}",
        "name": "MK-82 SNAKEAYE X3",
        "weight": 0,
    }
    BK90 = {"clsid": "{EF_BK90MJ2}", "name": "BK90", "weight": 0}
    brimstone = {"clsid": "{brimstone}", "name": "brimstone", "weight": 0}
    Meteor = {"clsid": "{Meteor}", "name": "Meteor", "weight": 0}
    RB15 = {"clsid": "{EF_AGM_84}", "name": "RB15", "weight": 0}
    EF_FuelTank_1000L = {
        "clsid": "{EF_FuelTank_1000L}",
        "name": "EF_FuelTank_1000L",
        "weight": 0,
    }
    RB15_2 = {"clsid": "{EF_rb15_antiship}", "name": "RB15", "weight": 0}
    MK_83 = {"clsid": "{BRU-42_3*Mk-83}", "name": "MK- 83", "weight": 0}


inject_weapons(WeaponsEurofighter)


@planemod
class Eurofighter(PlaneType):
    id = "Eurofighter"
    flyable = True
    height = 5.28
    width = 10.95
    length = 15.96
    fuel_max = 4996
    max_speed = 2495
    chaff = 120
    flare = 120
    charge_total = 240
    chaff_charge_size = 1
    flare_charge_size = 1
    eplrs = True
    category = "Multirole fighter"
    radio_frequency = 124

    livery_name = "EUROFIGHTER"

    pylons = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}

    class Pylon1:
        irist = (1, WeaponsEurofighter.irist)
        aim132 = (1, WeaponsEurofighter.aim132)
        AIM_9M_Sidewinder_IR_AAM = (1, Weapons.AIM_9M_Sidewinder_IR_AAM)
        Smokewinder___red = (1, Weapons.Smokewinder___red)
        Smokewinder___green = (1, Weapons.Smokewinder___green)
        Smokewinder___blue = (1, Weapons.Smokewinder___blue)
        Smokewinder___white = (1, Weapons.Smokewinder___white)
        Smokewinder___yellow = (1, Weapons.Smokewinder___yellow)
        Smokewinder___orange = (1, Weapons.Smokewinder___orange)
        AN_ASQ_T50_TCTS_Pod___ACMI_Pod = (1, Weapons.AN_ASQ_T50_TCTS_Pod___ACMI_Pod)

    class Pylon2:
        GBU_12___500lb_Laser_Guided_Bomb = (2, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb = (
            2,
            Weapons.BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb,
        )
        GBU_12_X3 = (2, WeaponsEurofighter.GBU_12_X3)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            2,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            2,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            2,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        Mk_82___500lb_GP_Bomb_LD = (2, Weapons.Mk_82___500lb_GP_Bomb_LD)
        Mk_83___1000lb_GP_Bomb_LD = (2, Weapons.Mk_83___1000lb_GP_Bomb_LD)
        BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD = (
            2,
            Weapons.BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD = (
            2,
            Weapons.BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD,
        )
        BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD = (
            2,
            Weapons.BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            2,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            2,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (2, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            2,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            2,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            2,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_ = (
            2,
            Weapons.BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_ = (
            2,
            Weapons.BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_,
        )
        BK90 = (2, WeaponsEurofighter.BK90)
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile = (
            2,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile,
        )
        ALARM = (2, Weapons.ALARM)
        brimstone = (2, WeaponsEurofighter.brimstone)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            2,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        irist = (2, WeaponsEurofighter.irist)
        aim132 = (2, WeaponsEurofighter.aim132)
        AIM_9M_Sidewinder_IR_AAM = (2, Weapons.AIM_9M_Sidewinder_IR_AAM)
        Meteor = (2, WeaponsEurofighter.Meteor)
        RB15 = (2, WeaponsEurofighter.RB15)

    class Pylon3:
        EF_FuelTank_1000L = (3, WeaponsEurofighter.EF_FuelTank_1000L)
        GBU_12___500lb_Laser_Guided_Bomb = (3, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb = (
            3,
            Weapons.BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb,
        )
        GBU_12_X3 = (3, WeaponsEurofighter.GBU_12_X3)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            3,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            3,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            3,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        Mk_82___500lb_GP_Bomb_LD = (3, Weapons.Mk_82___500lb_GP_Bomb_LD)
        Mk_83___1000lb_GP_Bomb_LD = (3, Weapons.Mk_83___1000lb_GP_Bomb_LD)
        BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD = (
            3,
            Weapons.BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD = (
            3,
            Weapons.BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD,
        )
        BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD = (
            3,
            Weapons.BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            3,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            3,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (3, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            3,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            3,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            3,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_ = (
            3,
            Weapons.BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_ = (
            3,
            Weapons.BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_ = (
            3,
            Weapons.BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile = (
            3,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile,
        )
        ALARM = (3, Weapons.ALARM)
        brimstone = (3, WeaponsEurofighter.brimstone)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            3,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        irist = (3, WeaponsEurofighter.irist)
        aim132 = (3, WeaponsEurofighter.aim132)
        AIM_9M_Sidewinder_IR_AAM = (3, Weapons.AIM_9M_Sidewinder_IR_AAM)
        Meteor = (3, WeaponsEurofighter.Meteor)
        RB15 = (3, WeaponsEurofighter.RB15)
        RB15_2 = (3, WeaponsEurofighter.RB15_2)

    class Pylon4:
        GBU_12___500lb_Laser_Guided_Bomb = (4, Weapons.GBU_12___500lb_Laser_Guided_Bomb)
        BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb = (
            4,
            Weapons.BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb,
        )
        GBU_12_X3 = (4, WeaponsEurofighter.GBU_12_X3)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            4,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            4,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            4,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        Mk_82___500lb_GP_Bomb_LD = (4, Weapons.Mk_82___500lb_GP_Bomb_LD)
        Mk_83___1000lb_GP_Bomb_LD = (4, Weapons.Mk_83___1000lb_GP_Bomb_LD)
        BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD = (
            4,
            Weapons.BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD = (
            4,
            Weapons.BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD,
        )
        BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD = (
            4,
            Weapons.BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            4,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            4,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (4, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            4,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            4,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            4,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_ = (
            4,
            Weapons.BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_ = (
            4,
            Weapons.BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_ = (
            4,
            Weapons.BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile = (
            4,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile,
        )
        ALARM = (4, Weapons.ALARM)
        brimstone = (4, WeaponsEurofighter.brimstone)
        RB15 = (4, WeaponsEurofighter.RB15)
        RB15_2 = (4, WeaponsEurofighter.RB15_2)

    class Pylon5:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            5,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        Meteor = (5, WeaponsEurofighter.Meteor)
        aim132 = (5, WeaponsEurofighter.aim132)
        AN_AAQ_28_LITENING___Targeting_Pod = (
            5,
            Weapons.AN_AAQ_28_LITENING___Targeting_Pod,
        )

    class Pylon6:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            6,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        Meteor = (6, WeaponsEurofighter.Meteor)
        aim132 = (6, WeaponsEurofighter.aim132)

    class Pylon7:
        EF_FuelTank_1000L = (7, WeaponsEurofighter.EF_FuelTank_1000L)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            7,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            7,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            7,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            7,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        MK_83 = (7, WeaponsEurofighter.MK_83)
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            7,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (7, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            7,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        CBU_97___10_x_SFW_Cluster_Bomb = (7, Weapons.CBU_97___10_x_SFW_Cluster_Bomb)
        CBU_87___202_x_CEM_Cluster_Bomb = (7, Weapons.CBU_87___202_x_CEM_Cluster_Bomb)
        AN_AAQ_28_LITENING___Targeting_Pod = (
            7,
            Weapons.AN_AAQ_28_LITENING___Targeting_Pod,
        )

    class Pylon8:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            8,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        Meteor = (8, WeaponsEurofighter.Meteor)
        aim132 = (8, WeaponsEurofighter.aim132)

    class Pylon9:
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            9,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        Meteor = (9, WeaponsEurofighter.Meteor)
        aim132 = (9, WeaponsEurofighter.aim132)
        AN_AAQ_28_LITENING___Targeting_Pod = (
            9,
            Weapons.AN_AAQ_28_LITENING___Targeting_Pod,
        )

    class Pylon10:
        GBU_12___500lb_Laser_Guided_Bomb = (
            10,
            Weapons.GBU_12___500lb_Laser_Guided_Bomb,
        )
        BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb = (
            10,
            Weapons.BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb,
        )
        GBU_12_X3 = (10, WeaponsEurofighter.GBU_12_X3)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            10,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            10,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            10,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        Mk_82___500lb_GP_Bomb_LD = (10, Weapons.Mk_82___500lb_GP_Bomb_LD)
        Mk_83___1000lb_GP_Bomb_LD = (10, Weapons.Mk_83___1000lb_GP_Bomb_LD)
        BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD = (
            10,
            Weapons.BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD = (
            10,
            Weapons.BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD,
        )
        BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD = (
            10,
            Weapons.BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            10,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            10,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (10, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            10,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            10,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            10,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_ = (
            10,
            Weapons.BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_ = (
            10,
            Weapons.BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_ = (
            10,
            Weapons.BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile = (
            10,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile,
        )
        ALARM = (10, Weapons.ALARM)
        brimstone = (10, WeaponsEurofighter.brimstone)
        RB15 = (10, WeaponsEurofighter.RB15)
        RB15_2 = (10, WeaponsEurofighter.RB15_2)

    class Pylon11:
        EF_FuelTank_1000L = (11, WeaponsEurofighter.EF_FuelTank_1000L)
        GBU_12___500lb_Laser_Guided_Bomb = (
            11,
            Weapons.GBU_12___500lb_Laser_Guided_Bomb,
        )
        BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb = (
            11,
            Weapons.BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb,
        )
        GBU_12_X3 = (11, WeaponsEurofighter.GBU_12_X3)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            11,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            11,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            11,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        Mk_82___500lb_GP_Bomb_LD = (11, Weapons.Mk_82___500lb_GP_Bomb_LD)
        Mk_83___1000lb_GP_Bomb_LD = (11, Weapons.Mk_83___1000lb_GP_Bomb_LD)
        BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD = (
            11,
            Weapons.BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD = (
            11,
            Weapons.BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD,
        )
        BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD = (
            11,
            Weapons.BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            11,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            11,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (11, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            11,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            11,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            11,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_ = (
            11,
            Weapons.BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_ = (
            11,
            Weapons.BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_ = (
            11,
            Weapons.BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile = (
            11,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile,
        )
        ALARM = (11, Weapons.ALARM)
        brimstone = (11, WeaponsEurofighter.brimstone)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            11,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        irist = (11, WeaponsEurofighter.irist)
        aim132 = (11, WeaponsEurofighter.aim132)
        AIM_9M_Sidewinder_IR_AAM = (11, Weapons.AIM_9M_Sidewinder_IR_AAM)
        Meteor = (11, WeaponsEurofighter.Meteor)
        RB15 = (11, WeaponsEurofighter.RB15)
        RB15_2 = (11, WeaponsEurofighter.RB15_2)

    class Pylon12:
        GBU_12___500lb_Laser_Guided_Bomb = (
            12,
            Weapons.GBU_12___500lb_Laser_Guided_Bomb,
        )
        BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb = (
            12,
            Weapons.BRU_33_with_2_x_GBU_12___500lb_Laser_Guided_Bomb,
        )
        GBU_12_X3 = (12, WeaponsEurofighter.GBU_12_X3)
        GBU_10___2000lb_Laser_Guided_Bomb = (
            12,
            Weapons.GBU_10___2000lb_Laser_Guided_Bomb,
        )
        GBU_16___1000lb_Laser_Guided_Bomb = (
            12,
            Weapons.GBU_16___1000lb_Laser_Guided_Bomb,
        )
        GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb = (
            12,
            Weapons.GBU_24A_B_Paveway_III___2000lb_Laser_Guided_Bomb,
        )
        Mk_82___500lb_GP_Bomb_LD = (12, Weapons.Mk_82___500lb_GP_Bomb_LD)
        Mk_83___1000lb_GP_Bomb_LD = (12, Weapons.Mk_83___1000lb_GP_Bomb_LD)
        BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD = (
            12,
            Weapons.BRU_33_with_2_x_Mk_82___500lb_GP_Bomb_LD,
        )
        BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD = (
            12,
            Weapons.BRU_33_with_2_x_Mk_82_Snakeye___500lb_GP_Bomb_HD,
        )
        BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD = (
            12,
            Weapons.BRU_33_with_2_x_Mk_82Y___500lb_GP_Chute_Retarded_HD,
        )
        BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD = (
            12,
            Weapons.BRU_33_with_2_x_Mk_83___1000lb_GP_Bomb_LD,
        )
        BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD = (
            12,
            Weapons.BRU_42_with_3_x_Mk_82___500lb_GP_Bombs_LD,
        )
        MK_82_SNAKEAYE_X3 = (12, WeaponsEurofighter.MK_82_SNAKEAYE_X3)
        BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD = (
            12,
            Weapons.BRU_42_with_3_x_Mk_82_AIR_Ballute___500lb_GP_Bombs_HD,
        )
        GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb = (
            12,
            Weapons.GBU_31_V_1_B___JDAM__2000lb_GPS_Guided_Bomb,
        )
        GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb = (
            12,
            Weapons.GBU_38_V_1_B___JDAM__500lb_GPS_Guided_Bomb,
        )
        BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_ = (
            12,
            Weapons.BK_90_MJ12__12x_MJ2_HEAT___36x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_ = (
            12,
            Weapons.BK_90_MJ1__72_x_MJ1_HE_FRAG_Bomblets_,
        )
        BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_ = (
            12,
            Weapons.BK_90_MJ2__24_x_MJ2_HEAT_Bomblets_,
        )
        AGM_88C_HARM___High_Speed_Anti_Radiation_Missile = (
            12,
            Weapons.AGM_88C_HARM___High_Speed_Anti_Radiation_Missile,
        )
        ALARM = (12, Weapons.ALARM)
        brimstone = (12, WeaponsEurofighter.brimstone)
        AIM_120C_AMRAAM___Active_Radar_AAM = (
            12,
            Weapons.AIM_120C_AMRAAM___Active_Radar_AAM,
        )
        irist = (12, WeaponsEurofighter.irist)
        aim132 = (12, WeaponsEurofighter.aim132)
        AIM_9M_Sidewinder_IR_AAM = (12, Weapons.AIM_9M_Sidewinder_IR_AAM)
        Meteor = (12, WeaponsEurofighter.Meteor)
        RB15 = (12, WeaponsEurofighter.RB15)
        RB15_2 = (12, WeaponsEurofighter.RB15_2)

    class Pylon13:
        irist = (13, WeaponsEurofighter.irist)
        aim132 = (13, WeaponsEurofighter.aim132)
        AIM_9M_Sidewinder_IR_AAM = (13, Weapons.AIM_9M_Sidewinder_IR_AAM)
        Smokewinder___red = (13, Weapons.Smokewinder___red)
        Smokewinder___green = (13, Weapons.Smokewinder___green)
        Smokewinder___blue = (13, Weapons.Smokewinder___blue)
        Smokewinder___white = (13, Weapons.Smokewinder___white)
        Smokewinder___yellow = (13, Weapons.Smokewinder___yellow)
        Smokewinder___orange = (13, Weapons.Smokewinder___orange)

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
