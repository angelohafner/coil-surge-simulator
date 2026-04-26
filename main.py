"""
main.py — Entry point for the distributed-coil surge simulation.

Usage
-----
  python main.py                        # uses config/default_case.json
  python main.py --config my_case.json  # custom config file

Workflow
--------
  1. Load SimulationConfig from JSON.
  2. Build ImpulseSource and DistributedCoil for each scenario.
  3. Solve the ODE system (TimeDomainSolver).
  4. Save CSV results (ResultProcessor).
  5. Generate static PNG figures (PlotGenerator).
  6. Generate animated GIFs (GifGenerator).

Scenarios simulated automatically
-----------------------------------
  - Default Pi model  (from config file)
  - Default T model   (same electrical parameters, different topology)
  - Low-C variant     (C_total × 0.1)
  - High-C variant    (C_total × 10)
"""

import argparse
import os
import sys
import time

# Make sure the project root is on sys.path when invoked directly
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.simulation_config import SimulationConfig
from src.sources.impulse_source import ImpulseSource
from src.models.distributed_coil import DistributedCoil
from src.solvers.time_domain_solver import TimeDomainSolver
from src.utils.result_processor import ResultProcessor
from src.visualization.plot_generator import PlotGenerator
from src.visualization.gif_generator import GifGenerator


# ──────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────

def run_simulation(config: SimulationConfig) -> dict:
    """Build model, run solver, return raw results dict."""
    source = ImpulseSource(
        source_type=config.source_type,
        amplitude=config.V_amplitude,
        t_front=config.t_front,
        t_tail=config.t_tail,
    )
    coil = DistributedCoil(config)
    solver = TimeDomainSolver(coil, source, config)
    return solver.solve()


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Distributed-coil surge (impulse) response simulator."
    )
    parser.add_argument(
        "--config",
        default=os.path.join("config", "default_case.json"),
        help="Path to JSON configuration file (default: config/default_case.json)",
    )
    args = parser.parse_args()

    # ── Load configuration ─────────────────────────────────────────────
    cfg_path = args.config
    if not os.path.isfile(cfg_path):
        print(f"[ERROR] Config file not found: {cfg_path}")
        sys.exit(1)

    base_cfg = SimulationConfig.from_json(cfg_path)
    out_dir = base_cfg.output_dir

    print("=" * 60)
    print("  Distributed Coil — Surge Response Simulator")
    print("=" * 60)
    print(base_cfg.summary())
    print("=" * 60)

    # ── Define all scenarios ───────────────────────────────────────────
    scenarios = {
        "pi":     base_cfg.copy_with(model_type="pi"),
        "t":      base_cfg.copy_with(model_type="t"),
        "low_c":  base_cfg.copy_with(model_type="pi", C_total=base_cfg.C_total * 0.1),
        "high_c": base_cfg.copy_with(model_type="pi", C_total=base_cfg.C_total * 10.0),
    }

    results = {}

    # ── Simulate all scenarios ─────────────────────────────────────────
    for name, cfg in scenarios.items():
        print(f"\n[Scenario: {name.upper()}]")
        print(f"  model={cfg.model_type.upper()}  "
              f"C_total={cfg.C_total:.2e} F  "
              f"N={cfg.n_sections}")
        t0 = time.time()
        results[name] = run_simulation(cfg)
        print(f"  Elapsed: {time.time()-t0:.2f} s")

    # ── Save CSV for primary Pi scenario ──────────────────────────────
    print("\n[Saving CSVs]")
    proc_pi = ResultProcessor(results["pi"], out_dir)
    proc_pi.save_csv()
    derived_pi = proc_pi.compute_derived()

    proc_t = ResultProcessor(results["t"], os.path.join(out_dir, "t_model"))
    proc_t.save_csv()

    # ── Static figures for primary Pi scenario ─────────────────────────
    print("\n[Static Figures — Pi model]")
    pg = PlotGenerator(results["pi"], derived_pi, out_dir)
    pg.plot_all()

    print("\n[Static Figures — T model]")
    derived_t = proc_t.compute_derived()
    pg_t = PlotGenerator(results["t"], derived_t, os.path.join(out_dir, "t_model"))
    pg_t.plot_all()

    # ── Animated GIFs ─────────────────────────────────────────────────
    print("\n[Animated GIFs]")
    gifgen = GifGenerator(out_dir)
    gifgen.generate_all(
        results_pi=results["pi"],
        results_t=results["t"],
        results_low_c=results["low_c"],
        results_high_c=results["high_c"],
        label_low_c=f'Low C  = {scenarios["low_c"].C_total:.1e} F',
        label_high_c=f'High C = {scenarios["high_c"].C_total:.1e} F',
    )

    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Simulation complete.")
    print(f"  Output directory : {os.path.abspath(out_dir)}/")
    print(f"    +-- csv/            - node voltages, currents, summary")
    print(f"    +-- figures/        - static PNG plots (Pi model)")
    print(f"    +-- t_model/        - static PNG plots (T model)")
    print(f"    +-- gifs/           - animated GIFs")
    print("=" * 60)

    d = derived_pi
    print(f"\n  Pi-model results:")
    print(f"    Peak input  voltage : {d['Vpk_in']:.1f} V")
    print(f"    Peak output voltage : {d['Vpk_out']:.1f} V")
    print(f"    Transfer ratio      : {d['transfer_ratio']:.4f}")


if __name__ == "__main__":
    main()
