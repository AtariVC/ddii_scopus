from typing import Dict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QSplitter, QTabWidget, QScrollArea, QGridLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

def init_graph_window(gridLayout_main_split: QGridLayout, left_widget,\
                        widget_model: Dict[str, Dict[str, QWidget]]) -> None:
    """Создание окна из макетов виджетов. На вход принемает layout куда будут добавлены виджеты

    Args:
        gridLayout_main_split (QGridLayout): главный лайоут для виджетов
        w_graph_widget (GraphWidget): -
        widget_model (dict): Словарь словарей виджетов dict{"Вкладки таб виджетов": dict{"Название виджетов": Виджеты Object}}
    """
    # Виджеты
    # w_graph_widget: GraphWidget = GraphWidget()
    tab_widget: QTabWidget = create_tab_widget_items(widget_model)
    splitter = QSplitter()
    gridLayout_main_split.addWidget(splitter)
    splitter.addWidget(left_widget)
    splitter.addWidget(tab_widget)

def create_tab_widget_items(widget_model: Dict[str, Dict[str, QWidget]]) -> QTabWidget:
    """
    Создает QTabWidget с вкладками, возвращая все вкладки через фабрику.
    """
    
    ######################### Фабрика функций ##################################
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
        for tab_name in widget_model.keys():
            dict_tab_factry = {tab_name: widget_maker}
        return dict_tab_factry

    def widget_maker(widgets: Dict[str, QWidget], tab_widget: QTabWidget):
        ######################
        spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Создаем QScrollArea для прокручиваемого содержимого
        scroll_area_menu = QScrollArea()
        scroll_area_menu.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content_widget)
        # Создание виджетов в grBox. Добавляем виджеты в scroll_content_layout
        for name, widget in widgets.items():
            scroll_content_layout.addWidget(build_grBox(widget, name=name))
        scroll_content_layout.addItem(spacer_v_scroll)
        return scroll_content_widget
    #################################################################################
    
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
        tab_widget.addTab(factory(widget_model[tab_name], tab_widget), tab_name)
    return tab_widget

    # # Функция для создания вкладки "Осциллограф"
# def __init__(self, *args) -> None:
#         super().__init__()
#         loadUi(Path(__file__).parent.joinpath('DialogGraphWidget2.ui'), self)
#         try:
#             self.client = args[0]
#             self.run_widget: RunMaesWidget =  RunMaesWidget(self.client)
#         except:
#             self.run_widget: RunMaesWidget =  RunMaesWidget()
#             # self.cm_cmd: ModbusCMCommand = ModbusCMCommand(self.client, self.logger)
#             # self.mpp_cmd: ModbusMPPCommand = ModbusMPPCommand(self.client, self.logger)
#         # self.mw = ModbusWorker()
#         # self.logger = log_init()
#         graph_widget: GraphWidget = GraphWidget()
#         osc_widgets =  {"Измерение": self.run_widget}
#         widget_model: Dict[str, Dict[str, QWidget]] = {"Осциллограмма": osc_widgets}
#         init_graph_window(self.mainGridLayout, graph_widget, widget_model)


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