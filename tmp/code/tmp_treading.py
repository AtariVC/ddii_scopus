import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg
from queue import Queue
import threading
import time
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

class WorkerThread(QObject):
    finished = pyqtSignal()

    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        self.running = True

    def run(self):
        while self.running:
            # Генерируем случайные данные
            data = np.random.random(100)
            # Помещаем данные в очередь
            self.queue.put(data)
            # Ждем 100 мс перед генерацией следующих данных
            time.sleep(0.1)
        # self.finished.emit()

    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Пример использования PyQtGraph с queue и threading")
        self.setGeometry(100, 100, 800, 600)

        self.graph_widget = pg.PlotWidget()
        self.setCentralWidget(self.graph_widget)

        self.plot_data_item = self.graph_widget.plot()

        layout = QVBoxLayout()
        layout.addWidget(self.graph_widget)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.queue = Queue()
        self.worker_thread = threading.Thread(target=self.worker_run)
        self.worker_thread.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)  # Обновляем график каждые 100 мс

    def worker_run(self):
        self.worker = WorkerThread(self.queue)
        self.worker.run()

    def update_plot(self):
        while not self.queue.empty():
            data = self.queue.get()
            self.plot_data_item.setData(data)

    def closeEvent(self, event):
        # Отправляем сигнал остановки потока
        self.worker.stop()
        self.worker.finished.connect(self.worker_thread_finished)

    def worker_thread_finished(self):
        # При завершении работы потока завершаем главное приложение
        self.worker_thread.join()
        sys.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
