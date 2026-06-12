"""
ImpulseSource: parametric surge/impulse voltage waveform.

Two waveform types are supported:

  double_exp  (default, suitable for lightning/switching impulse studies)
  ─────────────────────────────────────────────────────────────────────
  V(t) = V_amplitude * K * (exp(-alpha*t) - exp(-beta*t))

  alpha  = ln(2) / t_tail          (controls tail)
  beta   = 3.0  / t_front          (controls front)

  K is a normalisation constant chosen so that peak(V) = V_amplitude.

  For a standard 1.2/50 µs lightning impulse (IEC 60060-1):
    alpha ≈ 1.39 × 10^4 s^-1,  beta ≈ 2.5 × 10^6 s^-1

  ramp_exp  (simple ramp-then-decay, occasionally used for switching surges)
  ─────────────────────────────────────────────────────────────────────
  V(t) = V_amplitude * t / t_front             for t <= t_front
  V(t) = V_amplitude * exp(-(t-t_front)/t_tail) for t > t_front
"""

import numpy as np

# Relação empírica do coeficiente de frente da dupla exponencial:
# beta ~= FRONT_COEFF / T1 reproduz o tempo de frente IEC T1 = 1,67*(t90-t30)
# dentro das tolerâncias da IEC 60060-1 para o impulso 1,2/50 us
# (verificado em tests/test_impulse_source.py: T1 = 1,193 us, desvio -0,6 %).
FRONT_COEFF = 3.0


class ImpulseSource:
    """Callable surge waveform.  Call instance with a scalar or array time."""

    def __init__(
        self,
        source_type: str = "double_exp",
        amplitude: float = 1000.0,
        t_front: float = 1.2e-6,
        t_tail: float = 50e-6,
    ):
        self.source_type = source_type.lower()
        self.amplitude = amplitude
        self.t_front = t_front
        self.t_tail = t_tail

        if self.source_type not in ("double_exp", "ramp_exp"):
            raise ValueError(f"Unknown source_type '{source_type}'.")

        if self.source_type == "double_exp":
            self._setup_double_exp()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_double_exp(self):
        # tail coefficient: the slow exponential alone decays 50 % at t_tail
        # => alpha = ln2 / t_tail (the composite waveform's IEC half-value
        # time comes out ~5 % longer; see README "Hipóteses")
        self.alpha = np.log(2.0) / self.t_tail
        # front coefficient: empirical relation beta ≈ FRONT_COEFF / t_front
        self.beta = FRONT_COEFF / self.t_front

        # normalisation: ensure peak == amplitude
        t_peak = np.log(self.beta / self.alpha) / (self.beta - self.alpha)
        f_peak = np.exp(-self.alpha * t_peak) - np.exp(-self.beta * t_peak)
        self._K = 1.0 / f_peak   # multiply waveform by amplitude * _K

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def __call__(self, t: float) -> float:
        """Return source voltage at scalar time t [s]."""
        if t < 0.0:
            return 0.0
        if self.source_type == "double_exp":
            return float(
                self.amplitude
                * self._K
                * (np.exp(-self.alpha * t) - np.exp(-self.beta * t))
            )
        else:  # ramp_exp
            if t <= self.t_front:
                return self.amplitude * t / self.t_front
            return self.amplitude * np.exp(-(t - self.t_front) / self.t_tail)

    def evaluate_array(self, t_array: np.ndarray) -> np.ndarray:
        """Vectorised evaluation over a time array."""
        if self.source_type == "double_exp":
            t = np.asarray(t_array, dtype=float)
            v = self.amplitude * self._K * (
                np.exp(-self.alpha * t) - np.exp(-self.beta * t)
            )
            v[t < 0] = 0.0
            return v
        else:
            t = np.asarray(t_array, dtype=float)
            v = np.where(
                t <= self.t_front,
                self.amplitude * t / self.t_front,
                self.amplitude * np.exp(-(t - self.t_front) / self.t_tail),
            )
            v[t < 0] = 0.0
            return v

    @property
    def peak_time(self) -> float:
        if self.source_type == "double_exp":
            return np.log(self.beta / self.alpha) / (self.beta - self.alpha)
        return self.t_front

    def __repr__(self) -> str:
        return (
            f"ImpulseSource(type={self.source_type}, "
            f"V={self.amplitude:.0f} V, "
            f"T1={self.t_front*1e6:.2f} us, "
            f"T2={self.t_tail*1e6:.0f} us)"
        )
