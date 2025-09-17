from PyQt6 import QtWidgets, QtCore
import sys
from modules.Engine.engine import Engine
import qtmodern.styles
from qtmodern.windows import ModernWindow
import qasync
import asyncio
from qcustomwindow import (CustomWindow, QtWidgets, QMovie, QtGui,
                                   __version__, dark, light, stylesheet)  # noqa: F401

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(stylesheet)
    dark()
    # qtmodern.styles.dark(app)
    # light(app)
    w: Engine = Engine()
    # w.show()
    # mw: ModernWindow = ModernWindow(w)
    # mw.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)  # fix flickering on resize window

    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    w.show()

    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...






