"""Доставка консольного лога в Qt, фильтры и освобождение обработчиков."""

import io
import sys
import unittest
from threading import Thread

from loguru import logger
from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtWidgets import QApplication, QLabel

from app.src.components.log.config import log_init
from app.src.components.log.qt_sink import ConsoleLogSink
from app.widgets.controls.event_log import EventLogView, EventLogWidget


class ConsoleLogSinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        log_init()

    def setUp(self):
        self.console = io.StringIO()
        self.allowed = {"INFO", "WARNING"}
        self.console_id = logger.add(
            self.console, level=0,
            filter=lambda r: r["extra"].get("event_log_test") and r["level"].name in self.allowed,
        )
        self.log = logger.bind(event_log_test=True)
        self.sink = ConsoleLogSink(logger, max_entries=3, streams=(self.console,))
        self.entries = []
        self.sink.entriesReady.connect(self.entries.extend)
        self.addCleanup(logger.remove, self.console_id)
        self.addCleanup(self.sink.close)

    def test_console_filter_and_original_output_are_preserved(self):
        self.log.info("visible")
        self.log.debug("filtered")
        self.sink.flush()
        self.assertEqual([entry[2] for entry in self.entries], ["visible"])
        self.assertIn("visible", self.console.getvalue())
        self.assertNotIn("filtered", self.console.getvalue())

    def test_new_level_is_discovered_from_configuration(self):
        name = "EVENT_LOG_TEST_NEW"
        try:
            logger.level(name)
        except ValueError:
            logger.level(name, no=27)
        self.allowed.add(name)
        # Дополнительные поля фильтра узнаются по настоящей записи.
        self.log.log(name, "new level")
        self.sink.flush()
        self.assertIn(name, self.sink.levels())
        self.assertEqual(self.entries[-1][1:], (name, "new level"))

    def test_worker_thread_only_queues_records(self):
        worker = Thread(target=lambda: self.log.info("from worker"))
        worker.start()
        worker.join()
        self.assertEqual(self.entries, [])
        self.sink.flush()
        self.assertEqual(self.entries[-1][2], "from worker")

    def test_pending_queue_is_bounded(self):
        for index in range(5):
            self.log.info(str(index))
        self.sink.flush()
        self.assertEqual([entry[2] for entry in self.entries], ["2", "3", "4"])

    def test_close_removes_only_additional_sink(self):
        self.sink.close()
        self.sink.close()
        self.log.info("still in console")
        self.sink.flush()
        self.assertEqual(self.entries, [])
        self.assertIn("still in console", self.console.getvalue())

    def test_qt_destruction_removes_handler(self):
        sink = ConsoleLogSink(logger, streams=(self.console,))
        handler_id = sink._handler_id
        sink.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertNotIn(handler_id, logger._core.handlers)


class EventLogWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        log_init()

    def setUp(self):
        self.widget = EventLogWidget()
        self.addCleanup(self.widget.close)

    def test_configured_console_levels_have_buttons_without_live_label(self):
        levels = {button.property("log_level") for button in self.widget._filters.buttons()}
        self.assertTrue({"ALL", "DEBUG", "INFO", "WARNING", "ERROR", "RX", "TX", "EMULATOR"} <= levels)
        self.assertNotIn("tail · live", [label.text() for label in self.widget.findChildren(QLabel)])

    def test_level_filter_uses_original_names(self):
        view = self.widget.log_view
        view.add("12:00:00", "INFO", "one")
        view.add("12:00:01", "WARNING", "two")
        button = next(button for button in self.widget._filters.buttons()
                      if button.property("log_level") == "WARNING")
        button.click()
        self.assertTrue(view._rows[0][1].isHidden())
        self.assertFalse(view._rows[1][1].isHidden())
        self.assertEqual(view._rows[1][1].findChildren(QLabel)[1].text(), "WARN")

    def test_new_level_button_is_added_without_losing_selection(self):
        info = next(button for button in self.widget._filters.buttons()
                    if button.property("log_level") == "INFO")
        info.click()
        level = "EVENT_LOG_DYNAMIC"
        try:
            logger.level(level)
        except ValueError:
            logger.level(level, no=26)
        console_id = logger.add(sys.stdout, level=level,
                                filter=lambda record: record["level"].name == level)
        self.addCleanup(logger.remove, console_id)
        self.widget.sink.flush()
        self.assertIn(level, [button.property("log_level") for button in self.widget._filters.buttons()])
        self.assertEqual(self.widget._filters.checkedButton().property("log_level"), "INFO")

    def test_messages_remain_plain_text(self):
        self.widget.log_view.add("12:00:00", "INFO", "<b>literal</b>")
        message = self.widget.log_view._rows[-1][1].findChildren(QLabel)[-1]
        self.assertEqual(message.text(), "<b>literal</b>")
        self.assertEqual(message.textFormat(), Qt.TextFormat.PlainText)

    def test_history_is_bounded_and_can_be_cleared(self):
        view = EventLogView(max_entries=2)
        self.addCleanup(view.close)
        for index in range(4):
            view.add("12:00:00", "INFO", str(index))
        self.assertEqual(len(view._rows), 2)
        self.assertEqual(view._rows[0][1].findChildren(QLabel)[-1].text(), "2")
        view.clear()
        self.assertEqual(view._rows, [])
        self.assertEqual(view._vbox.count(), 1)  # остался только stretch


if __name__ == "__main__":
    unittest.main()
