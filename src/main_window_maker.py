from typing import Dict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QSplitter, QTabWidget, QScrollArea, QGridLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from typing import Optional, Sequence, Callable, Union

def create_split_widget(gridLayout_main_split: QGridLayout, 
                        left_widget: QWidget,
                        right_widget: QTabWidget) -> None:
    """Создает и добавляет в layout разделитель (QSplitter) с двумя виджетами.
    
    Функция принимает основной QGridLayout и два виджета (обычно QTabWidget), 
    создает горизонтальный QSplitter, размещает в нем оба виджета 
    и добавляет разделитель в указанный layout.

    Args:
        gridLayout_main_split (QGridLayout): Основной layout, в который будет добавлен QSplitter.
        left_widget (QTabWidget): Виджет, который будет размещен слева в QSplitter.
        right_widget (QTabWidget): Виджет, который будет размещен справа в QSplitter.
    """
    # Виджеты
    # w_graph_widget: GraphWidget = GraphWidget()
    # tab_widget: QTabWidget = create_tab_widget_items(widget_model)
    splitter = QSplitter()
    gridLayout_main_split.addWidget(splitter)
    splitter.addWidget(left_widget)
    splitter.addWidget(right_widget)

def clear_left_widget(self, left_widget: QWidget):
    left_widget.deleteLater()



def create_tab_widget_items(widget_model: Dict[str, Dict[str, QWidget]],
                            tab_widget_handler: Optional[Callable] = None) -> QTabWidget:
    """Создает и возвращает QTabWidget с организованными вкладками виджетов.

    Функция создает многоуровневый интерфейс с:
    - Вкладками (QTabWidget)
    - Прокручиваемыми областями (QScrollArea) 
    - Групповыми блоками (QGroupBox) для каждого виджета

    Args:
        widget_model (Dict[str, Dict[str, QWidget]]): 
            Иерархическая структура виджетов:
                - Ключ 1 уровня: Название вкладки (str)
                - Значение: Словарь {
                    "название виджета": QWidget-объект
                }
        tab_widget_handler (Optional[Callable] = None): 
        Обработчик событий изменения вкладок tabwidget.

    Returns:
        QTabWidget: Готовый виджет с вкладками, содержащий:
            - Каждая вкладка содержит ScrollArea
            - Каждый виджет оформлен в GroupBox
            - Автоматические отступы и размеры
            - Стандартизированное форматирование шрифтов

    Example:
        widget_structure = {

            "Графики": {
                "График 1": GraphWidget(),
                "График 2": GraphWidget()},

            "Настройки": {
                "Параметры": SettingsWidget()}
        }
        tab_widget = create_tab_widget_items(widget_structure)
        
    """
    
    ######################### Фабрика функций ##################################
    def _grBox_wrapper(widget: QWidget, name: str) -> QGroupBox:
        """Создает GroupBox с заданным виджетом внутри."""
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
    
    def _tab_factories(widget_model: Dict[str, Dict[str, QWidget]]):
        """Создает словарь фабричных функций для генерации содержимого вкладок.

        Args:
            widget_model (Dict[str, Dict[str, QWidget]]): 
                Словарь конфигурации вкладок, где:
                    - Ключ (str): название вкладки
                    - Значение (Dict[str, QWidget]): словарь виджетов в формате:
                        {"название виджета": QWidget-объект}

        Returns:
            Dict[str, Callable]: 
                Словарь фабричных функций в формате:
                    {"название вкладки": функция-widget_maker}
                Где widget_maker принимает (widgets: Dict[str, QWidget], tab_widget: QTabWidget)
                и возвращает QWidget с оформленными элементами.
        """
        dict_tab_factry = {}
        for tab_name in widget_model.keys():
            dict_tab_factry[tab_name]= _widget_maker
        return dict_tab_factry

    def _widget_maker(widgets: Dict[str, Optional[QWidget| QSpacerItem]]):
        """Фабрика для создания содержимого вкладки."""
        ######################
        spacer_v = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Создаем QScrollArea для прокручиваемого содержимого
        scroll_area_menu = QScrollArea()
        scroll_area_menu.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        scroll_content_layout = QVBoxLayout(scroll_content_widget)
        insert_spacer_flag = False
        # Создание виджетов в grBox. Добавляем виджеты в scroll_content_layout
        for name, widget in widgets.items():
            if isinstance(widget, QSpacerItem):
                spacer: QSpacerItem = widget # type: ignore
                scroll_content_layout.addItem(spacer)
            elif widget is not None:
                scroll_content_layout.addWidget(_grBox_wrapper(widget, name=name)) # type: ignore
                insert_spacer_flag = not insert_spacer_flag
        if insert_spacer_flag:
            scroll_content_layout.addItem(spacer_v_scroll)
        return scroll_content_widget
    
    #################################################################################
        

    tab_widget: QTabWidget = QTabWidget()
    tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    # Настройка шрифта для вкладок
    tab_font = QFont()
    tab_font.setFamily("Arial")
    tab_font.setPointSize(12)
    tab_widget.setFont(tab_font)
    # Используем фабрику для добавления вкладок
    factories = _tab_factories(widget_model)
    for tab_name, factory in factories.items():
        tab_widget.addTab(factory(widget_model[tab_name]), tab_name)
        if tab_widget_handler:
            # добавляем обработчик нажатия вкладок
            if tab_widget_handler:
                tab_widget.currentChanged.connect(tab_widget_handler)
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