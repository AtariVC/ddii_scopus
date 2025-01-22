'''Описания всех переменных проекта
'''

class EnvironmentVar():
    HEAD                           = 0x0FF1

    DDII_SWITCH_MODE                = 0x0001
    DDII_UPDATE_DATA                = 0x0002

    CM_ID                           = 1
    MPP_ID                          = 14

    CMD_DBG_GET_TELEMETRY           = 0x0000
    CMD_DBG_SWITCH_MODE             = 0x0001
    CMD_DBG_UPDATE_DATA             = 0x0002 # Команда на обновление структуры данных телеметрии
    CMD_DBG_DBG_RESET               = 0x0003    
    CMD_DBG_CSA_TEST_ENABLE         = 0x0004
    CMD_DBG_SET_CFG                 = 0x0005
    CMD_DBG_SET_VOLTAGE             = 0x0006
    CMD_DBG_GET_CFG_VOLTAGE         = 0x0007    
    CMD_DBG_SET_DEFAULT_CFG         = 0x0008
    CMD_DBG_GET_VOLTAGE             = 0x0009
    CMD_DBG_GET_CFG_PWM             = 0x000A
    CMD_DBG_HVIP_ON_OFF             = 0x000B
    CMD_DBG_GET_CFG                 = 0x000C
    CM_DBG_SET_HVIP_AB              = 0x000D
    CM_DBG_GET_HVIP_AB              = 0x000E
    CM_GET_TERM                     = 0x000F
    CM_DBG_GET_DESIRED_HVIP         = 0x0011
    

    REG_MPP_COMMAND                 = 0x0000
    GET_MPP_DATA                    = 0x0006
    REG_MPP_HH                      = 0x000A

    REG_MPP_LEVEL                   = 0x0079

    MPP_LEVEL_TRIG                  = 0x0001

    MPP_START_MEASURE: list[int]     = [0x0002, 0x0001]
    MPP_STOP_MEASURE: list[int]      = [0x0002, 0x0000]




    MB_F_CODE_16                    = 0x10
    MB_F_CODE_3                     = 0x03
    MB_F_CODE_6                     = 0x06
    REG_COMMAND                      = 0

    DEBUG_MODE                      = 0x0C
    COMBAT_MODE                     = 0x0E
    CONSTANT_MODE                   = 0x0F
    SILENT_MODE                     = 0x0D

    # Управление вкл каналов питания детекторов
    PIPS_CH_VOLTAGE                 = 1
    SIPM_CH_VOLTAGE                 = 2
    CHERENKOV_CH_VOLTAGE            = 3


    def __init__(self):
        pass