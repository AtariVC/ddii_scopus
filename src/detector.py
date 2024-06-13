"""
Тестовый модуль эмуляции детектирования частицы

При попадании частицы в детектор, происходит рассчет глубины проникновения вглубь детектора
потери энергии.
"""
import pips
import sipm
import particles

class Detector:
    """Класс эмулятора эелектроно-протнного телескопа
    """
    def __init__(self) -> None:
        self.pips1 = pips.Pips
        self.sipm1 = sipm.Sipm
        self.pips2 = pips.Pips
        self.pips3 = pips.Pips
        self.pips4 = pips.Pips
        self.cherenkov = sipm.Sipm
        self.electrons = None
        self.protons = None
    
    

    