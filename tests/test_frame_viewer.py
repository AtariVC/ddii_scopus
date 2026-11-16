"""Проверки формата кадров и интервала из текущей прошивки ЦМ."""

import asyncio
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from PyQt6.QtWidgets import QApplication
from pymodbus.register_read_message import ReadHoldingRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from app.src.components.frames.stream_frames import parse_ddii_frame, parse_system_frame
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.widgets.controls.frame_viewer import FramePollSettingsDialog, FrameViewerWidget


def row(table, label):
    return table.loc[table.iloc[:, 0] == label, "Numeric"].iloc[0]


def ddii_frame(duration: int) -> bytes:
    raw = bytearray(64)
    struct.pack_into(">HHHIH", raw, 0, 0x0FF1, 0x100E, 123, 0x12345678, duration)
    return bytes(raw)


class FrameFormatTests(unittest.TestCase):
    def test_system_frame_matches_packed_firmware_report(self):
        # Память typeSysFrameUnion на little-endian МК, упаковка по 2 байта.
        memory = bytearray(64)
        struct.pack_into("<HHHI", memory, 0, 0x0FF1, 0x1001, 42, 0x56781234)
        for index in range(3):
            struct.pack_into("<BBHHH", memory, 10 + index * 8,
                             index, 100 + index, 300 + index, 400 + index, 5 + index)
        struct.pack_into("<5H4BI6H", memory, 34,
                         1, 2, 3, 4, 5, 6, 7, 8, 9, 0x12345678,
                         10, 0x7FFF, 11, 12, 0x102, 0xABCD)
        wire = struct.pack(">32H", *struct.unpack("<32H", memory))
        table = parse_system_frame(wire)
        self.assertEqual(row(table, "Время кадра, с"), 0x12345678)
        self.assertEqual(row(table, "Время работы, с"), 0x12345678)
        self.assertEqual(row(table, "HVIP 1: PWM raw"), 100)
        self.assertEqual(row(table, "HVIP 1: состояние"), 0)
        self.assertEqual(row(table, "HVIP 3: U HV"), 302)
        self.assertEqual(row(table, "Счетчик перезапусков"), 7)
        self.assertEqual(row(table, "Статус неответов"), 6)
        self.assertEqual(row(table, "Резерв"), 9)
        self.assertEqual(row(table, "Статус ЦМ"), 8)
        self.assertEqual(row(table, "Температура"), 0x7FFF)
        self.assertEqual(row(table, "CRC16"), 0xABCD)

    def test_ddii_time_and_counters_keep_high_word_first(self):
        raw = bytearray(ddii_frame(20))
        struct.pack_into(">I", raw, 22, 0x12345678)
        struct.pack_into(">I", raw, 58, 0x23456789)
        table = parse_ddii_frame(raw)
        self.assertEqual(row(table, "Время кадра, с"), 0x12345678)
        self.assertEqual(row(table, "Электроны E > 0.1 МэВ"), 0x12345678)
        self.assertEqual(row(table, "Счетчик общего числа событий E > 1.6 МэВ"), 0x23456789)


class FrameCommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = SimpleNamespace(
            write_registers=AsyncMock(return_value=WriteMultipleRegistersResponse(3, 1)),
            read_holding_registers=AsyncMock(return_value=ReadHoldingRegistersResponse([0x1234] * 32)),
        )
        self.command = ModbusCMCommand(self.client, log_enabled=False, log_serial_exchange=False)

    async def test_interval_matches_firmware_limits_without_wrapping(self):
        for seconds, expected in ((-1, 1), (0, 1), (1, 1), (25, 25), (60, 60), (3600, 60), (65536, 60)):
            with self.subTest(seconds=seconds):
                self.assertNotEqual(await self.command.set_frame_interval(seconds), b"-1")
                self.client.write_registers.assert_awaited_with(3, [expected], slave=1)

    async def test_read_addresses_sizes_and_byte_order(self):
        for reader, address in ((self.command.read_ddii_frame, 200), (self.command.read_system_frame, 240)):
            self.assertEqual(await reader(), b"\x12\x34" * 32)
            self.client.read_holding_registers.assert_awaited_with(address, 32, slave=1)


class FrameViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.viewer = FrameViewerWidget()
        self.viewer.cm_ib = SimpleNamespace(set_frame_interval=AsyncMock(return_value=b"ok"))
        self.addCleanup(self.viewer.close)

    def test_invalid_and_constant_durations_do_not_change_setting(self):
        self.viewer.push_frame("ddii", ddii_frame(25))
        self.assertEqual(self.viewer.frame_interval(), 25)
        for duration in (0, 0xE0E1, 720):
            self.viewer.push_frame("ddii", ddii_frame(duration))
            self.assertEqual(self.viewer.frame_interval(), 25)

    def test_first_setting_is_sent_even_if_it_matches_measured_duration(self):
        self.viewer.push_frame("ddii", ddii_frame(25))
        self.viewer.set_frame_interval(25)
        asyncio.run(self.viewer._flush_frame_interval())
        self.viewer.cm_ib.set_frame_interval.assert_awaited_once_with(25)

    def test_stale_frame_cannot_override_confirmed_interval(self):
        self.viewer.set_frame_interval(30)
        self.viewer.push_frame("ddii", ddii_frame(10))
        self.assertEqual(self.viewer.frame_interval(), 30)
        asyncio.run(self.viewer._flush_frame_interval())
        self.viewer.push_frame("ddii", ddii_frame(10))
        self.assertEqual(self.viewer.frame_interval(), 30)
        self.viewer.set_frame_interval(30)
        self.assertIsNone(self.viewer._pending_frame_interval)

    def test_pending_interval_can_be_changed_back(self):
        self.viewer.set_frame_interval(30)
        asyncio.run(self.viewer._flush_frame_interval())
        self.viewer.set_frame_interval(20)
        self.viewer.set_frame_interval(30)
        asyncio.run(self.viewer._flush_frame_interval())
        self.viewer.cm_ib.set_frame_interval.assert_awaited_with(30)

    def test_failed_write_is_retried(self):
        self.viewer.cm_ib.set_frame_interval.side_effect = [b"-1", b"ok"]
        self.viewer.set_frame_interval(40)
        asyncio.run(self.viewer._flush_frame_interval())
        self.assertEqual(self.viewer._pending_frame_interval, 40)
        asyncio.run(self.viewer._flush_frame_interval())
        self.assertIsNone(self.viewer._pending_frame_interval)
        self.assertEqual(self.viewer.frame_interval(), 40)

    def test_reconnect_requires_a_new_confirmation(self):
        self.viewer.set_frame_interval(30)
        asyncio.run(self.viewer._flush_frame_interval())
        self.viewer._on_disconnected()
        self.viewer.set_frame_interval(30)
        self.assertEqual(self.viewer._pending_frame_interval, 30)

    def test_viewer_and_dialog_use_firmware_limits(self):
        self.viewer.set_frame_interval(3600)
        self.assertEqual(self.viewer.frame_interval(), 60)
        self.viewer.set_frame_interval(0)
        self.assertEqual(self.viewer.frame_interval(), 1)
        dialog = FramePollSettingsDialog(self.viewer.intervals(), 1, 10)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.spinBox_frame_interval.minimum(), 1)
        self.assertEqual(dialog.spinBox_frame_interval.maximum(), 60)


if __name__ == "__main__":
    unittest.main()
