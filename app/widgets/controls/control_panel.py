from dark_pro_widgets.widgets.controls.nav_list import NavList
from app.widgets.controls.power import PowerControlWidget
from PyQt6 import QtWidgets


_ITEMS_NAVLIST = ["Контроль питания", "Журнал событий", "Просмотрщик кадров", "Тестирование"]

class ControlPanel(NavList):

    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        self._pages = {}
        self.mok_widget = QtWidgets.QWidget()
        self.power_panel = PowerControlWidget(self._parent.client)
        self.build_navlist()
        self.sectionChanged.connect(self.on_screen_changed)

    def build_navlist(self):
        nav_items = _ITEMS_NAVLIST
        self.set_items(nav_items)
        
    def on_screen_changed(self):
        index_current_navitems = self.current_index()
        self._parent.stack_control_panel.setCurrentIndex(index_current_navitems)
        
    def build_stack_widget(self):
        self._pages = {_ITEMS_NAVLIST[0]: self.power_panel}
        for widget in self._pages.values():
            self._parent.stack_control_panel.addWidget(widget)
        for item in _ITEMS_NAVLIST:
            if item not in self._pages.keys():
                self._parent.stack_control_panel.addWidget(self.mok_widget)

    