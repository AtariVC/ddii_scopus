from PyQt6.QtWidgets import (QApplication, QWidget, QTabWidget, QGroupBox, QVBoxLayout, 
                            QSplitter, QGridLayout, QMainWindow, QLabel, QPushButton, 
                            QTextEdit, QSlider, QSpacerItem, QSizePolicy, QScrollArea,
                            QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg
from typing import Dict, Callable, Optional

# Пример виджетов, которые будут добавлены во вкладки
def create_example_widgets() -> Dict[str, Dict[str, QWidget]]:
    """Создает тестовые виджеты для демонстрации"""
    widget_model = {
        "Настройки": {
            "Текст": QLabel("Пример текстового поля"),
            "Кнопка": QPushButton("Нажми меня"),
        },
        "Графики": {
            "Слайдер": QSlider(Qt.Orientation.Horizontal),
            "Описание": QTextEdit("Здесь можно ввести описание графика"),
        },
        "Данные": {
            "Информация": QLabel("Тут будут отображаться данные"),
            "Статус": QLabel("Статус: готов"),
        },
        "Таблица": {
            "_handler": lambda: None,  # Специальный обработчик для этой вкладки
            "_widget": None  # Виджет будет создан динамически
        }
    }
    return widget_model

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Создаем главный layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.gridLayout = QGridLayout(central_widget)
        
        # Создаем модель виджетов
        self.widget_model = create_example_widgets()
        
        # Создаем контейнер для графика/таблицы
        self.content_container = QWidget()
        self.content_container.setMinimumSize(400, 400)
        self.content_container.setLayout(QVBoxLayout())
        
        # Устанавливаем обработчик для вкладки "Таблица"
        self.widget_model["Таблица"]["_handler"] = self.init_table
        
        # Инициализируем график по умолчанию
        self.init_graph()
        
        # Инициализируем окно с графиками
        self.init_graph_window()
        
        # Настройки главного окна
        self.setWindowTitle("Пример работы с вкладками и графиками")
        self.resize(1000, 700)
    
    def clear_container(self):
        """Очищает контейнер от всех виджетов"""
        layout = self.content_container.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def init_graph(self):
        """Инициализирует график в контейнере"""
        self.clear_container()
        
        # Создаем график
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setTitle("Пример графика", color='k')
        plot_widget.showGrid(x=True, y=True)
        plot_widget.plot([1, 2, 3, 4, 5], [1, 3, 2, 4, 3], pen=pg.mkPen('b', width=2))
        
        self.content_container.layout().addWidget(plot_widget)
    
    def init_table(self):
        """Инициализирует таблицу в контейнере"""
        self.clear_container()
        
        # Создаем таблицу
        table = QTableWidget()
        table.setRowCount(5)
        table.setColumnCount(3)
        
        # Заполняем таблицу данными
        for row in range(5):
            for col in range(3):
                item = QTableWidgetItem(f"Данные {row+1}-{col+1}")
                table.setItem(row, col, item)
        
        self.content_container.layout().addWidget(table)
    
    def init_graph_window(self):
        """Создание окна из макетов виджетов."""
        tab_widget = self.create_tab_widget_items(self.widget_model)
        splitter = QSplitter()
        self.gridLayout.addWidget(splitter)
        splitter.addWidget(self.content_container)
        splitter.addWidget(tab_widget)
    
    def create_tab_widget_items(self, widget_model: Dict[str, Dict[str, QWidget]]) -> QTabWidget:
        """
        Создает QTabWidget с вкладками, возвращая все вкладки через фабрику.
        """
        def build_grBox(widget: QWidget, name: str) -> QGroupBox:
            grBox_widget = QGroupBox(name)
            vLayout_grBox_widget = QVBoxLayout(grBox_widget)
            grBox_widget.setMaximumHeight(widget.minimumHeight() + 40)
            grBox_widget.setMinimumWidth(widget.minimumWidth() + 20)
            vLayout_grBox_widget.addWidget(widget)
            font = QFont()
            font.setFamily("Arial")
            font.setPointSize(12)
            grBox_widget.setFont(font)
            return grBox_widget
        
        def widget_maker(widgets: Dict[str, QWidget], tab_widget: QTabWidget) -> QWidget:
            spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            scroll_area_menu = QScrollArea()
            scroll_area_menu.setWidgetResizable(True)
            scroll_content_widget = QWidget()
            scroll_content_layout = QVBoxLayout(scroll_content_widget)
            
            for name, widget in widgets.items():
                # Пропускаем специальные ключи, начинающиеся с _
                if not name.startswith('_'):
                    scroll_content_layout.addWidget(build_grBox(widget, name=name))
            
            scroll_content_layout.addItem(spacer_v_scroll)
            return scroll_content_widget
        
        tab_widget = QTabWidget()
        tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        tab_font = QFont()
        tab_font.setFamily("Arial")
        tab_font.setPointSize(12)
        tab_widget.setFont(tab_font)
        
        # Добавляем вкладки
        for tab_name, widgets in widget_model.items():
            # Если есть специальный обработчик, создаем кнопку
            if "_handler" in widgets:
                btn = QPushButton(f"Активировать {tab_name}")
                btn.clicked.connect(widgets["_handler"])
                tab_widget.addTab(btn, tab_name)
            # Иначе создаем обычную вкладку с виджетами
            elif widgets:
                tab_widget.addTab(widget_maker(widgets, tab_widget), tab_name)
        
        # Связываем изменение вкладки с обновлением содержимого
        tab_widget.currentChanged.connect(self.on_tab_changed)
        
        return tab_widget
    
    def on_tab_changed(self, index):
        """Обработчик изменения вкладки"""
        tab_widget = self.sender()
        current_tab_text = tab_widget.tabText(index)
        current_widgets = self.widget_model.get(current_tab_text, {})
        
        # Если для вкладки есть специальный обработчик, вызываем его
        if "_handler" in current_widgets:
            current_widgets["_handler"]()

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()