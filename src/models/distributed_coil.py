"""
DistributedCoil: state-space model of a coil with N cascaded Pi or T sections.

Pi-model (N sections):
  Nodes: 0 (input, voltage imposed) ... N (output)
  State: x = [V_1, ..., V_N, I_1, ..., I_N]   shape: (2N,)

  Internal node k=1..N-1: capacitance = C_sec
  Output node k=N:        capacitance = C_sec/2 (half Pi end-cap)

  KCL node k (1..N-1): C_sec  * dV_k/dt = I_k - I_{k+1}
  KCL node N   (open): C_sec/2 * dV_N/dt = I_N
  KCL node N   (R_t):  C_sec/2 * dV_N/dt = I_N - V_N / R_term

  KVL section k (1..N): L_sec * dI_k/dt = V_{k-1} - V_k - R_sec * I_k
    with V_0 = V_source(t)

T-model (N sections):
  Topology per section k (0-based):
    j_{k} --[L/2, R/2]--> m_k --[L/2, R/2]--> j_{k+1}
    m_k connected to ground via C_sec

  Junction nodes j_k (k=1..N-1) carry no shunt element.
  By KCL at junction: I_R[k] = I_L[k+1]  =>  current at junction = alpha_{k+1}

  State (open circuit): x = [V_m0, ..., V_m(N-1), alpha_0, ..., alpha_{N-1}]  (2N,)
  State (resistive):    x = above + [beta]  (2N+1,)
    where beta = I_R[N-1] is the output current through the last right half-inductor

  KCL midpoint k=0..N-2: C_sec * dV_mk/dt = alpha_k - alpha_{k+1}
  KCL midpoint k=N-1 (open): C_sec * dV_m(N-1)/dt = alpha_{N-1}
  KCL midpoint k=N-1 (R_t):  C_sec * dV_m(N-1)/dt = alpha_{N-1} - beta

  KVL alpha_0 (left half, section 0):
    (L/2) * d(alpha_0)/dt = V_src - V_m0 - (R/2)*alpha_0

  KVL alpha_k (k=1..N-1, combined right half of section k-1 + left half of section k):
    L * d(alpha_k)/dt = V_m(k-1) - V_mk - R*alpha_k

  KVL beta (right half, last section, resistive only):
    (L/2) * d(beta)/dt = V_m(N-1) - (R_term + R/2)*beta

  Output voltage:
    Open:      V_out = V_m(N-1)   (no drop across zero-current right half)
    Resistive: V_out = R_term * beta
"""

import numpy as np
from .coil_section import CoilSection
from ..utils.simulation_config import SimulationConfig


