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
        frequency: float = 20000.0,
    ):
        self.source_type = source_type.lower()
        self.amplitude = amplitude
        self.t_front = t_front
        self.t_tail = t_tail
        self.frequency = frequency

        if self.source_type not in ("double_exp", "ramp_exp", "square"):
            raise ValueError(f"Unknown source_type '{source_type}'.")

        if self.source_type == "double_exp":
            self._setup_double_exp()
        elif self.source_type == "square":
            self._setup_square()

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

    def _setup_square(self):
        # Onda quadrada unipolar 0 -> amplitude, periodo T = 1/frequency, com
        # bordas trapezoidais de duracao t_rise (= t_front).  dv/dt = A/t_rise.
        if self.frequency <= 0.0:
            raise ValueError("square source requires frequency > 0.")
        self._T = 1.0 / self.frequency
        self._t_rise = self.t_front
        if self._t_rise <= 0.0 or self._t_rise >= self._T / 2.0:
            raise ValueError(
                "square source requires 0 < t_front (edge time) < T/2."
            )

    def _square_value(self, t: float) -> float:
        A, T, tr = self.amplitude, self._T, self._t_rise
        tl = t - np.floor(t / T) * T          # t modulo T (robusto para float)
        if tl < tr:
            return float(A * tl / tr)         # borda de subida
        if tl < T / 2.0:
            return float(A)                   # plato alto
        if tl < T / 2.0 + tr:
            return float(A * (1.0 - (tl - T / 2.0) / tr))   # borda de descida
        return 0.0                            # plato baixo

    def _square_deriv(self, t: float) -> float:
        A, T, tr = self.amplitude, self._T, self._t_rise
        tl = t - np.floor(t / T) * T
        if tl < tr:
            return float(A / tr)
        if tl < T / 2.0:
            return 0.0
        if tl < T / 2.0 + tr:
            return float(-A / tr)
        return 0.0

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
        elif self.source_type == "square":
            return self._square_value(t)
        else:  # ramp_exp
            if t <= self.t_front:
                return self.amplitude * t / self.t_front
            return self.amplitude * np.exp(-(t - self.t_front) / self.t_tail)

    def derivative(self, t: float) -> float:
        """Analytic time-derivative dV/dt at scalar time t [s].

        Needed when the coil model includes series capacitance: the
        series branch tying the input node to the source injects a
        current C_s * dV_src/dt into the first node.
        """
        if t < 0.0:
            return 0.0
        if self.source_type == "double_exp":
            return float(
                self.amplitude
                * self._K
                * (self.beta * np.exp(-self.beta * t)
                   - self.alpha * np.exp(-self.alpha * t))
            )
        elif self.source_type == "square":
            return self._square_deriv(t)
        else:  # ramp_exp
            if t <= self.t_front:
                return self.amplitude / self.t_front
            return float(
                -self.amplitude / self.t_tail
                * np.exp(-(t - self.t_front) / self.t_tail)
            )

    def evaluate_array(self, t_array: np.ndarray) -> np.ndarray:
        """Vectorised evaluation over a time array."""
        if self.source_type == "double_exp":
            t = np.asarray(t_array, dtype=float)
            v = self.amplitude * self._K * (
                np.exp(-self.alpha * t) - np.exp(-self.beta * t)
            )
            v[t < 0] = 0.0
            return v
        elif self.source_type == "square":
            t = np.asarray(t_array, dtype=float)
            A, T, tr = self.amplitude, self._T, self._t_rise
            tl = t - np.floor(t / T) * T
            v = np.zeros_like(t)
            rise = tl < tr
            high = (tl >= tr) & (tl < T / 2.0)
            fall = (tl >= T / 2.0) & (tl < T / 2.0 + tr)
            v[rise] = A * tl[rise] / tr
            v[high] = A
            v[fall] = A * (1.0 - (tl[fall] - T / 2.0) / tr)
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
        if self.source_type == "square":
            return self._t_rise
        return self.t_front

    def __repr__(self) -> str:
        return (
            f"ImpulseSource(type={self.source_type}, "
            f"V={self.amplitude:.0f} V, "
            f"T1={self.t_front*1e6:.2f} us, "
            f"T2={self.t_tail*1e6:.0f} us)"
        )
