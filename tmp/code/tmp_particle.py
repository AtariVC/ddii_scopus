


class Particle:
    def __init__(self):
        th_energy_el = 0.1 # MeV
        up_level_energy_el = 2 # MeV
        pass
    def electron_flux(self):
        pass

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