class DistributedCoil:
    """Builds and evaluates the ODE right-hand side for the coil network."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.n = config.n_sections
        self.L = config.L_total
        self.R = config.R_total
        self.C = config.C_total
        self.model_type = config.model_type.lower()
        self.termination = config.termination.lower()
        self.R_term = config.R_term

        if self.model_type not in ("pi", "t"):
            raise ValueError(f"Unknown model_type '{config.model_type}'. Use 'pi' or 't'.")

        # Per-section values
        self.L_sec = self.L / self.n
        self.R_sec = self.R / self.n
        self.C_sec = self.C / self.n

        self.sections = [
            CoilSection(k, self.L_sec, self.R_sec, self.C_sec, self.model_type)
            for k in range(self.n)
        ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def state_size(self) -> int:
        if self.model_type == "pi":
            return 2 * self.n
        else:  # "t"
            return 2 * self.n + (0 if self.termination == "open" else 1)

    def initial_state(self) -> np.ndarray:
        return np.zeros(self.state_size())

    def derivatives(self, t: float, x: np.ndarray, source_func) -> np.ndarray:
        """Compute dx/dt.  source_func(t) returns the source voltage at time t."""
        if self.model_type == "pi":
            return self._deriv_pi(t, x, source_func)
        else:
            return self._deriv_t(t, x, source_func)

    def node_voltages(self, t: float, x: np.ndarray, source_func) -> np.ndarray:
        """
        Return the voltage at each 'node' for visualization.
        Pi  -> shape (N+1,)  positions 0..N
        T   -> shape (N+2,)  positions 0, m0..m(N-1), N (normalized 0-1)
        """
        V_src = source_func(t)
        n = self.n
        if self.model_type == "pi":
            V = np.empty(n + 1)
            V[0] = V_src
            V[1:] = x[:n]
            return V
        else:
            V_m = x[:n]
            if self.termination == "open":
                V_out = V_m[-1]
            else:
                beta = x[2 * n]
                V_out = self.R_term * beta
            V = np.empty(n + 2)
            V[0] = V_src
            V[1:-1] = V_m
            V[-1] = V_out
            return V

    def node_positions(self) -> np.ndarray:
        """Normalized positions [0, 1] along the coil for each node voltage."""
        n = self.n
        if self.model_type == "pi":
            return np.linspace(0.0, 1.0, n + 1)
        else:
            inner = (np.arange(n) + 0.5) / n
            return np.concatenate([[0.0], inner, [1.0]])

    def section_currents(self, x: np.ndarray) -> np.ndarray:
        """Return inductor currents per section."""
        n = self.n
        if self.model_type == "pi":
            return x[n:].copy()          # I_1 .. I_N
        else:
            alphas = x[n: 2 * n].copy()
            if self.termination == "open":
                beta = np.array([0.0])
            else:
                beta = np.array([x[2 * n]])
            return np.concatenate([alphas, beta])

    # ------------------------------------------------------------------
    # Pi-model ODE
    # ------------------------------------------------------------------

    def _deriv_pi(self, t: float, x: np.ndarray, source_func) -> np.ndarray:
        n = self.n
        L, R, C = self.L_sec, self.R_sec, self.C_sec
        V_src = source_func(t)

        V = x[:n]   # node voltages V_1 .. V_N
        I = x[n:]   # inductor currents I_1 .. I_N

        dxdt = np.empty(2 * n)

        # KVL: L * dI_k/dt = V_{k-1} - V_k - R * I_k
        V_prev = np.empty(n)
        V_prev[0] = V_src
        V_prev[1:] = V[:-1]
        dxdt[n:] = (V_prev - V - R * I) / L

        # KCL: C_node * dV_k/dt = I_k - I_{k+1}
        I_next = np.empty(n)
        I_next[:-1] = I[1:]
        if self.termination == "open":
            I_next[-1] = 0.0
        else:
            I_next[-1] = V[-1] / self.R_term

        C_node = np.full(n, C)
        C_node[-1] = C / 2.0   # half Pi end-cap at output terminal

        dxdt[:n] = (I - I_next) / C_node

        return dxdt

    # ------------------------------------------------------------------
    # T-model ODE
    # ------------------------------------------------------------------

    def _deriv_t(self, t: float, x: np.ndarray, source_func) -> np.ndarray:
        n = self.n
        L, R, C = self.L_sec, self.R_sec, self.C_sec
        V_src = source_func(t)

        V_m = x[:n]       # midpoint voltages  V_m0 .. V_m(N-1)
        alpha = x[n:2*n]  # left/junction currents  alpha_0 .. alpha_{N-1}

        open_circuit = (self.termination == "open")
        size = self.state_size()
        dxdt = np.zeros(size)

        beta = 0.0 if open_circuit else x[2 * n]

        # KCL at midpoints
        # alpha_k flows in, alpha_{k+1} (or beta for last) flows out
        alpha_out = np.empty(n)
        alpha_out[:-1] = alpha[1:]
        alpha_out[-1] = beta
        dxdt[:n] = (alpha - alpha_out) / C

        # KVL for alpha_0 (left half of section 0, half-inductor):
        #   (L/2) * d(alpha_0)/dt = V_src - V_m0 - (R/2)*alpha_0
        dxdt[n] = (V_src - V_m[0] - (R / 2.0) * alpha[0]) / (L / 2.0)

        # KVL for alpha_k, k=1..N-1 (combined junction inductors = full L, R):
        #   L * d(alpha_k)/dt = V_m(k-1) - V_mk - R*alpha_k
        if n > 1:
            dxdt[n + 1: 2 * n] = (V_m[:-1] - V_m[1:] - R * alpha[1:]) / L

        # KVL for beta (right half of last section, half-inductor):
        #   (L/2) * d(beta)/dt = V_m(N-1) - (R_term + R/2)*beta
        if not open_circuit:
            dxdt[2 * n] = (V_m[-1] - (self.R_term + R / 2.0) * beta) / (L / 2.0)

        return dxdt
