from dark_pro_widgets.widgets.controls.nav_list import NavList
from app.widgets.controls.power import PowerControlWidget


_ITEMS_NAVLIST = ["Контроль питания", "Журнал событий", "Просмотрщик кадров", "Тестирование"]

class ControlPanel(NavList):

    def __init__(self, parent=None):
        super().__init__()
        self._parent = parent
        self._pages = {}
        self.power_panel = PowerControlWidget()
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
        self._parent.stack_control_panel.addWidget(self.power_panel)


    