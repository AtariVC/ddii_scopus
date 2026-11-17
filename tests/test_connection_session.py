"""Отказ одного устройства останавливает всю выбранную сессию без новых запросов."""

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from PyQt6.QtWidgets import QApplication, QWidget
from pymodbus.exceptions import ConnectionException, ModbusIOException
from pymodbus.pdu import ExceptionResponse
from pymodbus.register_read_message import ReadHoldingRegistersResponse
from pymodbus.register_write_message import WriteMultipleRegistersResponse

from app.plugins.connection.connection_bar import ConnectionBar
from app.plugins.connection.connection_settings import ConnectionSettings
from app.src.util.async_task_manager import AsyncTaskManager


class FakeClient:
    def __init__(self):
        self.connected = True
        self.connect = AsyncMock(return_value=True)
        self.read_holding_registers = AsyncMock(return_value=ReadHoldingRegistersResponse([0] * 32))
        self.write_registers = AsyncMock(return_value=WriteMultipleRegistersResponse(3, 1))
        self.callback_disconnected = Mock()
        self.close = Mock(side_effect=self._close)

    def _close(self):
        self.connected = False


class ConnectionSessionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    async def asyncSetUp(self):
        self.settings = ConnectionSettings(serial_port="test", tcp_host="127.0.0.1", cm_id=3, mpp_id=14)
        with patch.object(ConnectionSettings, "load", return_value=self.settings):
            self.bar = ConnectionBar()
        self.bar.logger = Mock()
        self.bar._await_serial_transport_ready = AsyncMock(return_value=True)
        self.bar._tcp_preflight_diagnostics = AsyncMock()
        self.bar._send_client_identity = AsyncMock()
        self.disconnected = Mock()
        self.bar.disconnected.connect(self.disconnected)

    async def asyncTearDown(self):
        self.bar._disconnect()
        self.bar.close()
        await asyncio.sleep(0)

    async def connect(self, mode="both", transport="Serial", client=None):
        self.settings.poll_mode = mode
        self.bar.set_transport(transport)
        client = client or FakeClient()
        factory = "AsyncModbusSerialClient" if transport == "Serial" else "AsyncModbusTcpClient"
        with patch(f"app.plugins.connection.connection_bar.{factory}", return_value=client) as constructor:
            await self.bar.connect_clicked()
            self.assertEqual(constructor.call_args.kwargs["retries"], 0)
            self.assertEqual(constructor.call_args.kwargs["reconnect_delay"], 0)
        return client

    async def test_modes_probe_only_selected_devices_on_both_transports(self):
        for transport in ("Serial", "TCP"):
            for mode, slaves in (("both", [3, 14]), ("cm", [3]), ("mpp", [14])):
                with self.subTest(transport=transport, mode=mode):
                    client = await self.connect(mode, transport)
                    self.assertTrue(self.bar.is_modbus_ready())
                    self.assertEqual([call.kwargs["slave"] for call in client.read_holding_registers.call_args_list], slaves)
                    cm, mpp = self.bar.get_commands_interface()
                    self.assertEqual(cm is not None, mode != "mpp")
                    self.assertEqual(mpp is not None, mode != "cm")
                    if cm is not None:
                        self.assertEqual(cm.CM_ID, 3)
                    self.assertEqual(self.bar.get_commands_interface(), (cm, mpp))
                    before = client.read_holding_registers.call_count
                    self.assertTrue(await self.bar.check_connection(only_cm=mode != "mpp", only_mpp=mode != "cm"))
                    self.assertEqual(client.read_holding_registers.call_count, before)
                    self.bar._disconnect()

    async def test_any_required_device_failing_rejects_connection(self):
        for transport in ("Serial", "TCP"):
            for failing_slave in (3, 14):
                client = FakeClient()

                async def read(address, count, slave):
                    if slave == failing_slave:
                        raise ConnectionException("no answer")
                    return ReadHoldingRegistersResponse([0] * count)

                client.read_holding_registers.side_effect = read
                await self.connect(transport=transport, client=client)
                self.assertFalse(self.bar.is_modbus_ready())
                self.assertEqual(self.bar._btn.text(), "Подключить")
                client.close.assert_called_once()

    async def test_first_failure_blocks_queued_and_stale_requests(self):
        client = await self.connect()
        cm, mpp = self.bar.get_commands_interface()
        entered, release = asyncio.Event(), asyncio.Event()

        async def failing(*args, **kwargs):
            entered.set()
            await release.wait()
            raise ModbusIOException("no answer")

        client.read_holding_registers.reset_mock()
        client.read_holding_registers.side_effect = failing
        first = asyncio.create_task(cm.read_registers(100, 1))
        await entered.wait()
        waiting = asyncio.create_task(mpp.get_hist16())
        await asyncio.sleep(0)
        release.set()
        self.assertEqual(await asyncio.gather(first, waiting), [b"-1", b"-1"])
        self.assertEqual(await cm.read_registers(100, 1), b"-1")
        self.assertEqual(client.read_holding_registers.call_count, 1)
        self.disconnected.assert_called_once()
        self.bar.logger.error.assert_called_once()
        self.assertEqual(self.bar.get_commands_interface(), (None, None))
        self.assertFalse(self.bar.cm_ready or self.bar.mpp_ready)

    async def test_protocol_error_is_not_a_transport_disconnect(self):
        client = await self.connect()
        client.read_holding_registers.return_value = ExceptionResponse(3, 2)
        cm, _ = self.bar.get_commands_interface()
        self.assertEqual(await cm.read_registers(999, 1), b"-1")
        self.assertTrue(self.bar.is_modbus_ready())
        self.disconnected.assert_not_called()

    async def test_synchronous_client_error_also_closes_session(self):
        client = await self.connect()
        client.read_holding_registers = Mock(side_effect=ConnectionException("not connected"))
        cm, _ = self.bar.get_commands_interface()
        self.assertEqual(await cm.read_registers(100, 1), b"-1")
        self.assertFalse(self.bar.is_modbus_ready())

    async def test_write_failure_also_closes_session(self):
        client = await self.connect()
        client.write_registers.side_effect = OSError("port removed")
        cm, _ = self.bar.get_commands_interface()
        self.assertEqual(await cm.set_frame_interval(10), b"-1")
        self.assertFalse(self.bar.is_modbus_ready())
        self.disconnected.assert_called_once()

    async def test_disconnect_during_connect_cannot_establish_later(self):
        client = FakeClient()
        entered = asyncio.Event()

        async def connect():
            entered.set()
            await asyncio.Event().wait()

        client.connect.side_effect = connect
        with patch("app.plugins.connection.connection_bar.AsyncModbusSerialClient", return_value=client):
            task = asyncio.create_task(self.bar.connect_clicked())
            await entered.wait()
            await self.bar.disconnect_clicked()
            await task
        self.assertFalse(self.bar.is_modbus_ready())
        self.assertIsNone(self.bar.client)
        client.read_holding_registers.assert_not_called()

    async def test_io_error_response_and_gateway_failure_disconnect(self):
        for response in (None, ModbusIOException("timeout"), ExceptionResponse(3, 11)):
            client = await self.connect()
            client.read_holding_registers.return_value = response
            cm, _ = self.bar.get_commands_interface()
            self.assertEqual(await cm.read_registers(100, 1), b"-1")
            self.assertFalse(self.bar.is_modbus_ready())

    async def test_transport_callback_disconnects_even_when_idle(self):
        client = await self.connect(transport="TCP")
        original = self.bar._session._disconnected
        client.callback_disconnected(OSError("socket lost"))
        original.assert_called_once()
        self.assertFalse(self.bar.is_modbus_ready())
        self.disconnected.assert_called_once()
        self.assertIsNone(self.bar.tcp_client)

    async def test_disconnect_interrupts_inflight_request_without_slot_cancellation(self):
        client = await self.connect()
        cm, _ = self.bar.get_commands_interface()
        entered, stopped = asyncio.Event(), asyncio.Event()

        async def read(*args, **kwargs):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

        client.read_holding_registers.side_effect = read
        request = asyncio.create_task(cm.read_registers(100, 1))
        await entered.wait()
        await self.bar.disconnect_clicked()
        self.assertEqual(await request, b"-1")
        self.assertTrue(stopped.is_set())
        self.assertFalse(request.cancelled())

    async def test_reconnection_does_not_revive_old_commands(self):
        old_client = await self.connect()
        old_cm, _ = self.bar.get_commands_interface()
        old_session = self.bar._session
        await self.bar.disconnect_clicked()
        new_client = await self.connect()
        before = old_client.read_holding_registers.call_count
        self.assertEqual(await old_cm.read_registers(100, 1), b"-1")
        old_session.fail("late failure")
        self.assertEqual(old_client.read_holding_registers.call_count, before)
        self.assertTrue(self.bar.is_modbus_ready())
        new_client.close.assert_not_called()

    async def test_failure_cancels_all_bound_tasks_and_clears_consumers(self):
        client = await self.connect()
        owners, managers, tasks, stopped = [], [], [], []
        for device in ("cm", "mpp"):
            owner, manager, stop = QWidget(), AsyncTaskManager(), Mock()
            binding = self.bar.bind_device(owner, device, manager, Mock(), stop)
            owners.append((owner, binding))
            managers.append(manager)
            stopped.append(stop)
            for index in range(2):
                manager.create_task(asyncio.sleep(100), f"poll_{index}")
            tasks.extend(manager.tasks.values())
        await asyncio.sleep(0)
        client.read_holding_registers.side_effect = ConnectionException("unplugged")
        cm, _ = self.bar.get_commands_interface()
        await cm.read_registers(100, 1)
        await asyncio.gather(*tasks, return_exceptions=True)
        self.assertTrue(all(task.cancelled() for task in tasks))
        self.assertTrue(all(not manager.get_active_tasks() for manager in managers))
        for stop in stopped:
            stop.assert_called_once()
        for owner, _ in owners:
            owner.close()

    async def test_failed_poll_does_not_continue_to_next_request(self):
        client = await self.connect(mode="cm")
        manager, owner = AsyncTaskManager(), QWidget()
        cm, _ = self.bar.get_commands_interface()
        binding = self.bar.bind_device(owner, "cm", manager, Mock(), Mock())
        client.read_holding_registers.reset_mock()
        client.read_holding_registers.side_effect = TimeoutError("timeout")

        async def poll():
            await cm.read_registers(100, 1)
            self.fail("poll must be cancelled before the next request")

        manager.create_task(poll(), "poll")
        task = manager.tasks["poll"]
        await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(task.cancelled())
        self.assertEqual(client.read_holding_registers.call_count, 1)
        owner.close()

    async def test_old_task_completion_cannot_remove_restarted_poll(self):
        manager = AsyncTaskManager()
        manager.create_task(asyncio.sleep(100), "poll")
        old = manager.tasks["poll"]
        manager.cancel_all_tasks()
        manager.create_task(asyncio.sleep(100), "poll")
        new = manager.tasks["poll"]
        await asyncio.gather(old, return_exceptions=True)
        self.assertIs(manager.tasks.get("poll"), new)
        manager.cancel_all_tasks()
        await asyncio.gather(new, return_exceptions=True)


if __name__ == "__main__":
    unittest.main()
