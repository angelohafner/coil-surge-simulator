"""
TimeDomainSolver: integrates the coil ODE system using scipy's RK45 solver.

Formulation
-----------
The coil network is cast as a first-order ODE system:

    dx/dt = f(t, x)

where x is the state vector (inductor currents + capacitor voltages).
scipy.integrate.solve_ivp with method='RK45' provides adaptive step-size
control; the t_eval array forces output at equally-spaced reporting points.

The solver returns a Results dict containing:
  t          : time array [s]
  V_source   : source voltage at each time step [V]
  V_nodes    : node voltages, shape (n_nodes, n_time)
  I_sections : section currents, shape (n_sections, n_time)
  positions  : normalised position along coil [0,1] for each node
  raw_y      : raw ODE solution matrix (state vector history)
"""

import numpy as np
from scipy.integrate import solve_ivp

from ..models.distributed_coil import DistributedCoil
from ..sources.impulse_source import ImpulseSource
from ..utils.simulation_config import SimulationConfig


class TimeDomainSolver:
    """Runs the time-domain ODE simulation for a DistributedCoil."""

    def __init__(
        self,
        coil: DistributedCoil,
        source: ImpulseSource,
        config: SimulationConfig,
    ):
        self.coil = coil
        self.source = source
        self.config = config

    # ------------------------------------------------------------------
    # Main solve
    # ------------------------------------------------------------------

    def solve(self) -> dict:
        """
        Integrate the ODE and return a results dictionary.
        Raises RuntimeError if the solver fails.
        """
        cfg = self.config
        t_eval = np.arange(0.0, cfg.t_total + cfg.dt / 2, cfg.dt)

        x0 = self.coil.initial_state()

        print(
            f"  Solver  : RK45 | state size = {self.coil.state_size()} | "
            f"steps = {len(t_eval)}"
        )

        sol = solve_ivp(
            fun=lambda t, x: self.coil.derivatives(t, x, self.source),
            t_span=(0.0, t_eval[-1]),
            y0=x0,
            method="RK45",
            t_eval=t_eval,
            rtol=1e-7,
            atol=1e-12,
            dense_output=False,
        )

        if not sol.success:
            raise RuntimeError(f"ODE solver failed: {sol.message}")

        print(f"  Done.   ODE evaluations: {sol.nfev}")
        return self._extract(sol.t, sol.y)

    # ------------------------------------------------------------------
    # Result extraction
    # ------------------------------------------------------------------

    def _extract(self, t: np.ndarray, y: np.ndarray) -> dict:
        """Build the results dict from the raw ODE output."""
        n_time = len(t)
        n = self.coil.n

        V_source = self.source.evaluate_array(t)

        positions = self.coil.node_positions()  # shape (n_nodes,)
        n_nodes = len(positions)

        V_nodes = np.empty((n_nodes, n_time))
        for i in range(n_time):
            V_nodes[:, i] = self.coil.node_voltages(t[i], y[:, i], self.source)

        # Section currents: shape (n_sec_currents, n_time)
        I_list = [self.coil.section_currents(y[:, i]) for i in range(n_time)]
        I_sections = np.array(I_list).T   # (n_currents, n_time)

        return {
            "t": t,
            "V_source": V_source,
            "V_nodes": V_nodes,       # (n_nodes, n_time)
            "I_sections": I_sections, # (n_currents, n_time)
            "positions": positions,   # (n_nodes,)
            "raw_y": y,
            "config": self.config,
            "model_type": self.config.model_type,
            "n_sections": n,
        }
