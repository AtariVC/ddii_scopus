"""Кадры прибора: декларативные схемы регистров, кодек и состояние.

* :mod:`~app.src.components.frames.codec` — ``Field`` / ``Frame`` / типы + кодек.
* :mod:`~app.src.components.frames.device_frames` — описания кадров + реестр ``FRAMES``.
* :mod:`~app.src.components.frames.state` — ``DeviceState`` со слиянием частичных чтений.
* :mod:`~app.src.components.frames.stream_frames` — системный кадр и кадр ДДИИ
  (схемы ``bytes_parser``); импортируется напрямую, чтобы не тянуть pandas в
  рантайм-путь опроса.
"""
from app.src.components.frames.codec import (
    F32,
    I16,
    MASK,
    U16,
    U32,
    Field,
    FieldType,
    Frame,
    to_dataframe,
)
from app.src.components.frames.debug_view import (
    build_bp_frame,
    parse_channels,
    parse_frame,
)
from app.src.components.frames.device_frames import FRAMES, HVIP
from app.src.components.frames.state import DeviceState

__all__ = [
    "Field",
    "FieldType",
    "Frame",
    "U16",
    "I16",
    "U32",
    "F32",
    "MASK",
    "to_dataframe",
    "FRAMES",
    "HVIP",
    "DeviceState",
    "build_bp_frame",
    "parse_frame",
    "parse_channels",
]
