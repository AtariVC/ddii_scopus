'''Описания всех переменных проекта
'''

class EnviramentVar():
    DDII_SWITCH_MODE                = 0x0001
    DDII_UPDATE_DATA                = 0x0002

    CM_ID                           = 1

    CMD_DBG_GET_TELEMETRIA          = 0x0000
    CMD_DBG_SWITCH_MODE             = 0x0001
    CMD_DBG_SET_CFG                 = 0x0002
    CMD_DBG_DBG_RESET               = 0x0003    
    CMD_DBG_CSA_TEST_ENABLE         = 0x0004
    CMD_DBG_UPDATE_CFG              = 0x0005
    CMD_DBG_SET_VOLTAGE             = 0x0006
    CMD_DBG_GET_CFG_VOLTAGE         = 0x0007    
    CMD_DBG_SET_DEFAULT_CFG         = 0x0008
    CMD_DBG_GET_VOLTAGE             = 0x0009
    CMD_DBG_GET_CFG_PWM             = 0x000A
    CMD_DBG_HVIP_ON_OFF             = 0x000B


    MB_F_CODE_16                    = 0x10
    MB_F_CODE_3                     = 0x03
    MB_F_CODE_6                     = 0x06
    REG_COMAND                      = 0

    DEBUG_MODE                      = 0x0C
    COMBAT_MODE                     = 0x0E
    CONSTANT_MODE                   = 0x0F
    SILENT_MODE                     = 0x0D


    def __init__(self):
        pass