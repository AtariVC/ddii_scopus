import sys
from pathlib import Path

src_path = Path(__file__).resolve().parents[2]
sys.path.append(str(src_path))

from src.event.event import Event  # noqa: E402
from src.log_config import log_init, log_s  # noqa: E402

_bufer = None

class SyncDataManeger():
    global _data
    def __init__(self):
        self.sync_name_event: Event = Event(str)
        self.logger = log_init()

    def sync_data(self, data: str) -> None:
        self.sync_name_event.emit(_data)

    # def sync_name(self) -> None:
    #     if self.name_fifo:
    #         self.synced_name = self.name_fifo
    #     else:
    #         self.synced_name = ''
    #         self.logger.error("Нет имени для синхронизации. self.name_fifo == ''")
    #         raise ValueError()