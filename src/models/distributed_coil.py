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
  Grounded end: V_N = 0 is imposed at the reference node.

  KVL section k (1..N): L_sec * dI_k/dt = V_{k-1} - V_k - R_sec * I_k
    with V_0 = V_source(t)

  Series (turn-to-turn) capacitance (optional, config.C_series_total > 0):
    A capacitor C_s_sec is placed across each section's series branch
    (between node k-1 and node k), in parallel with L_sec/R_sec.  Its
    displacement current C_s_sec * d(V_{k-1}-V_k)/dt couples neighbouring
    nodes, so the nodal KCL is no longer diagonal:

        C @ dV/dt = i_net(I) + C_s_sec * dV_src/dt * e_0

    where C is a constant symmetric tridiagonal "mass" matrix (shunt on the
    diagonal, -C_s_sec on the off-diagonals).  It is LU-factored once at
    construction and back-solved each step.  With C_series_total == 0 the
    matrix is diagonal and the original shunt-only path is used verbatim,
    so results are bit-identical to the shunt-only model.

    The end-to-end equivalent series capacitance is C_series_total; N
    per-section capacitors in cascade give it, hence C_s_sec = N*C_series_total.
    This makes the discrete second difference converge to V'' = alpha^2 V
    with alpha = sqrt(C_total/C_series_total) (see initial_voltage_distribution
    and tests/test_initial_distribution.py).

T-model (N sections):
  Topology per section k (0-based):
    j_{k} --[L/2, R/2]--> m_k --[L/2, R/2]--> j_{k+1}
    m_k connected to ground via C_sec

  Junction nodes j_k (k=1..N-1) carry no shunt element.
  By KCL at junction: I_R[k] = I_L[k+1]  =>  one junction current per section,
  named i_junction_k.  (Naming note: earlier versions called these currents
  "alpha"/"beta", clashing with the impulse-source exponents alpha/beta —
  renamed after the audit, finding A11.)

  State (open circuit): x = [V_m0, ..., V_m(N-1), i_junction_0, ..., i_junction_{N-1}]  (2N,)
  State (resistive or grounded): x = above + [i_out]  (2N+1,)
    where i_out = I_R[N-1] is the output current through the last right half-inductor

  KCL midpoint k=0..N-2: C_sec * dV_mk/dt = i_junction_k - i_junction_{k+1}
  KCL midpoint k=N-1 (open): C_sec * dV_m(N-1)/dt = i_junction_{N-1}
  KCL midpoint k=N-1 (R_t or grounded):
    C_sec * dV_m(N-1)/dt = i_junction_{N-1} - i_out

  KVL i_junction_0 (left half, section 0):
    (L/2) * d(i_junction_0)/dt = V_src - V_m0 - (R/2)*i_junction_0

  KVL i_junction_k (k=1..N-1, combined right half of section k-1 + left half of section k):
    L * d(i_junction_k)/dt = V_m(k-1) - V_mk - R*i_junction_k

  KVL i_out (right half, last section, resistive or grounded):
    (L/2) * d(i_out)/dt = V_m(N-1) - (R_term + R/2)*i_out
    with R_term = 0 for a grounded output terminal

  Output voltage:
    Open:      V_out = V_m(N-1)   (no drop across zero-current right half)
    Resistive: V_out = R_term * i_out
    Grounded:  V_out = 0
