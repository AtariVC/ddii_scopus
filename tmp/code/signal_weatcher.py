from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

class ConnectionWatcher(QObject):
    connected = pyqtSignal(str, bool)

    def __init__(self, target, *signals):
        if not target.findChild(ConnectionWatcher):
            super().__init__(target)
            self._signals = set(signals)
            target.connectNotify = lambda s: self._notified(s, True)
            target.disconnectNotify = lambda s: self._notified(s, False)
        else:
            raise RuntimeError('target already has a connection watcher')

    def _notified(self, signal, connecting):
        name = str(signal.name(), 'utf-8')
        if name in self._signals:
            count = self.parent().receivers(getattr(self.parent(), name))
            if connecting and count == 1:
                self.connected.emit(name, True)
            elif not connecting and count == 0:
                self.connected.emit(name, False)

class ExampleApp(QWidget):
    do_something = pyqtSignal(str)

    def __init__(self, something_enabled: bool = False):
        super().__init__()

        self.button = QPushButton("Do something")

        watcher = ConnectionWatcher(self.button, 'pressed')
        watcher.connected.connect(self.handleConnection)

        c1 = self.button.pressed.connect(self.do_work)
        c2 = self.button.pressed.connect(self.do_work)

        self.button.pressed.disconnect(c1)
        self.button.pressed.disconnect(c2)

        self.setLayout(QVBoxLayout())
        self.layout.addWidget(self.button)

        self.show()

    def handleConnection(self, name, connecting):
        print('connecting:', name, connecting)

    def do_work(self):
        self.do_something.emit("Something!")


if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    window = ExampleApp(something_enabled=True)
    window.do_something.connect(lambda result: print(result))
    app.exec()