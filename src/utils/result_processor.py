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

        V_in = V[0, :]
        V_out = V[-1, :]

        Vpk_in = np.max(np.abs(V_in))
        Vpk_out = np.max(np.abs(V_out))
        ratio = Vpk_out / Vpk_in if Vpk_in > 1e-30 else 0.0

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
        self._save_summary()
        print(f"  CSVs saved -> {self.csv_dir}")

    def _save_node_voltages(self):
        V = self.results["V_nodes"]
        t = self.results["t"]
        n_nodes = V.shape[0]
        header = ["time_s"] + [f"V_node_{k}" for k in range(n_nodes)]
        data = np.column_stack([t, V.T])
        self._write(os.path.join(self.csv_dir, "node_voltages.csv"), header, data)

    def _save_section_currents(self):
        I = self.results["I_sections"]
        t = self.results["t"]
        n_sec = I.shape[0]
        header = ["time_s"] + [f"I_sec_{k}" for k in range(n_sec)]
        data = np.column_stack([t, I.T])
        self._write(os.path.join(self.csv_dir, "section_currents.csv"), header, data)

    def _save_summary(self):
        d = self._derived
        path = os.path.join(self.csv_dir, "summary.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["node_idx", "position_norm", "V_max_V", "dV_max_V"])
            n_nodes = len(d["V_max_per_node"])
            n_gaps = len(d["dV_max_per_gap"])
            for i in range(n_nodes):
                dv = d["dV_max_per_gap"][i] if i < n_gaps else float("nan")
                pos = d["positions"][i]
                w.writerow([i, f"{pos:.4f}", f"{d['V_max_per_node'][i]:.4f}", f"{dv:.4f}"])
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([])
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
