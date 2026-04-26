"""
CoilSection: data container for a single lumped section of the distributed coil.
Used by DistributedCoil to store per-section parameters.
"""
from dataclasses import dataclass


@dataclass
class CoilSection:
    """One Pi- or T-equivalent section of the coil."""
    index: int          # section index (0-based)
    L_sec: float        # section inductance [H]
    R_sec: float        # section series resistance [Ohm]
    C_sec: float        # section shunt capacitance to ground [F]
    model_type: str     # "pi" or "t"

    @property
    def L_half(self) -> float:
        return self.L_sec / 2.0

    @property
    def R_half(self) -> float:
        return self.R_sec / 2.0

    @property
    def C_half(self) -> float:
        return self.C_sec / 2.0

    def __repr__(self) -> str:
        return (
            f"CoilSection(idx={self.index}, model={self.model_type}, "
            f"L={self.L_sec:.3e} H, R={self.R_sec:.3e} Ohm, C={self.C_sec:.3e} F)"
        )
