from dark_pro_widgets.widgets.controls.nav_list import NavList


class ControlNavList():
    def __init__(self, parent):
        self.parent = parent
        self.navlist = NavList()
        
        
    def build_navlist(self):
        nav_items = ["Контроль питания", "Журнал событий", "Просмотрщик кадров", "Тестирование"]
        self.navlist.set_items(nav_items)
