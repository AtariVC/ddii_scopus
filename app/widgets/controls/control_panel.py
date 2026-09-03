from dark_pro_widgets.widgets.controls.nav_list import NavList
from app.widgets.controls.frame_viewer import FrameViewerWidget
from app.widgets.controls.power import PowerControlWidget
from app.widgets.settings.power_settings import PowerSettingsWidget
from PyQt6 import QtWidgets

_ITEMS_NAVLIST = ["Контроль питания", "Журнал событий",
                  "Просмотрщик кадров", "Тестирование"]

class ControlPanel(NavList):

    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        self._pages = {}
        self.power_panel = PowerControlWidget(self._parent.w_ser_dialog)
        self.frame_viewer = FrameViewerWidget(self._parent.w_ser_dialog)
        self.build_navlist()
        self.sectionChanged.connect(self.on_screen_changed)

    def build_navlist(self):
        nav_items = _ITEMS_NAVLIST
        self.set_items(nav_items)
        
    def on_screen_changed(self):
        index_current_navitems = self.current_index()
        self._parent.stack_control_panel.setCurrentIndex(index_current_navitems)
        
    def build_stack_widget(self):
        """Собирает стек страниц: порядок страниц = порядок пунктов навигации."""
        self._pages = {_ITEMS_NAVLIST[0]: self.power_panel,
                       _ITEMS_NAVLIST[2]: self.frame_viewer}
        for item in _ITEMS_NAVLIST:
            # пункт без своей страницы — пустая заглушка, чтобы индексы стека
            # совпадали с индексами навигации
            page = self._pages.get(item)
            self._parent.stack_control_panel.addWidget(page if page is not None
                                                       else QtWidgets.QWidget())