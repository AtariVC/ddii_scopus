"""AI is creating summary for
"""
class Sipm():
    """Эмулятор sipm детектора
    """
    def __init__(self) -> None:
        self.e_to_ph: float = 30666 # Ph/MeV
        self.dl_sipm: float = 3 # thickness [mm]
        self.gain_sipm: float =3.4 * 10**5 # SiPM gain
        self.tau_sipm: float = 100 * 10**-9 # time constant [s]
