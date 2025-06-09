from PyQt6.QtWidgets import (QApplication, QWidget, QTabWidget, QGroupBox, QVBoxLayout, 
                            QSplitter, QGridLayout, QMainWindow, QLabel, QPushButton, 
                            QTextEdit, QSlider, QSpacerItem, QSizePolicy, QScrollArea,
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Пример работы с вкладками и графиками")
        self.resize(1200, 800)
        
        # Главный контейнер
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QGridLayout(central)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Контейнер для контента
        self.content_container = QWidget()
        self.content_container.setLayout(QVBoxLayout())
        self.content_container.layout().setContentsMargins(0, 0, 0, 0)
        self.content_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Модель виджетов
        self.widget_model = self.create_widget_model()
        self.widget_model["Таблица"]["_handler"] = self.init_table
        
        # Инициализация
        self.init_graph()
        self.setup_main_interface()
    
    def create_widget_model(self):
        return {
            "Настройки": {
                "Текст": QLabel("Пример текстового поля"),
                "Кнопка": QPushButton("Нажми меня"),
            },
            "Графики": {
                "Слайдер": QSlider(Qt.Orientation.Horizontal),
                "Описание": QTextEdit("Описание графика"),
            },
            "Данные": {
                "Информация": QLabel("Данные будут здесь"),
                "Статус": QLabel("Готово"),
            },
            "Таблица": {
                "_handler": None,
                "_widget": None
            }
        }
    
    def setup_main_interface(self):
        tab_widget = self.create_tab_widget()
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.content_container)
        splitter.addWidget(tab_widget)
        splitter.setSizes([800, 400])
        
        self.main_layout.addWidget(splitter)
    
    def create_tab_widget(self):
        tab_widget = QTabWidget()
        tab_widget.setFont(QFont("Arial", 10))
        
        for tab_name, widgets in self.widget_model.items():
            if "_handler" in widgets:
                btn = QPushButton(f"Показать {tab_name}")
                btn.clicked.connect(widgets["_handler"])
                tab_widget.addTab(btn, tab_name)
            elif widgets:
                tab_widget.addTab(self.create_tab_content(widgets), tab_name)
        
        tab_widget.currentChanged.connect(self.on_tab_changed)
        return tab_widget
    
    def create_tab_content(self, widgets):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 5, 5, 5)
        
        for name, widget in widgets.items():
            if not name.startswith('_'):
                group = QGroupBox(name)
                group.setStyleSheet("QGroupBox { font-weight: bold; }")
                group_layout = QVBoxLayout(group)
                
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, 
                                   QSizePolicy.Policy.Fixed)
                group_layout.addWidget(widget)
                layout.addWidget(group)
        
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll
    
    def clear_container(self):
        layout = self.content_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def init_graph(self):
        self.clear_container()
        
        plot = pg.PlotWidget()
        plot.setBackground('w')
        plot.plot([1,2,3,4,5], [1,3,2,4,3], pen='b')
        
        self.content_container.layout().addWidget(plot)
    
    def init_table(self):
        self.clear_container()
        
        table = QTableWidget(20, 5)
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                table.setItem(row, col, QTableWidgetItem(f"{row+1}-{col+1}"))
        
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.content_container.layout().addWidget(table)
    
    def on_tab_changed(self, index):
        tab_text = self.sender().tabText(index)
        if tab_text == "Таблица":
            self.init_table()
        else:
            self.init_graph()

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()