"""

import numpy as np
from scipy.linalg import lu_factor, lu_solve

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

        # Series (turn-to-turn) capacitance.  See module docstring for the
        # C_s_sec = N * C_series_total derivation.  Disabled (==0) by default,
        # in which case the shunt-only KCL path is used verbatim.
        self.C_series_total = config.C_series_total
        self.has_series_c = self.C_series_total > 0.0
        self.C_s_sec = self.n * self.C_series_total if self.has_series_c else 0.0
        self.alpha_dist = (
            float(np.sqrt(self.C / self.C_series_total))
            if self.has_series_c else float("inf")
        )

        self.sections = [
            CoilSection(k, self.L_sec, self.R_sec, self.C_sec, self.model_type)
            for k in range(self.n)
        ]

        # Tridiagonal nodal capacitance "mass" matrix (Pi model only),
        # LU-factored once and reused every derivative evaluation and by
        # initial_voltage_distribution.
        self._cap_lu = None
        self._n_v = 0
        if self.model_type == "pi" and self.has_series_c:
            self._build_pi_series_capacitance()

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
            if self.termination == "grounded":
                V[1:-1] = x[: n - 1]
                V[-1] = 0.0
            else:
                V[1:] = x[:n]
            return V
        else:
            V_m = x[:n]
            if self.termination == "open":
                V_out = V_m[-1]
            elif self.termination == "grounded":
                V_out = 0.0
            else:
                i_out = x[2 * n]
                V_out = self.R_term * i_out
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

    def initial_voltage_distribution(self, v_input: float = 1.0):
        """Electrostatic voltage distribution at t=0+ (Pi model).

        At the surge front the inductors block any current (I=0), so the
        voltage splits across the purely capacitive network formed by the
        series capacitance C_s between nodes and the shunt capacitance C_g
        to the reference.  Integrating C @ dV/dt = C_s_sec*dV_src/dt*e_0 over
        the infinitesimal front gives C @ V(0+) = C_s_sec * v_input * e_0, so
        the same LU-factored mass matrix that drives the ODE also yields the
        initial distribution.

        Returns (positions, voltages) over all Pi nodes 0..N, with the input
        node at v_input and the terminal set by the boundary condition.
        Requires config.C_series_total > 0 (otherwise the distribution is
        degenerate: all the voltage sits on the input node).
        """
        if self.model_type != "pi":
            raise NotImplementedError(
                "initial_voltage_distribution is implemented for the Pi model only.")
        if not self.has_series_c:
            raise ValueError(
                "initial_voltage_distribution requires C_series_total > 0 "
                "(without series capacitance the t=0+ distribution is degenerate).")

        n = self.n
        rhs = np.zeros(self._n_v)
        rhs[0] = self.C_s_sec * v_input
        v_active = lu_solve(self._cap_lu, rhs)

        v_full = np.empty(n + 1)
        v_full[0] = v_input
        if self.termination == "grounded":
            v_full[1:n] = v_active          # V_1 .. V_{N-1}
            v_full[n] = 0.0
        else:
            v_full[1:] = v_active           # V_1 .. V_N
        return self.node_positions(), v_full

    def section_currents(self, x: np.ndarray) -> np.ndarray:
        """
        Return inductor currents.
        Pi -> I_1..I_N.  T -> i_junction_0..i_junction_{N-1} + i_out
        (i_out is identically zero with open termination, by definition).
        """
        n = self.n
        if self.model_type == "pi":
            return x[n:].copy()          # I_1 .. I_N
        else:
            i_junction = x[n: 2 * n].copy()
            if self.termination == "open":
                i_out = np.array([0.0])
            else:
                i_out = np.array([x[2 * n]])
            return np.concatenate([i_junction, i_out])

    # ------------------------------------------------------------------
    # Series-capacitance helpers (Pi model)
    # ------------------------------------------------------------------

    def _build_pi_series_capacitance(self) -> None:
        """Assemble and LU-factor the tridiagonal nodal capacitance matrix.

        Active voltage nodes depend on the termination: 1..N for open/
        resistive (V_N is a state), 1..N-1 for grounded (V_N is pinned to 0).
        Diagonal = shunt capacitance + C_s_sec * (number of series branches
        touching the node); off-diagonals = -C_s_sec between adjacent active
        nodes.  The branch from the input node to node 1, and (grounded) from
        node N-1 to the reference, add to the diagonal but have no active
        off-diagonal partner.
        """
        n = self.n
        C, Cs = self.C_sec, self.C_s_sec

        if self.termination == "grounded":
            n_v = n - 1                      # V_1 .. V_{N-1}; V_N == 0
            shunt = np.full(n_v, C)
            series_count = np.full(n_v, 2.0) if n_v > 0 else np.zeros(0)
        else:
            n_v = n                          # V_1 .. V_N
            shunt = np.full(n_v, C)
            shunt[-1] = C / 2.0              # half Pi end-cap at the output node
            series_count = np.full(n_v, 2.0)
            series_count[-1] = 1.0           # node N has no section N+1

        self._n_v = n_v
        if n_v < 1:                          # degenerate (e.g. N=1 grounded)
            self._cap_lu = None
            return

        diag = shunt + Cs * series_count
        cap = np.diag(diag)
        if n_v > 1:
            off = -Cs * np.ones(n_v - 1)
            cap += np.diag(off, 1) + np.diag(off, -1)
        self._cap_matrix = cap
        self._cap_lu = lu_factor(cap)

    @staticmethod
    def _source_derivative(source_func, t: float) -> float:
        """dV_src/dt: analytic when the source exposes derivative(t),
        otherwise a central finite difference as a safe fallback."""
        deriv = getattr(source_func, "derivative", None)
        if deriv is not None:
            return float(deriv(t))
        h = 1e-11
        return float((source_func(t + h) - source_func(t - h)) / (2.0 * h))

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

        V_for_kvl = V.copy()
        if self.termination == "grounded":
            V_for_kvl[-1] = 0.0

        # KVL: L * dI_k/dt = V_{k-1} - V_k - R * I_k
        V_prev = np.empty(n)
        V_prev[0] = V_src
        V_prev[1:] = V_for_kvl[:-1]
        dxdt[n:] = (V_prev - V_for_kvl - R * I) / L

        # KCL.  Without series capacitance the nodal capacitance is diagonal
        # and the original shunt-only path runs verbatim (keeps the regression
        # bit-identical).  With series capacitance the nodes are coupled, so we
        # back-solve the pre-factored tridiagonal mass matrix instead.
        if not self.has_series_c:
            # KCL: C_node * dV_k/dt = I_k - I_{k+1}
            if self.termination == "grounded":
                if n > 1:
                    dxdt[: n - 1] = (I[: n - 1] - I[1:]) / C
                dxdt[n - 1] = 0.0
            else:
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

        # KCL with series capacitance:
        #   C @ dV/dt = i_net(I) + C_s_sec * dV_src/dt * e_0
        dV_src = self._source_derivative(source_func, t)
        if self.termination == "grounded":
            if self._n_v >= 1:
                i_net = (I[: n - 1] - I[1:]).astype(float)   # copy: don't touch x
                i_net[0] += self.C_s_sec * dV_src
                dxdt[: n - 1] = lu_solve(self._cap_lu, i_net)
            dxdt[n - 1] = 0.0
        else:
            I_next = np.empty(n)
            I_next[:-1] = I[1:]
            if self.termination == "open":
                I_next[-1] = 0.0
            else:
                I_next[-1] = V[-1] / self.R_term

            i_net = (I - I_next).astype(float)               # copy: don't touch x
            i_net[0] += self.C_s_sec * dV_src
            dxdt[:n] = lu_solve(self._cap_lu, i_net)

        return dxdt

    # ------------------------------------------------------------------
    # T-model ODE
    # ------------------------------------------------------------------

    def _deriv_t(self, t: float, x: np.ndarray, source_func) -> np.ndarray:
        n = self.n
        L, R, C = self.L_sec, self.R_sec, self.C_sec
        V_src = source_func(t)

        V_m = x[:n]            # midpoint voltages  V_m0 .. V_m(N-1)
        i_junc = x[n:2*n]      # junction currents  i_junction_0 .. i_junction_{N-1}

        open_circuit = (self.termination == "open")
        grounded_output = (self.termination == "grounded")
        size = self.state_size()
        dxdt = np.zeros(size)

        i_out = 0.0 if open_circuit else x[2 * n]

        # KCL at midpoints
        # i_junction_k flows in, i_junction_{k+1} (or i_out for last) flows out
        i_next = np.empty(n)
        i_next[:-1] = i_junc[1:]
        i_next[-1] = i_out
        dxdt[:n] = (i_junc - i_next) / C

        # KVL for i_junction_0 (left half of section 0, half-inductor):
        #   (L/2) * d(i_junction_0)/dt = V_src - V_m0 - (R/2)*i_junction_0
        dxdt[n] = (V_src - V_m[0] - (R / 2.0) * i_junc[0]) / (L / 2.0)

        # KVL for i_junction_k, k=1..N-1 (combined junction inductors = full L, R):
        #   L * d(i_junction_k)/dt = V_m(k-1) - V_mk - R*i_junction_k
        if n > 1:
            dxdt[n + 1: 2 * n] = (V_m[:-1] - V_m[1:] - R * i_junc[1:]) / L

        # KVL for i_out (right half of last section, half-inductor):
        #   (L/2) * d(i_out)/dt = V_m(N-1) - (R_term + R/2)*i_out
        #   use R_term = 0 for a grounded output terminal
        if not open_circuit:
            termination_resistance = 0.0 if grounded_output else self.R_term
            dxdt[2 * n] = (
                V_m[-1] - (termination_resistance + R / 2.0) * i_out
            ) / (L / 2.0)

        return dxdt
