from typing import Callable, Dict, Optional, Sequence, Union

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


# Храним главный splitter для последующей замены левого виджета
_MAIN_SPLITTER: Optional[QSplitter] = None
# Ограничение минимальной ширины правой панели со скроллом
_RIGHT_PANEL_MIN_WIDTH: int = 640

def create_split_widget(gridLayout_main_split: QGridLayout, left_widget: QWidget, right_widget: QTabWidget) -> None:
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
    splitter.setObjectName("main_splitter")
    gridLayout_main_split.addWidget(splitter)
    splitter.addWidget(left_widget)
    splitter.addWidget(right_widget)
    # Настройки, чтобы левая панель схлопывалась
    splitter.setChildrenCollapsible(True)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 0)
    splitter.setSizes([800, 483])
    # Сохраняем ссылку на главный сплиттер
    global _MAIN_SPLITTER
    _MAIN_SPLITTER = splitter


def replace_left_widget(new_left_widget: QWidget) -> None:
    # left_widget.deleteLater()
    # Удаляем все дочерние виджеты, но не сам контейнер
    # for child in left_widget.children():
    #     if isinstance(child, QWidget):
    #         left_widget.hide()
    #         child.deleteLater()
    """Заменяет левый виджет в главном сплиттере без передачи старого."""
    global _MAIN_SPLITTER
    splitter = _MAIN_SPLITTER
    if splitter is None:
        return
    # Заменяем левый виджет (индекс 0)
    if splitter.count() == 0:
        return
    current_left = splitter.widget(0)
    # Если новый виджет уже стоит слева — не заменяем самим на себя
    if current_left is new_left_widget or splitter.indexOf(new_left_widget) == 0:
        new_left_widget.show()
        splitter.show()
        return
    old_left = current_left
    sp = new_left_widget.sizePolicy()
    sp.setHorizontalStretch(1)
    new_left_widget.setSizePolicy(sp)
    new_left_widget.setMinimumWidth(max(200, new_left_widget.minimumWidth()))
    splitter.replaceWidget(0, new_left_widget)
    new_left_widget.show()
    if isinstance(old_left, QWidget) and (old_left is not new_left_widget):
        old_left.hide()
    splitter.show()


def create_tab_widget_items(
    widget_model: Dict[str, Dict[str, QWidget]], tab_widget_handler: Optional[Callable] = None
) -> QTabWidget:
    """Создает и возвращает QTabWidget с организованными вкладками виджетов.
    Функция создает многоуровневый интерфейс с:
    - Вкладками (QTabWidget)
    - Прокручиваемыми областями (QScrollArea)
    - Групповыми блоками (QGroupBox) для каждого виджета

    :Args:
        widget_model (Dict[str, Dict[str, QWidget]]):
            Иерархическая структура виджетов:
                - Ключ 1 уровня: Название вкладки (str)
                - Значение: Словарь {
                    "название виджета": QWidget-объект
                }
        tab_widget_handler (Optional[Callable] = None):
        Обработчик событий изменения вкладок tabwidget.

    :Return:

        QTabWidget: Готовый виджет с вкладками, содержащий:
            - Каждая вкладка содержит ScrollArea
            - Каждый виджет оформлен в GroupBox
            - Автоматические отступы и размеры
            - Стандартизированное форматирование шрифтов

    :Example:
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
        """Создает GroupBox с заданным виджетом внутри.

        Без жёстких ограничений по ширине/высоте, чтобы корректно встраиваться
        в вертикальный scroll без горизонтальной прокрутки.
        """
        grBox_widget: QGroupBox = QGroupBox(name)
        vLayout_grBox_widget: QVBoxLayout = QVBoxLayout(grBox_widget)
        # Разрешаем горизонтальное расширение вместе с viewport
        sp = grBox_widget.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        grBox_widget.setSizePolicy(sp)
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
            dict_tab_factry[tab_name] = _widget_maker
        return dict_tab_factry

    def _widget_maker(widgets: Dict[str, Optional[QWidget | QSpacerItem]]):
        """Фабрика для создания содержимого вкладки с прокруткой.

        - Все виджеты (кроме "Подключение") попадают внутрь вертикального scroll.
        - Виджет "Подключение" добавляется ПОД scroll (вне области прокрутки).
        """
        spacer_v_scroll = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Создаем QScrollArea и наполняемый контейнер
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Прокрутка только по вертикали
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(7, 7, 7, 7)
        edge_spacer_flag = True

        # Список виджетов, которые должны быть под скроллом
        bottom_widgets: list[QWidget] = []

        # Добавляем виджеты: почти все в scroll, "Подключение" — отдельно
        for name, widget in widgets.items():
            if isinstance(widget, QSpacerItem):
                content_layout.addItem(widget)
                edge_spacer_flag = False
            elif widget is not None:
                if name.strip().lower() == "подключение":
                    bottom_widgets.append(widget)
                else:
                    content_layout.addWidget(_grBox_wrapper(widget, name=name))  # type: ignore[arg-type]

        if edge_spacer_flag:
            content_layout.addItem(spacer_v_scroll)

        scroll_area.setWidget(content)

        # Возвращаем контейнер с прокруткой и нижним блоком "Подключение"
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll_area)
        # Добавляем виджеты подключения под скроллом без обёртки
        for bw in bottom_widgets:
            container_layout.addWidget(bw)
        # Приоритет по высоте — у области прокрутки
        container_layout.setStretch(0, 1)
        return container

    #################################################################################

    tab_widget: QTabWidget = QTabWidget()
    tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    # Настройка шрифта для вкладок
    tab_font = QFont()
    tab_font.setFamily("Arial")
    tab_font.setPointSize(12)
    tab_widget.setFont(tab_font)
    # Ограничиваем минимальную ширину правой панели с вкладками (scroll)
    tab_widget.setMinimumWidth(_RIGHT_PANEL_MIN_WIDTH)
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
