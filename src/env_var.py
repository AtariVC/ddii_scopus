'''Описания всех переменных проекта
'''

class EnvironmentVar():
    HEAD                            = 0x0FF1

    DDII_SWITCH_MODE                = 0x0001
    DDII_UPDATE_DATA                = 0x0002

    CM_ID                           = 1
    MPP_ID_DEFAULT                  = 14

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

    # CM legacy debug commands, FC16 only. See cm_dbg_cmd_list in cm.h.
    CM_DBG_CMD_CTRL                 = 0x0000
    CM_DBG_CMD_SWITCH_ON_OFF        = 0x0001
    CM_DBG_CMD_CM_RESET             = 0x0002
    CM_DBG_CMD_CM_CHECK_MEM         = 0x0003
    CM_DBG_CMD_CM_INIT              = 0x0004
    CM_DBG_CMD_ARCH_REQUEST         = 0x0005

    # CM ctrl commands through CM_DBG_CMD_CTRL. See ctrl_list in cm.h.
    CM_CTRL_START_TEST              = 0x0000
    CM_CTRL_SET_DESIRED_HV_X10      = 0x0001
    CM_CTRL_SET_INTERVAL_MEAS       = 0x0002
    CM_CTRL_SET_COEFF_ELV_LSB       = 0x0003
    CM_CTRL_SET_HH                  = 0x0004
    CM_CTRL_SAVE_CURRENT_STATE      = 0x0005
    CM_CTRL_LOAD_STATE              = 0x0006
    CM_CTRL_RESET_DEFAULT           = 0x0007

    # CM debug register map. See modbus_debug.h.
    MB_DBG_REG_BASE                 = 100
    MB_DDII_FRAME_REG_BASE          = 200
    MB_SYS_FRAME_REG_BASE           = 240
    MB_HVIP_REG_BASE                = 300
    MB_CFG_REG_BASE                 = 400

    MB_DBG_REG_DBG_ENABLE           = 0
    MB_DBG_REG_CONST_MODE           = 1
    MB_DBG_REG_CM_STATUS            = 2
    MB_DBG_REG_CM_RST_COUNTER       = 3
    MB_DBG_REG_CM_MEAS_INTERVAL_MS  = 4
    MB_DBG_REG_MPP_INTERVAL_MS      = 5
    MB_DBG_REG_DDII_INTERVAL_MS     = 6
    MB_DBG_REG_MEM_RD_PTR           = 7
    MB_DBG_REG_MEM_WR_PTR           = 8
    MB_DBG_REG_FIFO_LEVEL           = 9
    MB_DBG_REG_FIFO_ERROR_CNT       = 10
    MB_DBG_REG_IB_ERROR_CNT         = 11
    MB_DBG_REG_IB_NANS_CNT          = 12
    MB_DBG_REG_MKORT_ERROR          = 13
    MB_DBG_REG_MKORT_ERROR_CNT      = 14
    MB_DBG_REG_COMMAND              = 15
    MB_DBG_REG_COMMAND_RESULT       = 16
    MB_DBG_REG_NUMBER               = 17

    MB_FRAME_REG_NUMBER             = 32
    MB_DDII_FRAME_REG_NUMBER        = 32
    MB_SYS_FRAME_REG_NUMBER         = 32
    MB_CFG_REG_NUMBER               = 58

    MB_DBG_CMD_CM_INIT              = 1 << 0
    MB_DBG_CMD_MEM_FORMAT           = 1 << 1
    MB_DBG_CMD_FIFO_CLEAR           = 1 << 2
    MB_DBG_CMD_MEM_RD_PTR_ZERO      = 1 << 3
    MB_DBG_CMD_PREPARE_FRAME        = 1 << 4
    MB_DBG_CMD_PREPARE_SYS_FRAME    = 1 << 5

    REG_CM_DBG_ENABLE               = MB_DBG_REG_BASE + MB_DBG_REG_DBG_ENABLE
    REG_CM_DBG_CONST_MODE           = MB_DBG_REG_BASE + MB_DBG_REG_CONST_MODE
    REG_CM_DBG_STATUS               = MB_DBG_REG_BASE + MB_DBG_REG_CM_STATUS
    REG_CM_DBG_RST_COUNTER          = MB_DBG_REG_BASE + MB_DBG_REG_CM_RST_COUNTER
    REG_CM_DBG_MEAS_INTERVAL_MS     = MB_DBG_REG_BASE + MB_DBG_REG_CM_MEAS_INTERVAL_MS
    REG_CM_DBG_MPP_INTERVAL_MS      = MB_DBG_REG_BASE + MB_DBG_REG_MPP_INTERVAL_MS
    REG_CM_DBG_DDII_INTERVAL_MS     = MB_DBG_REG_BASE + MB_DBG_REG_DDII_INTERVAL_MS
    REG_CM_DBG_MEM_RD_PTR           = MB_DBG_REG_BASE + MB_DBG_REG_MEM_RD_PTR
    REG_CM_DBG_MEM_WR_PTR           = MB_DBG_REG_BASE + MB_DBG_REG_MEM_WR_PTR
    REG_CM_DBG_FIFO_LEVEL           = MB_DBG_REG_BASE + MB_DBG_REG_FIFO_LEVEL
    REG_CM_DBG_FIFO_ERROR_CNT       = MB_DBG_REG_BASE + MB_DBG_REG_FIFO_ERROR_CNT
    REG_CM_DBG_IB_ERROR_CNT         = MB_DBG_REG_BASE + MB_DBG_REG_IB_ERROR_CNT
    REG_CM_DBG_IB_NANS_CNT          = MB_DBG_REG_BASE + MB_DBG_REG_IB_NANS_CNT
    REG_CM_DBG_MKORT_ERROR          = MB_DBG_REG_BASE + MB_DBG_REG_MKORT_ERROR
    REG_CM_DBG_MKORT_ERROR_CNT      = MB_DBG_REG_BASE + MB_DBG_REG_MKORT_ERROR_CNT
    REG_CM_DBG_COMMAND              = MB_DBG_REG_BASE + MB_DBG_REG_COMMAND
    REG_CM_DBG_COMMAND_RESULT       = MB_DBG_REG_BASE + MB_DBG_REG_COMMAND_RESULT

    MB_HVIP_REG_CH_SELECT           = 0
    MB_HVIP_REG_MODE                = 1
    MB_HVIP_REG_STATE               = 2
    MB_HVIP_REG_PWM_RAW             = 3
    MB_HVIP_REG_PWM_X100            = 4
    MB_HVIP_REG_PWM_MAX_X100        = 5
    MB_HVIP_REG_V_FB_X100           = 6
    MB_HVIP_REG_V_HV_X100           = 7
    MB_HVIP_REG_V_HV_DESIRED_X100   = 8
    MB_HVIP_REG_CURRENT_X100        = 9
    MB_HVIP_REG_MAX_CURRENT_X100    = 10
    MB_HVIP_REG_FLAG_OVERVOLT       = 11
    MB_HVIP_REG_PID_K_X10000        = 12
    MB_HVIP_REG_PID_P_X10000        = 13
    MB_HVIP_REG_PID_I_X10000        = 14
    MB_HVIP_REG_PID_D_X10000        = 15
    MB_HVIP_REG_PID_REACTION_MAX_X10000 = 16
    MB_HVIP_REG_PID_ERROR_X100      = 17
    MB_HVIP_REG_NUMBER              = 18

    REG_CM_HVIP_CH_SELECT           = MB_HVIP_REG_BASE + MB_HVIP_REG_CH_SELECT
    REG_CM_HVIP_MODE                = MB_HVIP_REG_BASE + MB_HVIP_REG_MODE
    REG_CM_HVIP_STATE               = MB_HVIP_REG_BASE + MB_HVIP_REG_STATE
    REG_CM_HVIP_PWM_RAW             = MB_HVIP_REG_BASE + MB_HVIP_REG_PWM_RAW
    REG_CM_HVIP_PWM_X100            = MB_HVIP_REG_BASE + MB_HVIP_REG_PWM_X100
    REG_CM_HVIP_PWM_MAX_X100        = MB_HVIP_REG_BASE + MB_HVIP_REG_PWM_MAX_X100
    REG_CM_HVIP_V_FB_X100           = MB_HVIP_REG_BASE + MB_HVIP_REG_V_FB_X100
    REG_CM_HVIP_V_HV_X100           = MB_HVIP_REG_BASE + MB_HVIP_REG_V_HV_X100
    REG_CM_HVIP_V_HV_DESIRED_X100   = MB_HVIP_REG_BASE + MB_HVIP_REG_V_HV_DESIRED_X100
    REG_CM_HVIP_CURRENT_X100        = MB_HVIP_REG_BASE + MB_HVIP_REG_CURRENT_X100
    REG_CM_HVIP_MAX_CURRENT_X100    = MB_HVIP_REG_BASE + MB_HVIP_REG_MAX_CURRENT_X100
    REG_CM_HVIP_FLAG_OVERVOLT       = MB_HVIP_REG_BASE + MB_HVIP_REG_FLAG_OVERVOLT
    REG_CM_HVIP_PID_K_X10000        = MB_HVIP_REG_BASE + MB_HVIP_REG_PID_K_X10000
    REG_CM_HVIP_PID_P_X10000        = MB_HVIP_REG_BASE + MB_HVIP_REG_PID_P_X10000
    REG_CM_HVIP_PID_I_X10000        = MB_HVIP_REG_BASE + MB_HVIP_REG_PID_I_X10000
    REG_CM_HVIP_PID_D_X10000        = MB_HVIP_REG_BASE + MB_HVIP_REG_PID_D_X10000
    REG_CM_HVIP_PID_REACTION_MAX_X10000 = MB_HVIP_REG_BASE + MB_HVIP_REG_PID_REACTION_MAX_X10000
    REG_CM_HVIP_PID_ERROR_X100      = MB_HVIP_REG_BASE + MB_HVIP_REG_PID_ERROR_X100

    CM_SET_READ_POINTER             = 30
    CM_SET_WRITE_POINTER            = 32
    CM_GET_READ_POINTER             = 29
    CM_GET_WRITE_POINTER            = 31
    READ_MEM_FRAME                  = 33

    REG_MPP_CTRL                    = 0x0000
    REG_MPP_CTRL_ISSUE_WAVEFORM     = 0x0009
    REG_MPP_CTRL_SET_HH             = 0x0008
    REG_MPP_CTRL_TRIG_COUNT_CLEAR   = 0x000B
    
    
    TMPCOUNT                        = 0x0006
    REG_GET_MPP_STRUCT              = 0x0006
    ACQ1_PEACK                      = 0x0007
    ACQ2_PEACK                      = 0x0008
    DDIN_PEACK                      = 0x0009
    REG_MPP_HH                      = 0x000B
    REG_MPP_HIST_32                 = 44
    REG_MPP_HIST_16                 = 56
    REG_MPP_HIST_HCP                = 62
    REG_MPP_LEVEL                   = 0x0079
    REG_CALIBR_ALL_CH               = 0x0050
    REG_OSCILL_CH0                  = 0xA000
    REG_OSCILL_CH1                  = 0xA200

    

    MPP_LEVEL_TRIG                  = 0x0001
    MPP_TRIG_CNT_CLEAR              = 0x000B

    MPP_START_MEASURE: list[int]    = [0x0002, 0x0001]
    MPP_STOP_MEASURE: list[int]     = [0x0002, 0x0000]
    MPP_START_MEASURE_FORCED        = 0x0051




    MB_F_CODE_16                    = 0x10
    MB_F_CODE_3                     = 0x03
    MB_F_CODE_6                     = 0x06
    REG_COMMAND                     = 0

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
