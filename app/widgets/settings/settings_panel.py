from dark_pro_widgets.widgets.controls.nav_list import NavList
from app.widgets.settings.mpp_level import MPPLevel
from PyQt6 import QtWidgets


_ITEMS_NAVLIST = ["Уровни МПП"]

class SettingPanel(NavList):
    def __init__(self, parent) -> None:
        super().__init__()
        self._parent = parent
        self._pages = {}
        # ConnectionBar (нижняя панель связи): MPPLevel сам берёт у неё командные
        # интерфейсы ЦМ и МПП по сигналу подключения
        self.mpp_level = MPPLevel(self._parent.w_ser_dialog)
        self.build_navlist()
        self.sectionChanged.connect(self.on_screen_changed)

    def build_navlist(self):
        nav_items = _ITEMS_NAVLIST
        self.set_items(nav_items)

    def on_screen_changed(self):
        index_current_navitems = self.current_index()
        self._parent.stack_setting_panel.setCurrentIndex(index_current_navitems)

    def build_stack_widget(self):
        """Собирает стек страниц: порядок страниц = порядок пунктов навигации."""
        self._pages = {_ITEMS_NAVLIST[0]: self.mpp_level}
        for item in _ITEMS_NAVLIST:
            # пункт без своей страницы — пустая заглушка, чтобы индексы стека
            # совпадали с индексами навигации
            page = self._pages.get(item)
            self._parent.stack_setting_panel.addWidget(page if page is not None
                                                       else QtWidgets.QWidget())
