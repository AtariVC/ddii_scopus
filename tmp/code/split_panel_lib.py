from PyQt6.QtWidgets import (QWidget, QTabWidget, QGroupBox, QVBoxLayout, 
                            QSplitter, QGridLayout, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Optional, Union, List

class SplitPanelWindow(QObject):
    """
    Универсальное окно с двумя панелями (левой и правой) и вкладками.
    Каждая панель может содержать любой виджет.
    """
    
    panel_changed = pyqtSignal(str)  # Сигнал при изменении активной панели
    
    def __init__(self, parent_widget: QWidget, parent: Optional[QObject] = None):
        """
        Инициализация разделяемого окна
        
        Args:
            parent_widget: Родительский виджет, куда будет добавлено окно
            parent: Родительский QObject (необязательный)
        """
        super().__init__(parent)
        self.parent_widget = parent_widget
        self.grid_layout = QGridLayout(parent_widget)
        self.splitter = QSplitter()
        self.grid_layout.addWidget(self.splitter)
        
        # Создаем контейнеры для панелей
        self.left_panel = QWidget()
        self.left_panel.setLayout(QVBoxLayout())
        self.left_panel.layout().setContentsMargins(0, 0, 0, 0)
        
        self.right_panel = QWidget()
        self.right_panel.setLayout(QVBoxLayout())
        self.right_panel.layout().setContentsMargins(0, 0, 0, 0)
        
        # Инициализация вкладок для правой панели
        self.right_tab_widget = None
        self.current_left_widget = None
        
        # Добавляем панели в splitter
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
    
    def set_left_widget(self, widget: QWidget):
        """Установка виджета в левую панель"""
        self.clear_left_panel()
        self.left_panel.layout().addWidget(widget)
        self.current_left_widget = widget
    
    def clear_left_panel(self):
        """Очистка левой панели"""
        while self.left_panel.layout().count():
            child = self.left_panel.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.current_left_widget = None
    
    def init_right_tabs(self, tab_widgets: Dict[str, QWidget]):
        """
        Инициализация вкладок в правой панели
        
        Args:
            tab_widgets: Словарь {имя_вкладки: виджет}
        """
        self.clear_right_panel()
        
        self.right_tab_widget = QTabWidget()
        self.right_tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Настройка шрифта для вкладок
        tab_font = QFont()
        tab_font.setFamily("Arial")
        tab_font.setPointSize(12)
        self.right_tab_widget.setFont(tab_font)
        
        # Добавляем вкладки
        for name, widget in tab_widgets.items():
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(widget)
            self.right_tab_widget.addTab(scroll_area, name)
        
        # Подключаем сигнал изменения вкладки
        self.right_tab_widget.currentChanged.connect(self._on_tab_changed)
        
        self.right_panel.layout().addWidget(self.right_tab_widget)
    
    def clear_right_panel(self):
        """Очистка правой панели"""
        while self.right_panel.layout().count():
            child = self.right_panel.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.right_tab_widget = None
    
    def add_right_tab(self, name: str, widget: QWidget):
        """Добавление новой вкладки в правую панель"""
        if self.right_tab_widget is None:
            self.right_tab_widget = QTabWidget()
            self.right_panel.layout().addWidget(self.right_tab_widget)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        self.right_tab_widget.addTab(scroll_area, name)
    
    def remove_right_tab(self, name: str):
        """Удаление вкладки из правой панели"""
        if self.right_tab_widget:
            for i in range(self.right_tab_widget.count()):
                if self.right_tab_widget.tabText(i) == name:
                    self.right_tab_widget.removeTab(i)
                    break
    
    def set_splitter_sizes(self, left_size: int, right_size: int):
        """Установка размеров разделителя"""
        self.splitter.setSizes([left_size, right_size])
    
    def _on_tab_changed(self, index):
        """Обработчик изменения вкладки"""
        if self.right_tab_widget:
            tab_name = self.right_tab_widget.tabText(index)
            self.panel_changed.emit(f"right_tab:{tab_name}")
    
    def create_group_box(self, widget: QWidget, title: str) -> QGroupBox:
        """
        Создает групповой box с заданным виджетом и заголовком
        
        Args:
            widget: Виджет для размещения внутри группы
            title: Заголовок группы
            
        Returns:
            QGroupBox: Созданный групповой box
        """
        group_box = QGroupBox(title)
        layout = QVBoxLayout(group_box)
        layout.addWidget(widget)
        
        font = QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        group_box.setFont(font)
        
        return group_box