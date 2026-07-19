import asyncio
import sys
from pathlib import Path

import qasync
import qtmodern.styles
from PyQt6 import QtCore, QtWidgets
from qtmodern.windows import ModernWindow

from app.ui.window_linker_new import MainUIRenderer

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    qtmodern.styles.dark(app)
    # light(app)
    w: MainUIRenderer = MainUIRenderer()
    # w.show()
    mw: ModernWindow = ModernWindow(w)
    mw.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)  # fix flickering on resize window

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    mw.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...