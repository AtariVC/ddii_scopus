"""AI is creating summary for
"""

class Pips:
    """Эмулятор pips детектора
    """
    def __init__(self) -> None:
        self.e_to_q: float = 3.6 # eV/1e
        self.dl_pips: float = 0.3 # thickness [mm]
        self.tau_pips: float = 50 * 10**-9 # time constant [s]
        self.t_pips: float = 0.1 # threhold [MeV]

    def signal(self):
        pass

    def count_particle(self, ):
        pass