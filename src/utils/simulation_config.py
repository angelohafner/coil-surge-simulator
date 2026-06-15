"""
SimulationConfig: central dataclass holding all simulation parameters.
Load from JSON or create programmatically.

All parameters are validated on construction (__post_init__): invalid
values raise ValueError listing every problem found, so a typo in the
JSON cannot silently change the physics of the study (see audit finding
A5: an invalid `termination` used to fall through to "resistive").
"""
import json
import warnings
from dataclasses import dataclass, asdict, field, fields

VALID_MODEL_TYPES = ("pi", "t")
VALID_SOURCE_TYPES = ("double_exp", "ramp_exp", "square")
VALID_TERMINATIONS = ("open", "resistive", "grounded")


@dataclass
class SimulationConfig:
    # Coil parameters
    n_sections: int = 20          # number of cascaded sections
    L_total: float = 0.01         # total inductance [H]
    R_total: float = 5.0          # total series resistance [Ohm]
    C_total: float = 1e-9         # total capacitance to ground [F]
    C_series_total: float = 0.0   # total series (turn-to-turn) capacitance [F];
                                  # 0.0 = disabled (shunt-only model, default).
                                  # When > 0 it couples adjacent nodes and makes
                                  # the t=0+ distribution non-uniform (~cosh/sinh).
    model_type: str = "pi"        # "pi" or "t"

    # Impulse source parameters
    source_type: str = "double_exp"
    V_amplitude: float = 1000.0   # peak voltage [V]
    t_front: float = 1.2e-6       # front time T1 [s]
    t_tail: float = 50e-6         # tail time T2 [s]

    # Time domain simulation
    t_total: float = 20e-6        # total simulation time [s]
    dt: float = 1e-8              # reporting time step [s]

    # ODE solver (scipy.integrate.solve_ivp)
    solver_method: str = "RK45"   # e.g. "RK45", "Radau" (stiff cases)
    rtol: float = 1e-7            # relative tolerance
    atol: float = 1e-12           # absolute tolerance

    # Output terminal condition
    termination: str = "open"     # "open", "resistive", or "grounded"
    R_term: float = 1e6           # termination resistance [Ohm]

    # Study scenarios run by main.py in addition to the base Pi/T cases:
    # one extra Pi case per multiplier, with C_total scaled by it
    c_scenario_multipliers: list = field(default_factory=lambda: [0.1, 10.0])

    # Output directory
    output_dir: str = "output"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def __post_init__(self):
        problems: list[str] = []

        if not isinstance(self.n_sections, int) or isinstance(self.n_sections, bool):
            problems.append(f"n_sections deve ser inteiro (recebido {self.n_sections!r})")
        elif self.n_sections < 1:
            problems.append(f"n_sections deve ser >= 1 (recebido {self.n_sections})")

        for name in ("L_total", "C_total", "V_amplitude", "t_front",
                     "t_tail", "t_total", "dt", "rtol", "atol"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or value <= 0:
                problems.append(f"{name} deve ser > 0 (recebido {value!r})")

        if not isinstance(self.R_total, (int, float)) or self.R_total < 0:
            problems.append(f"R_total deve ser >= 0 (recebido {self.R_total!r})")

        if not isinstance(self.C_series_total, (int, float)) or self.C_series_total < 0:
            problems.append(
                f"C_series_total deve ser >= 0 (recebido {self.C_series_total!r})")

        if str(self.model_type).lower() not in VALID_MODEL_TYPES:
            problems.append(
                f"model_type deve ser um de {VALID_MODEL_TYPES} (recebido {self.model_type!r})")
        if str(self.source_type).lower() not in VALID_SOURCE_TYPES:
            problems.append(
                f"source_type deve ser um de {VALID_SOURCE_TYPES} (recebido {self.source_type!r})")
        if str(self.termination).lower() not in VALID_TERMINATIONS:
            problems.append(
                f"termination deve ser um de {VALID_TERMINATIONS} (recebido {self.termination!r})")
        elif (str(self.termination).lower() == "resistive"
              and (not isinstance(self.R_term, (int, float)) or self.R_term <= 0)):
            problems.append(
                f"R_term deve ser > 0 quando termination='resistive' (recebido {self.R_term!r})")

        if (isinstance(self.dt, (int, float)) and isinstance(self.t_total, (int, float))
                and self.dt > 0 and self.t_total > 0 and self.dt >= self.t_total):
            problems.append(
                f"dt ({self.dt}) deve ser menor que t_total ({self.t_total})")

        if (not isinstance(self.c_scenario_multipliers, (list, tuple))
                or any(not isinstance(m, (int, float)) or m <= 0
                       for m in self.c_scenario_multipliers)):
            problems.append(
                "c_scenario_multipliers deve ser lista de números > 0 "
                f"(recebido {self.c_scenario_multipliers!r})")

        if problems:
            raise ValueError(
                "Configuração inválida:\n  - " + "\n  - ".join(problems))

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: str) -> "SimulationConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(
                f"Chaves desconhecidas em {path}: {unknown}. "
                f"Chaves válidas: {sorted(known)}")

        missing = sorted(known - set(data))
        if missing:
            defaults = {f.name: f.default for f in fields(cls)}
            detail = ", ".join(f"{k}={defaults[k]!r}" for k in missing)
            warnings.warn(
                f"{path}: chaves ausentes assumiram valor default: {detail}",
                stacklevel=2,
            )
        return cls(**data)

    def to_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    def copy_with(self, **kwargs) -> "SimulationConfig":
        """Return a new (re-validated) config with selected fields overridden."""
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
        ]
        if self.C_series_total > 0:
            alpha = math.sqrt(C / self.C_series_total)
            lines.append(
                f"Series C    : {self.C_series_total*1e12:.3f} pF   "
                f"alpha=sqrt(Cg/Cs)={alpha:.2f}"
            )
        lines += [
            f"Termination : {self.termination}",
            f"Impulse     : {self.V_amplitude:.0f} V  "
            f"{self.t_front*1e6:.1f}/{self.t_tail*1e6:.0f} us",
            f"t_total     : {self.t_total*1e6:.1f} us   dt : {self.dt*1e9:.1f} ns",
            f"Solver      : {self.solver_method}  rtol={self.rtol:.1e}  atol={self.atol:.1e}",
        ]
        return "\n".join(lines)
