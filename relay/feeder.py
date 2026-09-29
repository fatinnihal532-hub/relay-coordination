"""Radial feeder model and fault calculation (ohmic method, 11 kV base)."""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class Feeder:
    kv: float                     # feeder nominal voltage, kV
    source_mva_max: float         # upstream 33 kV fault level, maximum plant
    source_mva_min: float         # upstream 33 kV fault level, minimum plant
    source_xr: float
    tx_mva: float                 # 33/11 kV power transformer
    tx_z_pct: float
    tx_xr: float
    buses: list                   # names, from the substation outwards
    sections: list                # (length km, r ohm/km, x ohm/km) between consecutive buses
    loads_mva: list               # load connected at each bus
    relays: list = field(default_factory=list)   # (name, bus index, load A, overload factor), source side first

    def _z_source(self, mva):
        z = self.kv ** 2 / mva
        r = z / np.sqrt(1 + self.source_xr ** 2)
        return complex(r, r * self.source_xr)

    def _z_tx(self):
        z = self.tx_z_pct / 100 * self.kv ** 2 / self.tx_mva
        r = z / np.sqrt(1 + self.tx_xr ** 2)
        return complex(r, r * self.tx_xr)

    def z_to_bus(self, i, case="max"):
        """Thevenin impedance (ohm, at feeder voltage) seen from bus i."""
        z = self._z_source(self.source_mva_max if case == "max" else self.source_mva_min) + self._z_tx()
        for L, r, x in self.sections[:i]:
            z += L * complex(r, x)
        return z

    def fault_3ph(self, i, case="max", c=1.1):
        """Three-phase fault current (A); c is the IEC 60909 voltage factor (1.1 max, 1.0 min)."""
        return c * self.kv * 1e3 / np.sqrt(3) / abs(self.z_to_bus(i, case))

    def fault_2ph_min(self, i):
        """Minimum fault: phase-to-phase at minimum plant, c = 1.0 (sensitivity check)."""
        return np.sqrt(3) / 2 * self.fault_3ph(i, "min", c=1.0)

    def load_downstream(self, i):
        """Load current (A) through a breaker at bus i feeding the line towards bus i+1."""
        mva = sum(self.loads_mva[i + 1:])
        return mva * 1e3 / (np.sqrt(3) * self.kv)

    def tx_rated_current(self):
        return self.tx_mva * 1e3 / (np.sqrt(3) * self.kv)


def default_feeder():
    """A 33/11 kV substation feeding a radial 11 kV overhead line.

    Typical values for Bangladesh distribution networks: 20/26 MVA 33/11 kV transformer
    (10% impedance), 11 kV overhead line on ACSR 'Dog' conductor, and a 500 MVA (max) /
    250 MVA (min) fault level on the 33 kV side."""
    f = Feeder(
        kv=11.0,
        source_mva_max=500.0, source_mva_min=250.0, source_xr=10.0,
        tx_mva=20.0, tx_z_pct=10.0, tx_xr=15.0,
        buses=["SS 11 kV bus", "Section A", "Section B", "Section C"],
        # ACSR Dog, 100 mm2: about 0.273 + j0.363 ohm/km at 50 Hz
        sections=[(4.0, 0.273, 0.363), (5.0, 0.273, 0.363), (6.0, 0.273, 0.363)],
        loads_mva=[0.0, 3.0, 2.5, 2.0],
    )
    f.relays = [
        ("Incomer (transformer LV)", 0, f.tx_rated_current(), 1.25),
        ("Feeder breaker", 0, f.load_downstream(0), 1.5),
        ("Recloser A", 1, f.load_downstream(1), 1.5),
        ("Recloser B", 2, f.load_downstream(2), 1.5),
    ]
    return f
