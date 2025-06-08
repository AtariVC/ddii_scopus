from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                            QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
                            QVBoxLayout)
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from split_panel_lib import SplitPanelWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Инициализируем наше универсальное окно
        self.split_panel = SplitPanelWindow(central_widget)
        
        # 1. Создаем виджеты для левой панели
        self._init_left_panel_widgets()
        
        # 2. Создаем виджеты для правой панели (вкладки)
        self._init_right_panel_widgets()
        
        # Настройки главного окна
        self.setWindowTitle("Универсальное разделяемое окно")
        self.resize(1200, 800)
        self.split_panel.set_splitter_sizes(800, 400)  # Размеры панелей
    
    def _init_left_panel_widgets(self):
        """Инициализация виджетов для левой панели"""
        # Вариант 1: График (pyqtgraph)
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.plot([1, 2, 3, 4, 5], [1, 3, 2, 4, 3], pen='b')
        
        # Вариант 2: Таблица
        table = QTableWidget(5, 3)
        for row in range(5):
            for col in range(3):
                table.setItem(row, col, QTableWidgetItem(f"Данные {row+1}-{col+1}"))
        
        # Вариант 3: Произвольный виджет
        custom_widget = QWidget()
        layout = QVBoxLayout(custom_widget)
        layout.addWidget(QLabel("Произвольный виджет"))
        layout.addWidget(QPushButton("Кнопка"))
        layout.addWidget(QTextEdit("Текстовое поле"))
        
        # Устанавливаем один из виджетов в левую панель
        self.split_panel.set_left_widget(plot_widget)  # Можно заменить на table или custom_widget
    
    def _init_right_panel_widgets(self):
        """Инициализация вкладок для правой панели"""
        tab_widgets = {
            "Настройки": self._create_settings_tab(),
            "Информация": self._create_info_tab(),
            "Данные": self._create_data_tab()
        }
        
        self.split_panel.init_right_tabs(tab_widgets)
    
    def _create_settings_tab(self) -> QWidget:
        """Создает вкладку с настройками"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Параметры:"))
        layout.addWidget(QPushButton("Сохранить"))
        layout.addWidget(QTextEdit("Здесь могут быть настройки"))
        
        return widget
    
    def _create_info_tab(self) -> QWidget:
        """Создает вкладку с информацией"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Информационная панель"))
        layout.addWidget(QLabel("Версия: 1.0.0"))
        layout.addWidget(QLabel("Статус: Активен"))
        
        return widget
    
    def _create_data_tab(self) -> QWidget:
        """Создает вкладку с данными"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        table = QTableWidget(4, 2)
        table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        data = [["Температура", "25°C"], ["Давление", "760 мм"], ["Влажность", "45%"]]
        
        for row, (param, value) in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(param))
            table.setItem(row, 1, QTableWidgetItem(value))
        
        layout.addWidget(table)
        return widget

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()