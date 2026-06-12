"""
ResultProcessor: computes derived quantities from simulation results
and saves CSV files.

Derived quantities
------------------
  V_max_per_node  : peak |voltage| at each node over the entire simulation
  dV_max_per_gap  : peak |voltage gradient| between adjacent nodes
  V_in            : input terminal voltage time series
  V_out           : output terminal voltage time series
  transfer_ratio  : max(|V_out|) / max(|V_in|)

CSV files (data dictionary in README.md)
----------------------------------------
  node_voltages.csv    time_s + one column per node. Pi: V_source,
                       V_node_1..N. T: V_source, V_mid_0..N-1, V_out.
  section_currents.csv time_s + currents. Pi: I_sec_1..N. T:
                       I_junction_0..N-1, I_out (I_out = 0 by definition
                       with open termination).
  summary_nodes.csv    per-node table: node_idx, position_norm, V_max_V,
                       dV_max_V (gap to the NEXT node; last row has no
                       next node -> empty). For the open-circuit T model
                       the last physical gap (mid_N-1 -> output) is
                       structurally zero because both points carry the
                       same state variable; it is reported EMPTY, not 0,
                       to avoid reading it as "no dielectric stress".
  summary_scalars.csv  key,value pairs: transfer_ratio, V_peak_in_V,
                       V_peak_out_V.
"""

import os
import csv
import numpy as np


class ResultProcessor:
    """Processes simulation results and saves them to disk."""

    def __init__(self, results: dict, output_dir: str):
        self.results = results
        self.csv_dir = os.path.join(output_dir, "csv")
        os.makedirs(self.csv_dir, exist_ok=True)
        self._derived: dict | None = None

    # ------------------------------------------------------------------
    # Column naming (honest, model-aware headers)
    # ------------------------------------------------------------------

    def _model_termination(self) -> tuple[str, str]:
        cfg = self.results["config"]
        return cfg.model_type.lower(), cfg.termination.lower()

    def _node_names(self) -> list[str]:
        n = self.results["n_sections"]
        model, _term = self._model_termination()
        if model == "pi":
            return ["V_source"] + [f"V_node_{k}" for k in range(1, n + 1)]
        return ["V_source"] + [f"V_mid_{k}" for k in range(n)] + ["V_out"]

    def _current_names(self) -> list[str]:
        n = self.results["n_sections"]
        model, _term = self._model_termination()
        if model == "pi":
            return [f"I_sec_{k}" for k in range(1, n + 1)]
        return [f"I_junction_{k}" for k in range(n)] + ["I_out"]

    # ------------------------------------------------------------------
    # Derived quantities
    # ------------------------------------------------------------------

    def compute_derived(self) -> dict:
        if self._derived is not None:
            return self._derived

        V = self.results["V_nodes"]       # (n_nodes, n_time)
        t = self.results["t"]
        pos = self.results["positions"]

        V_max = np.max(np.abs(V), axis=1)        # peak at each node
        dV = np.diff(V, axis=0)                  # (n_nodes-1, n_time)
        dV_max = np.max(np.abs(dV), axis=1)

        # T model, open circuit: the output node repeats the last midpoint
        # state, so the last gap is structurally zero. Report it as nan so
        # it cannot be misread as "no dielectric stress at the coil end".
        model, term = self._model_termination()
        if model == "t" and term == "open" and len(dV_max) > 0:
            dV_max = dV_max.copy()
            dV_max[-1] = np.nan

        V_in = V[0, :]
        V_out = V[-1, :]

        Vpk_in = np.max(np.abs(V_in))
        Vpk_out = np.max(np.abs(V_out))
        ratio = Vpk_out / Vpk_in if Vpk_in > 0.0 else float("nan")

        self._derived = {
            "V_max_per_node": V_max,
            "dV_max_per_gap": dV_max,
            "V_in": V_in,
            "V_out": V_out,
            "Vpk_in": Vpk_in,
            "Vpk_out": Vpk_out,
            "transfer_ratio": ratio,
            "t": t,
            "positions": pos,
        }
        return self._derived

    # ------------------------------------------------------------------
    # CSV saving
    # ------------------------------------------------------------------

    def save_csv(self) -> None:
        self.compute_derived()
        self._save_node_voltages()
        self._save_section_currents()
        self._save_summary_nodes()
        self._save_summary_scalars()
        print(f"  CSVs saved -> {self.csv_dir}")

    def _save_node_voltages(self):
        V = self.results["V_nodes"]
        t = self.results["t"]
        header = ["time_s"] + self._node_names()
        data = np.column_stack([t, V.T])
        self._write(os.path.join(self.csv_dir, "node_voltages.csv"), header, data)

    def _save_section_currents(self):
        I = self.results["I_sections"]
        t = self.results["t"]
        header = ["time_s"] + self._current_names()
        data = np.column_stack([t, I.T])
        self._write(os.path.join(self.csv_dir, "section_currents.csv"), header, data)

    def _save_summary_nodes(self):
        d = self._derived
        path = os.path.join(self.csv_dir, "summary_nodes.csv")
        n_nodes = len(d["V_max_per_node"])
        n_gaps = len(d["dV_max_per_gap"])
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["node_idx", "position_norm", "V_max_V", "dV_max_V"])
            for i in range(n_nodes):
                if i < n_gaps and np.isfinite(d["dV_max_per_gap"][i]):
                    gap = f"{d['dV_max_per_gap'][i]:.4f}"
                else:
                    gap = ""    # sem vão seguinte ou vão estrutural (T aberto)
                w.writerow([i, f"{d['positions'][i]:.4f}",
                            f"{d['V_max_per_node'][i]:.4f}", gap])

    def _save_summary_scalars(self):
        d = self._derived
        path = os.path.join(self.csv_dir, "summary_scalars.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["transfer_ratio", f"{d['transfer_ratio']:.6f}"])
            w.writerow(["V_peak_in_V", f"{d['Vpk_in']:.4f}"])
            w.writerow(["V_peak_out_V", f"{d['Vpk_out']:.4f}"])

    @staticmethod
    def _write(path: str, header: list, data: np.ndarray):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            for row in data:
                w.writerow([f"{v:.8g}" for v in row])
