from typing import Dict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QSplitter, QTabWidget, QScrollArea, QGridLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
# from graph_widget import GraphWidget   

def init_widgets(w_graph_widget, gridLayout_main_split: QGridLayout,\
                        widget_model: Dict[str, Dict[str, QWidget]]) -> None:
    """Создание окна из макетов виджетов

    Args:
        w_graph_widget (GraphWidget): -
        gridLayout_main_split (QGridLayout): главный лайоут для виджетов
        widget_model (dict): Словарь словарей виджетов dict{"Вкладки таб виджетов": dict{"Название виджетов": Виджеты Object}}
    """
    # Виджеты
    # w_graph_widget: GraphWidget = GraphWidget()
    tab_widget: QTabWidget = create_tab_widget_items(widget_model)
    splitter = QSplitter()
    gridLayout_main_split.addWidget(splitter)
    splitter.addWidget(w_graph_widget)
    splitter.addWidget(tab_widget)

def create_tab_widget_items(widget_model: Dict[str, Dict[str, QWidget]]) -> QTabWidget:
    """
    Создает QTabWidget с вкладками, возвращая все вкладки через фабрику.
    """
    def build_grBox(widget: QWidget, name: str) -> QGroupBox:
        grBox_widget: QGroupBox = QGroupBox(name)
        vLayout_grBox_widget: QVBoxLayout = QVBoxLayout(grBox_widget)
        grBox_widget.setMaximumHeight(widget.minimumHeight() + 40)
        grBox_widget.setMinimumWidth(widget.minimumWidth() + 20)
        vLayout_grBox_widget.addWidget(widget)
        font = QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        grBox_widget.setFont(font)
        return grBox_widget
    
    def tab_factories(widget_model: Dict[str, Dict[str, QWidget]]):
        """Функиция для согласования типов
        Args:
            widget_model (Dict[str, Dict[str, QWidget]]): _description_

        Returns:
            _type_: _description_
        """
        dict_tab_factry = {}
        for tab_name, widgets in widget_model:
            dict_tab_factry = {tab_name: widget_maker}
        return dict_tab_factry

    def widget_maker(self, widgets: Dict[str, QWidget], tab_widget: QTabWidget):
        ######################
        grBox_with_widgets: list[QGroupBox] = []
        spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Создание виджетов в grBox
        for name, widget in widgets:
            grBox_with_widgets.append(build_grBox(widget, name=name))
        # Создаем QScrollArea для прокручиваемого содержимого
        scroll_area_menu = QScrollArea()
        scroll_area_menu.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content_widget)
        # Добавляем виджеты в scroll_content_layout
        for grBox_widget in grBox_with_widgets:
            scroll_content_layout.addWidget(grBox_widget)
        return scroll_area_menu
    
    tab_widget = QTabWidget()
    tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    # Настройка шрифта для вкладок
    tab_font = QFont()
    tab_font.setFamily("Arial")
    tab_font.setPointSize(12)
    tab_widget.setFont(tab_font)
    # Используем фабрику для добавления вкладок
    factories = tab_factories(widget_model)
    for tab_name, factory in factories.items():
        tab_widget.addTab(factory(tab_widget), tab_name)
    return tab_widget

    # # Функция для создания вкладки "Осциллограф"
    # def init_tab_widget_item_meas(widgets) -> QWidget:
    #     """_summary_
    #     Args:
    #         widgets (dict): передаем сдоварь виджетов. {"Название": виджет Object}
    #     Returns:
    #         QWidget: Возвращает готовый табвиджет
    #     """
    #     ######################
    #     grBox_with_widgets: list[QGroupBox] = []
    #     spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    #     spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    #     # Создание виджетов в grBox
    #     for key, item in widgets:
    #         grBox_with_widgets.append(build_grBox(item, name=key))
    #     ######################
    #     # Создаем QScrollArea для прокручиваемого содержимого
    #     scroll_area_menu = QScrollArea()
    #     scroll_area_menu.setWidgetResizable(True)
    #     scroll_content_widget = QWidget()
    #     scroll_content_layout = QVBoxLayout(scroll_content_widget)
    #     # Добавляем виджеты в scroll_content_layout
    #     scroll_content_layout.addWidget(grBox_run_meas_widget)
    #     ######################
    #     scroll_content_layout.addItem(spacer_v_scroll)
    #     scroll_area_menu.setWidget(scroll_content_widget)
    #     menu_widget = QWidget()
    #     menu_layout = QVBoxLayout(menu_widget)
    #     menu_layout.addWidget(scroll_area_menu)
    #     # Создаем макет для подключения
    #     vLayout_ser_connect = QVBoxLayout()
    #     add_serial_widget(vLayout_ser_connect, self.w_ser_dialog)
    #     menu_layout.addItem(spacer_v)
    #     menu_layout.addLayout(vLayout_ser_connect)
    #     return menu_widget
    # # Функция для создания вкладки "Парсер"
    # def init_tab_widget_item_parser() -> QWidget:
    #     parser_widget = QWidget()
    #     # vLayout_parser = QVBoxLayout(parser_widget)
    #     return parser_widget
    
    # tab_widget = QTabWidget()
    # tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    # # Настройка шрифта для вкладок
    # tab_font = QFont()
    # tab_font.setFamily("Arial")
    # tab_font.setPointSize(12)
    # tab_widget.setFont(tab_font)
    # # Используем фабрику для добавления вкладок
    # factories = build_tab_factories(widgets)
    # for tab_name, factory in factories.items():
    #     tab_widget.addTab(factory(), tab_name)
    # return tab_widget