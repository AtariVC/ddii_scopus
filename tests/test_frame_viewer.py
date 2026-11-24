"""Проверки формата кадров и интервала из текущей прошивки ЦМ."""

import asyncio
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from PyQt6.QtWidgets import QApplication
from pymodbus.register_read_message import ReadHoldingRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from app.src.components.frames.stream_frames import parse_ddii_frame, parse_system_frame
from app.src.components.modbus.command_interface import ModbusCMCommand
from app.widgets.controls.frame_viewer import FrameViewerWidget


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
        self.command = ModbusCMCommand(self.client, log_enabled=False)

    async def test_interval_matches_firmware_limits_without_wrapping(self):
        for seconds, expected in ((-1, 1), (0, 1), (1, 1), (25, 25), (60, 60), (3600, 60), (65536, 60)):
            with self.subTest(seconds=seconds):
                self.assertNotEqual(await self.command.set_frame_interval(seconds), b"-1")
                self.client.write_registers.assert_awaited_with(3, [expected], slave=1)

    async def test_read_addresses_sizes_and_byte_order(self):
        for reader, address in ((self.command.read_ddii_frame, 200), (self.command.read_system_frame, 240)):
            self.assertEqual(await reader(), b"\x12\x34" * 32)
            self.client.read_holding_registers.assert_awaited_with(address, 32, slave=1)


class FrameViewerTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    async def asyncSetUp(self):
        self.viewer = FrameViewerWidget()
        self.command = SimpleNamespace(
            read_system_frame=AsyncMock(return_value=bytes(64)),
            read_ddii_frame=AsyncMock(return_value=ddii_frame(25)),
        )
        self.viewer._on_device_ready(self.command)

    async def asyncTearDown(self):
        self.viewer.close()
        await asyncio.sleep(0)

    async def settle(self):
        for _ in range(4):
            await asyncio.sleep(0)

    def card(self, key="system"):
        return self.viewer.table(key)

    async def test_connect_and_reconnect_require_explicit_start(self):
        await self.settle()
        self.assertEqual(self.viewer._tasks.get_active_tasks(), [])
        self.command.read_system_frame.assert_not_awaited()
        self.command.read_ddii_frame.assert_not_awaited()
        self.card().controls.button_continuous.setChecked(True)
        self.card().controls.button_refresh.click()
        await self.settle()
        self.viewer._on_disconnected()
        await self.settle()
        self.assertFalse(self.card().controls.button_refresh.isChecked())
        self.assertFalse(self.card().controls.button_refresh.isEnabled())
        self.viewer._on_device_ready(self.command)
        await self.settle()
        self.assertEqual(self.viewer._tasks.get_active_tasks(), [])
        self.assertFalse(self.card().controls.button_refresh.isChecked())
        self.assertTrue(self.card().controls.button_refresh.isEnabled())
        self.command.read_system_frame.assert_awaited_once()

    async def test_each_button_reads_only_its_frame_once(self):
        for key in ("system", "ddii"):
            with self.subTest(key=key):
                card = self.card(key)
                self.assertFalse(card.controls.button_refresh.isCheckable())
                card.controls.button_refresh.click()
                self.assertFalse(card.controls.button_refresh.isChecked())
                await self.settle()
                self.assertTrue(card._rows)
        self.command.read_system_frame.assert_awaited_once()
        self.command.read_ddii_frame.assert_awaited_once()
        self.assertEqual(self.viewer._tasks.get_active_tasks(), [])

    async def test_mode_toggle_alone_does_not_start_polling(self):
        card = self.card()
        card.controls.button_continuous.click()
        self.assertTrue(card.controls.button_refresh.isCheckable())
        self.assertFalse(card.controls.button_refresh.isChecked())
        self.assertTrue(card.controls.lineEdit_interval.isEnabled())
        await self.settle()
        self.command.read_system_frame.assert_not_awaited()

    async def test_continuous_polling_uses_committed_interval_and_stops(self):
        card = self.card()
        card.controls.button_continuous.setChecked(True)
        card.controls.lineEdit_interval.setText("3")
        real_sleep = asyncio.sleep
        delays = []
        next_poll = asyncio.Event()

        async def sleep_interval(seconds):
            delays.append(seconds)
            await next_poll.wait()
            next_poll.clear()

        with patch("app.widgets.controls.frame_viewer.asyncio.sleep", side_effect=sleep_interval):
            card.controls.button_refresh.click()
            await real_sleep(0)
            self.assertTrue(card.controls.button_refresh.isChecked())
            self.assertFalse(card.controls.lineEdit_interval.isEnabled())
            self.command.read_system_frame.assert_awaited_once()
            self.assertEqual(delays, [3])
            next_poll.set()
            await real_sleep(0)
            self.assertEqual(self.command.read_system_frame.await_count, 2)
            card.controls.button_refresh.click()
            await real_sleep(0)
            self.assertFalse(card.controls.button_refresh.isChecked())
            self.assertTrue(card.controls.lineEdit_interval.isEnabled())
            self.assertEqual(self.viewer._tasks.get_active_tasks(), [])
        self.command.read_ddii_frame.assert_not_awaited()

    async def test_cards_poll_independently_and_disabling_repeat_stops_one(self):
        for key, seconds in (("system", 1), ("ddii", 2)):
            card = self.card(key)
            card.set_interval(seconds)
            card.controls.button_continuous.setChecked(True)
            card.controls.button_refresh.click()
        await self.settle()
        self.assertEqual(set(self.viewer._tasks.get_active_tasks()), {"frame_system", "frame_ddii"})
        self.card().controls.button_continuous.setChecked(False)
        await self.settle()
        self.assertEqual(self.viewer._tasks.get_active_tasks(), ["frame_ddii"])
        self.assertFalse(self.card().controls.button_refresh.isCheckable())
        self.assertFalse(self.card().controls.button_refresh.isChecked())
        self.assertTrue(self.card("ddii").controls.button_refresh.isChecked())

    async def test_disconnect_cancels_inflight_read_and_other_poll(self):
        pending = asyncio.Event()

        async def blocked_read():
            await pending.wait()
            return bytes(64)

        self.command.read_system_frame.side_effect = blocked_read
        for key in ("system", "ddii"):
            self.card(key).controls.button_continuous.setChecked(True)
            self.card(key).controls.button_refresh.click()
        await self.settle()
        tasks = list(self.viewer._tasks.tasks.values())
        self.viewer._on_disconnected()
        await self.settle()
        pending.set()
        await self.settle()
        self.assertTrue(all(task.cancelled() for task in tasks))
        self.assertEqual(self.viewer._tasks.get_active_tasks(), [])
        self.assertFalse(self.card()._rows)
        for key in ("system", "ddii"):
            self.assertFalse(self.card(key).controls.button_refresh.isChecked())
            self.assertFalse(self.card(key).controls.button_refresh.isEnabled())

    async def test_fast_stop_start_keeps_new_poll_and_button_active(self):
        card = self.card()
        card.controls.button_continuous.setChecked(True)
        card.controls.button_refresh.click()
        await self.settle()
        old_task = self.viewer._tasks.tasks["frame_system"]
        card.controls.button_refresh.click()
        card.controls.button_refresh.click()
        new_task = self.viewer._tasks.tasks["frame_system"]
        self.assertIsNot(old_task, new_task)
        await self.settle()
        self.assertTrue(old_task.cancelled())
        self.assertIs(self.viewer._tasks.tasks["frame_system"], new_task)
        self.assertTrue(card.controls.button_refresh.isChecked())
        self.assertEqual(self.command.read_system_frame.await_count, 2)

    async def test_repeated_single_clicks_do_not_duplicate_inflight_request(self):
        pending = asyncio.Event()

        async def blocked_read():
            await pending.wait()
            return bytes(64)

        self.command.read_system_frame.side_effect = blocked_read
        self.card().controls.button_refresh.click()
        self.card().controls.button_refresh.click()
        await self.settle()
        self.command.read_system_frame.assert_awaited_once()
        pending.set()
        await self.settle()
        self.assertEqual(self.viewer._tasks.get_active_tasks(), [])

    async def test_continuous_start_can_replace_inflight_single_read(self):
        pending = asyncio.Event()

        async def blocked_read():
            await pending.wait()
            return bytes(64)

        self.command.read_system_frame.side_effect = blocked_read
        card = self.card()
        card.controls.button_refresh.click()
        await self.settle()
        old_task = self.viewer._tasks.tasks["frame_system"]
        card.controls.button_continuous.setChecked(True)
        card.controls.button_refresh.click()
        await self.settle()
        self.assertTrue(old_task.cancelled())
        self.assertTrue(card.controls.button_refresh.isChecked())
        self.assertEqual(self.command.read_system_frame.await_count, 2)
        pending.set()
        await self.settle()
        self.assertTrue(card.controls.button_refresh.isChecked())
        self.assertEqual(self.viewer._tasks.get_active_tasks(), ["frame_system"])

    async def test_failed_read_resets_continuous_button(self):
        self.command.read_ddii_frame.return_value = b"-1"
        card = self.card("ddii")
        card.controls.button_continuous.setChecked(True)
        card.controls.button_refresh.click()
        await self.settle()
        self.assertFalse(card.controls.button_refresh.isChecked())
        self.assertEqual(self.viewer._tasks.get_active_tasks(), [])

    async def test_interval_is_validated_and_normalized(self):
        card = self.card()
        self.assertEqual(card.controls.lineEdit_interval.validator().bottom(), 1)
        self.assertEqual(card.controls.lineEdit_interval.validator().top(), 60)
        for text, expected in (("25", 25), ("", 25), ("0", 1), ("999", 60)):
            with self.subTest(text=text):
                card.controls.lineEdit_interval.setText(text)
                card.controls.button_refresh.click()
                await self.settle()
                self.assertEqual(card.interval(), expected)
                self.assertEqual(card.controls.lineEdit_interval.text(), str(expected))

    async def test_new_frame_replaces_display_without_history(self):
        raw = bytearray(ddii_frame(25))
        self.viewer.push_frame("ddii", raw)
        card = self.card("ddii")
        count = len(card._rows)
        struct.pack_into(">H", raw, 4, 456)
        self.viewer.push_frame("ddii", raw)
        self.assertEqual(len(card._rows), count)
        self.assertIn("456", card._rows["Номер кадра"].text())
        self.assertFalse(hasattr(self.viewer, "_history"))
        self.assertFalse(hasattr(self.viewer, "button_settings"))
        self.assertFalse(hasattr(self.viewer, "button_prev"))
        self.assertTrue(card._tags.isHidden())
        self.viewer.push_frame("ddii", b"bad")
        self.assertIn("456", card._rows["Номер кадра"].text())


if __name__ == "__main__":
    unittest.main()
