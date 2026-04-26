"""
SimulationConfig: central dataclass holding all simulation parameters.
Load from JSON or create programmatically.
"""
import json
from dataclasses import dataclass, asdict


@dataclass
class SimulationConfig:
    # Coil parameters
    n_sections: int = 20          # number of cascaded sections
    L_total: float = 0.01         # total inductance [H]
    R_total: float = 5.0          # total series resistance [Ohm]
    C_total: float = 1e-9         # total capacitance to ground [F]
    model_type: str = "pi"        # "pi" or "t"

    # Impulse source parameters
    source_type: str = "double_exp"
    V_amplitude: float = 1000.0   # peak voltage [V]
    t_front: float = 1.2e-6       # front time T1 [s]
    t_tail: float = 50e-6         # tail time T2 [s]

    # Time domain simulation
    t_total: float = 50e-6        # total simulation time [s]
    dt: float = 1e-8              # reporting time step [s]

    # Output terminal condition
    termination: str = "open"     # "open" or "resistive"
    R_term: float = 1e6           # termination resistance [Ohm]

    # Output directory
    output_dir: str = "output"

    @classmethod
    def from_json(cls, path: str) -> "SimulationConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def copy_with(self, **kwargs) -> "SimulationConfig":
        """Return a new config with selected fields overridden."""
        d = asdict(self)
        d.update(kwargs)
        return SimulationConfig(**d)

    def summary(self) -> str:
        n = self.n_sections
        L, R, C = self.L_total, self.R_total, self.C_total
        import math
        Z0 = math.sqrt(L / C)
        tau = math.sqrt(L * C)
        lines = [
            f"Model       : {self.model_type.upper()} ({n} sections)",
            f"L_total     : {L*1e3:.3f} mH    R_total : {R:.2f} Ohm",
            f"C_total     : {C*1e12:.3f} pF",
            f"Surge Z     : {Z0:.1f} Ohm",
            f"Travel time : {tau*1e6:.3f} us",
            f"Termination : {self.termination}",
            f"Impulse     : {self.V_amplitude:.0f} V  "
            f"{self.t_front*1e6:.1f}/{self.t_tail*1e6:.0f} us",
            f"t_total     : {self.t_total*1e6:.1f} us   dt : {self.dt*1e9:.1f} ns",
        ]
        return "\n".join(lines)
