"""
PlotGenerator: creates static PNG figures from simulation results.

Figures produced
----------------
  1. io_voltage.png         Input vs output voltage vs time
  2. section_voltages.png   Voltage at selected nodes vs time
  3. max_voltage.png        Peak voltage at each node (bar chart)
  4. gradient.png           Peak voltage gradient between adjacent nodes
  5. heatmap.png            2D map: time (x) × position (y), voltage (color)
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_STYLE = {
    "figure.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "legend.fontsize": 9,
    "lines.linewidth": 1.5,
}


class PlotGenerator:
    """Generates and saves all static figures."""

    def __init__(self, results: dict, derived: dict, output_dir: str):
        self.res = results
        self.drv = derived
        self.fig_dir = os.path.join(output_dir, "figures")
        os.makedirs(self.fig_dir, exist_ok=True)
        plt.rcParams.update(_STYLE)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def _t_us(self):
        return self.res["t"] * 1e6  # time in µs

    def _save(self, fig: plt.Figure, name: str):
        path = os.path.join(self.fig_dir, name)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"    Saved: {name}")

    def _model_label(self) -> str:
        cfg = self.res["config"]
        return f"{cfg.model_type.upper()}-model  ({cfg.n_sections} sections)"

    # ------------------------------------------------------------------
    # Figure 1: Input / output voltage
    # ------------------------------------------------------------------

    def plot_io_voltage(self) -> None:
        t_us = self._t_us()
        V_in = self.drv["V_in"]
        V_out = self.drv["V_out"]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(t_us, V_in, label="Input  (node 0)", color="tab:blue")
        ax.plot(t_us, V_out, label="Output (node N)", color="tab:red", linestyle="--")
        ax.set_xlabel("Time [µs]")
        ax.set_ylabel("Voltage [V]")
        ax.set_title(f"Input vs Output Voltage — {self._model_label()}")
        ax.legend()
        ax.grid(True)
        fig.tight_layout()
        self._save(fig, "io_voltage.png")

    # ------------------------------------------------------------------
    # Figure 2: Selected node voltages
    # ------------------------------------------------------------------

    def plot_section_voltages(self) -> None:
        t_us = self._t_us()
        V = self.res["V_nodes"]
        pos = self.res["positions"]
        n_nodes = V.shape[0]

        # Pick ~6 representative nodes (always include first and last)
        indices = np.unique(
            np.round(np.linspace(0, n_nodes - 1, min(6, n_nodes))).astype(int)
        )

        # matplotlib.colormaps substitui cm.get_cmap (deprecado, remoção na 3.11)
        cmap = matplotlib.colormaps["plasma"].resampled(len(indices))
        fig, ax = plt.subplots(figsize=(8, 4))
        for idx_i, node in enumerate(indices):
            pct = pos[node] * 100
            label = f"x = {pct:.0f} %"
            ax.plot(t_us, V[node, :], label=label, color=cmap(idx_i))

        ax.set_xlabel("Time [µs]")
        ax.set_ylabel("Voltage [V]")
        ax.set_title(f"Voltage at Selected Nodes — {self._model_label()}")
        ax.legend()
        ax.grid(True)
        fig.tight_layout()
        self._save(fig, "section_voltages.png")

    # ------------------------------------------------------------------
    # Figure 3: Peak voltage per node
    # ------------------------------------------------------------------

    def plot_max_voltage(self) -> None:
        V_max = self.drv["V_max_per_node"]
        pos = self.drv["positions"] * 100   # %

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(pos, V_max, width=100 / max(len(pos), 1), color="steelblue", edgecolor="navy")
        ax.set_xlabel("Position along coil [%]")
        ax.set_ylabel("Peak voltage [V]")
        ax.set_title(f"Peak Voltage per Node — {self._model_label()}")
        ax.set_xlim(-5, 105)
        ax.grid(axis="y")
        fig.tight_layout()
        self._save(fig, "max_voltage.png")

    # ------------------------------------------------------------------
    # Figure 4: Peak voltage gradient between adjacent nodes
    # ------------------------------------------------------------------

    def plot_gradient(self) -> None:
        dV = self.drv["dV_max_per_gap"]
        pos = self.drv["positions"]
        mid_pos = (pos[:-1] + pos[1:]) / 2 * 100   # midpoint between adjacent nodes [%]

        # T model with open termination: the last gap (midpoint -> output)
        # is structurally zero (both points share the same state variable),
        # so it is omitted instead of plotted as a misleading zero bar.
        cfg = self.res["config"]
        note = ""
        if cfg.model_type.lower() == "t" and cfg.termination.lower() == "open":
            dV, mid_pos = dV[:-1], mid_pos[:-1]
            note = "\n(last gap omitted: output node = last midpoint in open-circuit T)"

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(mid_pos, dV, width=100 / max(len(mid_pos), 1),
               color="orangered", edgecolor="darkred")
        ax.set_xlabel("Position along coil [%]")
        ax.set_ylabel("Peak |ΔV| between adjacent nodes [V]")
        ax.set_title(
            f"Voltage Gradient between Adjacent Nodes — {self._model_label()}{note}",
            fontsize=10 if note else None,
        )
        ax.set_xlim(-5, 105)
        ax.grid(axis="y")
        fig.tight_layout()
        self._save(fig, "gradient.png")

    # ------------------------------------------------------------------
    # Figure 5: 2D heatmap time × position
    # ------------------------------------------------------------------

    def plot_heatmap(self) -> None:
        t_us = self._t_us()
        V = self.res["V_nodes"]        # (n_nodes, n_time)
        pos = self.res["positions"] * 100   # %

        fig, ax = plt.subplots(figsize=(9, 5))
        vmax = np.max(np.abs(V))
        im = ax.pcolormesh(
            t_us, pos, V,
            cmap="RdBu_r",
            vmin=-vmax, vmax=vmax,
            shading="auto",
        )
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Voltage [V]")
        ax.set_xlabel("Time [µs]")
        ax.set_ylabel("Position along coil [%]")
        ax.set_title(f"Voltage Distribution Map — {self._model_label()}")
        fig.tight_layout()
        self._save(fig, "heatmap.png")

    # ------------------------------------------------------------------
    # Run all
    # ------------------------------------------------------------------

    def plot_all(self) -> None:
        print("  Generating static figures ...")
        self.plot_io_voltage()
        self.plot_section_voltages()
        self.plot_max_voltage()
        self.plot_gradient()
        self.plot_heatmap()
