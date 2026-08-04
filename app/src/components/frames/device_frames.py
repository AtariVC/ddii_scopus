"""Описания кадров прибора в одном месте + реестр по ключу.

Каждый кадр (:class:`~app.src.components.frames.codec.Frame`) — декларативная
раскладка регистров одного логического блока прибора. ``offset`` поля совпадает с
номером регистра в прошивке внутри блока (address = BASE + ch*NUMBER + offset).

Кадры выбираются по ключу через :data:`FRAMES`. Для Modbus-чтения ключ известен на
месте вызова (ты сам читаешь конкретное окно), поэтому «сниффинг» не нужен. Если
появится самоописывающий кадр — рядом можно завести дискриминатор (поле-тип →
ключ) и роутить по нему; сейчас такого нет.

Публичное:
* ``HVIP`` — кадр одного канала HVIP (17 регистров, MODE…PID_ERROR).
* ``FRAMES: dict[str, Frame]`` — реестр всех кадров по ``frame.key``.
"""
from __future__ import annotations

from app.src.components.frames.codec import F32, I16, MASK, U16, Field, Frame

# HVIP: один канал, регистры MB_HVIP_REG_* (offset == reg внутри канала).
# Масштаб *X100 → 0.01, *X10000 → 0.0001; STATE — битовая маска (scale=1).
HVIP = Frame(
    key="hvip",
    fields=(
        Field("mode",             0,  U16,           access="rw"),
        Field("state",            1,  MASK,          access="r"),   # маска HVIP_STATE_*
        Field("pwm_raw",          2,  U16,           access="rw"),
        Field("pwm",              3,  U16, 0.01, "%", access="rw"),
        Field("pwm_max",          4,  U16, 0.01, "%", access="rw"),
        Field("v_fb",             5,  U16, 0.01, "В", access="r"),
        Field("voltage",          6,  U16, 0.01, "В", access="r"),   # V_HV
        Field("voltage_desired",  7,  U16, 0.01, "В", access="rw"),  # уставка V_HV_DESIRED
        Field("current",          8,  U16, 0.01, "мА", access="r"),
        Field("max_current",      9,  U16, 0.01, "мА", access="rw"),
        Field("flag_overvolt",   10,  U16,           access="r"),
        Field("pid_k",           11,  U16, 0.0001,   access="rw"),
        Field("pid_p",           12,  U16, 0.0001,   access="rw"),
        Field("pid_i",           13,  U16, 0.0001,   access="rw"),
        Field("pid_d",           14,  U16, 0.0001,   access="rw"),
        Field("pid_reaction_max",15,  U16, 0.0001,   access="rw"),
        Field("pid_error",       16,  I16, 0.01,     access="r"),   # знаковый
    ),
)

# Сюда добавляются остальные кадры прибора (системные, конфиг и т.п.):
# SYSTEM = Frame(key="system", fields=(...))

# Реестр: ключ кадра -> кадр. Выбор парсера = FRAMES[key].
FRAMES: dict[str, Frame] = {frame.key: frame for frame in (HVIP,)}
