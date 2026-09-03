import asyncio
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget
import qasync


def preview(widget, title="preview", size:tuple=(460, 320), spacing=14,
            margins:tuple=(24, 24, 24, 24), stretch=1):
    import sys
    from PyQt6.QtWidgets import QApplication
    from dark_pro_widgets import qss, theme
    app = QApplication(sys.argv)
    app.setStyleSheet(qss.build_stylesheet())
    event_loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(event_loop)
    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)
    host = QWidget()
    host.setWindowTitle(title)
    host.setStyleSheet(f"background-color: {theme.BG};")
    layout = QVBoxLayout(host)
    layout.setContentsMargins(*margins)
    layout.addWidget(widget())
    layout.addStretch(1)
    host.resize(*size)
    theme.tint_window_board(int(host.winId()))
    host.show()
    with event_loop:
        try:
            event_loop.run_until_complete(app_close_event.wait())
        except asyncio.CancelledError:
            ...