# Команды Modbus / IB в проекте

## Функциональные коды Modbus

Реализовано в `Sources/internal_bus.c` / `Sources/internal_bus.h` (внутренняя шина, Modbus RTU с CRC16).

| Код | Define | Назначение |
|-----|--------|-----------|
| 0x03 | `MB_F_CODE_3` | Read Holding Registers |
| 0x06 | `MB_F_CODE_6` | Write Single Register |
| 0x10 (16) | `MB_F_CODE_16` | Write Multiple Registers |
| 0x6A (106) | `MB_F_CODE_106` | Нестандартная команда (4 байта data) |
| 0x6F (111) | `MB_F_CODE_111` | Нестандартная команда (4 байта data) |
| 0x80 | `MB_F_CODE_ERROR` | Битовый признак ошибки (ответ-исключение) |

Дополнительно объявлен, но не обрабатывается в switch:

- `MB_F_CODE_1` (0x01) — только define, реализации нет (`internal_bus.h:24`).

Вспомогательные функции протокола: `__modbusb_crc16` (`internal_bus.c:514`), `mb_frame_calc_crc16` (`internal_bus.c:406`), `mb_frame_form_packet` (`internal_bus.c:315`), `__ib_parsing_rx_data` (`internal_bus.c:193`), `ib_run_transaction` (`internal_bus.c:109`).

## IB-команды (cm_dbg_ib_command_handler)

Обработчик: `cm_dbg_ib_command_handler()` в `Sources/main.c:362`. Срабатывает при `dev_id == CM_SELF_MB_ID` по `reg_addr` (значения — из `enum cm_dbg_cmd_list`, `Sources/cm.h:96`).

### f_code 0x10 (запись) — реализованы (`main.c:371-467`)

| reg_addr | Значение | Команда | Обработка |
|---|---|---|---|
| 1 | `CM_DBG_CMD_SWITCH_MODE` | Переключение режима | COMBAT/CONSTATNT/SILENT/DEBUG (`ddii.mode`) |
| 11 | `CMD_HVIP_ON_OFF` | Вкл/выкл HVIP | режим канала PIPS/SIPM/CHERENKOV |
| 2 | `CMD_DBG_UPDATE_DATA` | Обновить данные | `ddii_mpp_get_data()` |
| 4 | `CM_DBG_CMD_CSA_TEST_ENABLE` | Тест CSA | `csa_test.enable_test` |
| 5 | `CM_DBG_UPDATE_CFG` | Обновить конфиг | `ddii_update_cfg()` + перезапуск цикла измерений |
| 3 | `CM_DBG_CMD_CM_RESET` | Сброс ЦМ | заглушка (todo) |
| 6 | `CM_DBG_SET_VOLTAGE` | Задать напряжение/ШИМ | `ddii_cmd_set_voltage_pwm()` |
| 13 | `CM_DBG_SET_HVIP_AB` | Задать коэф. A/B | `ddii_hvip_set_coef_a_b()` |
| 8 | `SET_DEFAULT_CFG` | Конфиг по умолчанию | `ddii_set_default_cfg()` |
| 16 | `SET_VOLTAGE_CORRECTION_MODE` | Режим коррекции | `ddii.voltage_correction_mode` |

### f_code 0x03 (чтение) — реализованы (`main.c:468-524`)

| reg_addr | Значение | Команда |
|---|---|---|
| 12 | `CMD_DBG_GET_CFG` | Чтение конфига |
| 0 | `CMD_DBG_GET_TELEMETRIA` | Чтение телеметрии |
| 7 | `CM_DBG_GET_CFG_VOLTAGE` | Конфиг напряжений |
| 10 | `CM_DBG_GET_CFG_PWM` | Конфиг ШИМ |
| 9 | `CM_DBG_GET_VOLTAGE` | Текущие напряжения HVIP |
| 14 | `CM_DBG_GET_HVIP_AB` | Коэффициенты A/B |
| 17 | `CM_DBG_GET_DESIRED_HVIP` | Заданные напряжения |
| 15 | `CM_GET_TERM` | Данные термодатчиков |

### Объявлены, но НЕ реализованы / закомментированы (`cm.h:105-109`)

| reg_addr | Значение |
|---|---|
| 18 | `CM_DBG_CMD_CM_CHECK_MEM` |
| 19 | `CM_DBG_CMD_CM_INIT` |
| 20 | `CM_DBG_CMD_ARCH_REQUEST` |
| 21 | `CM_DBG_CMD_HVIP_PIPS_VOLTAGE` |
| 22 | `CM_DBG_CMD_HVIP_PIPS_READ_VOLTAGE` |
| 23 | `CM_DBG_CMD_MPP_SET_OFFSET_CHANEL1` |
| 24 | `CM_DBG_CMD_MPP_SET_OFFSET_CHANEL2` |
| 25 | `CM_DBG_CMD_MPP_GET_OFFSET_CHANEL1` |
| 26 | `CM_DBG_CMD_MPP_GET_OFFSET_CHANEL2` |
| 27 | `CM_DBG_CMD_MPP_ON_OFF` |

## Регистровые команды REG_MPP_*

Отправляются в `Sources/ddii.c` через `ib_run_transaction` (f_code 0x10/0x03): `REG_MPP_COMAND`, `REG_MPP_LEVEL_TRIG`, `REG_MPP_LEVEL_HH`, `REG_MPP_STRUCT_DATA`, `REG_MPP_LEVEL`, `REG_MPP_HIST`.
