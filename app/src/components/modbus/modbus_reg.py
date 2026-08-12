
class CmCtrlReg():
    DEBUG_MODE_SWITCH                  = 0
    CONST_MODE_SWITCH                  = 1
    POWER_HVIP_SWITCH                  = 2
    SET_INTERVAL_MEAS                  = 3
    GET_FRAME                          = 4
    CM_CHECK_MEM                       = 5
    ARCH_REQUEST                       = 6
    SET_RD_PTR_MEM                     = 7
    REQUEST_ARCH                       = 8
    SET_HH_MPP                         = 9
    SET_COEFF_ELV_LSB_MPP              = 10
    SET_OFFSET_MPP                     = 11
    START_AUTOTEST                     = 12
    GPIO_IMPACT_AUTOTEST               = 13
    LOAD_STATE_CFG                     = 14
    SAVE_CURRENT_STATE_CFG             = 15
    RESET_DEFAULT_CRG                  = 16
    CM_RESET                           = 17
    NUMBER                             = 18

class CmDbgReg():
    BASE                               = 100
    DBG_MODE                           = BASE + 0
    CONST_MODE                         = BASE + 1
    HVIP_MODE                          = BASE + 2
    CM_STATUS                          = BASE + 3
    CM_RST_COUNTER                     = BASE + 4
    MEM_RD_PTR                         = BASE + 5
    MEM_WR_PTR                         = BASE + 6
    FIFO_LEVEL                         = BASE + 7
    FIFO_ERROR_CNT                     = BASE + 8
    IB_ERROR_CNT                       = BASE + 9
    IB_NANS_CNT                        = BASE + 10
    MKO_ERROR                          = BASE + 11
    MKO_ERROR_CNT                      = BASE + 12
    NUMBER                             = BASE + 13

class CmFrameReg():
    """Кадры прибора в debug-регистрах ЦМ: читаются целиком одним окном."""
    DDII_BASE                          = 200
    DDII_NUMBER                        = 32
    SYS_BASE                           = 240
    SYS_NUMBER                         = 32


class CmHvipReg():
    BASE                               = 300
    MODE                               = BASE + 0
    STATE                              = BASE + 1
    PWM_RAW                            = BASE + 2
    PWM_X100                           = BASE + 3
    PWM_MAX_X100                       = BASE + 4
    V_FB_X100                          = BASE + 5
    V_HV_X100                          = BASE + 6
    V_HV_DESIRED_X100                  = BASE + 7
    CURRENT_X100                       = BASE + 8
    MAX_CURRENT_X100                   = BASE + 9
    FLAG_OVERVOLT                      = BASE + 10
    PID_K_X10000                       = BASE + 11
    PID_P_X10000                       = BASE + 12
    PID_I_X10000                       = BASE + 13
    PID_D_X10000                       = BASE + 14
    PID_REACTION_MAX_X10000            = BASE + 15
    PID_ERROR_X100                     = BASE + 16
    # MB_HVIP_REG_NUMBER: регистров на один канал; каналы разложены
    # последовательными блоками по NUMBER регистров от BASE.
    NUMBER                             = 17


class MppReg():
    MPP_CTRL                           = 0x0000
    MPP_CTRL_ISSUE_WAVEFORM            = 0x0009
    # NB: тот же адрес, что и MPP_STRUCT — так было и в прежней карте регистров
    TMPCOUNT                           = 0x0006
    MPP_STRUCT                         = 6
    ACQ1_PEACK                         = 7
    ACQ2_PEACK                         = 8
    DDIN_PEACK                         = 9
    MPP_HH                             = 11
    MPP_HIST_32                        = 44
    MPP_HIST_16                        = 56
    MPP_HIST_HCP                       = 62
    MPP_LEVEL                          = 0x0079
    CALIBR_ALL_CH                      = 0x0050
    OSCILL_CH0                         = 0xA000
    OSCILL_CH1                         = 0xA200

    MPP_LEVEL_TRIG                     = 1
    MPP_TRIG_CNT_CLEAR                 = 11

    MPP_START_MEASURE: list[int]       = [0x0002, 0x0001]
    MPP_STOP_MEASURE: list[int]        = [0x0002, 0x0000]
    MPP_START_MEASURE_FORCED           = 0x0051


class ModbusReg():
    ctrl_reg = CmCtrlReg()
    dbg_reg = CmDbgReg()
    hvip_reg = CmHvipReg()
    frame_reg = CmFrameReg()
    mpp_reg = MppReg()

    MB_F_CODE_16                       = 0x10
    MB_F_CODE_3                        = 0x03
    MB_F_CODE_6                        = 0x06
    REG_COMMAND                        = 0

    CM_ID                              = 1
    MPP_ID                             = 14
    # Управление вкл каналов питания детекторов
    PIPS_CH_VOLTAGE                    = 1
    SIPM_CH_VOLTAGE                    = 2
    CHERENKOV_CH_VOLTAGE               = 3


    def __init__(self):
        pass
