from __future__ import annotations
import logging
import threading
from collections.abc import Callable
from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, action: Callable, parent=None):
        super().__init__(parent)
        self.action = action
        self.cancel = threading.Event()

    def run(self) -> None:
        try:
            self.completed.emit(self.action(self.cancel, self.progress.emit))
        except Exception as exc:
            logging.getLogger(__name__).exception("Operazione fallita")
            self.failed.emit(str(exc))
