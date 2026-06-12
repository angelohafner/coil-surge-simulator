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
  4. Save CSV results + run_metadata.json for EVERY scenario
     (ResultProcessor; provenance: config, git commit, versions).
  5. Generate static PNG figures (PlotGenerator) for Pi and T.
  6. Generate animated GIFs (GifGenerator).

Scenarios simulated automatically
-----------------------------------
  - Default Pi model  (from config file)         -> output/
  - Default T model   (same parameters)          -> output/t_model/
  - Low-C variant     (C_total x min multiplier) -> output/low_c/
  - High-C variant    (C_total x max multiplier) -> output/high_c/
  The multipliers come from `c_scenario_multipliers` in the config.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime

# Make sure the project root is on sys.path when invoked directly
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.simulation_config import SimulationConfig
from src.sources.impulse_source import ImpulseSource
from src.models.distributed_coil import DistributedCoil
from src.solvers.time_domain_solver import TimeDomainSolver
from src.utils.result_processor import ResultProcessor
from src.visualization.plot_generator import PlotGenerator
from src.visualization.gif_generator import GifGenerator

ROOT = os.path.dirname(os.path.abspath(__file__))


# ──────────────────────────────────────────────────────────────────────
# Helpers
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


def git_commit_hash() -> str:
    """Current commit hash (provenance); 'unknown' outside a git checkout."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except OSError:
        pass
    return "unknown"


def environment_info() -> dict:
    import matplotlib
    import numpy
    import scipy
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__,
    }


def write_run_metadata(cfg: SimulationConfig, scenario: str,
                       out_dir: str, commit: str, env: dict) -> None:
    """Stamp the scenario output with full provenance (audit, R7)."""
    meta = {
        "scenario": scenario,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": commit,
        "environment": env,
        "config": asdict(cfg),
    }
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "run_metadata.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"  Metadata   -> {path}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Distributed-coil surge (impulse) response simulator."
    )
    parser.add_argument(
        "--config",
        default=os.path.join(ROOT, "config", "default_case.json"),
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
    mults = sorted(base_cfg.c_scenario_multipliers)
    mult_low, mult_high = mults[0], mults[-1]

    scenarios = {
        "pi":     base_cfg.copy_with(model_type="pi"),
        "t":      base_cfg.copy_with(model_type="t"),
        "low_c":  base_cfg.copy_with(model_type="pi",
                                     C_total=base_cfg.C_total * mult_low),
        "high_c": base_cfg.copy_with(model_type="pi",
                                     C_total=base_cfg.C_total * mult_high),
    }
    scenario_dirs = {
        "pi":     out_dir,
        "t":      os.path.join(out_dir, "t_model"),
        "low_c":  os.path.join(out_dir, "low_c"),
        "high_c": os.path.join(out_dir, "high_c"),
    }

    commit = git_commit_hash()
    env = environment_info()

    results = {}
    processors = {}

    # ── Simulate all scenarios; save CSV + provenance for each ────────
    for name, cfg in scenarios.items():
        print(f"\n[Scenario: {name.upper()}]")
        print(f"  model={cfg.model_type.upper()}  "
              f"C_total={cfg.C_total:.2e} F  "
              f"N={cfg.n_sections}")
        t0 = time.time()
        results[name] = run_simulation(cfg)
        print(f"  Elapsed: {time.time()-t0:.2f} s")

        processors[name] = ResultProcessor(results[name], scenario_dirs[name])
        processors[name].save_csv()
        write_run_metadata(cfg, name, scenario_dirs[name], commit, env)

    derived_pi = processors["pi"].compute_derived()
    derived_t = processors["t"].compute_derived()

    # ── Static figures (Pi and T) ──────────────────────────────────────
    print("\n[Static Figures — Pi model]")
    pg = PlotGenerator(results["pi"], derived_pi, out_dir)
    pg.plot_all()

    print("\n[Static Figures — T model]")
    pg_t = PlotGenerator(results["t"], derived_t, scenario_dirs["t"])
    pg_t.plot_all()

    # ── Animated GIFs ─────────────────────────────────────────────────
    print("\n[Animated GIFs]")
    gifgen = GifGenerator(out_dir)
    gifgen.generate_all(
        results_pi=results["pi"],
        results_t=results["t"],
        results_low_c=results["low_c"],
        results_high_c=results["high_c"],
        label_low_c=f'C x {mult_low:g}  = {scenarios["low_c"].C_total:.1e} F',
        label_high_c=f'C x {mult_high:g} = {scenarios["high_c"].C_total:.1e} F',
    )

    # ── Summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Simulation complete.")
    print(f"  Output directory : {os.path.abspath(out_dir)}/")
    print(f"    +-- csv/, run_metadata.json   - Pi (primary scenario)")
    print(f"    +-- figures/                  - static PNG plots (Pi)")
    print(f"    +-- t_model/                  - T model (csv + figures)")
    print(f"    +-- low_c/, high_c/           - capacitance variants (csv)")
    print(f"    +-- gifs/                     - animated GIFs")
    print("=" * 60)

    d = derived_pi
    print(f"\n  Pi-model results:")
    print(f"    Peak input  voltage : {d['Vpk_in']:.1f} V")
    print(f"    Peak output voltage : {d['Vpk_out']:.1f} V")
    print(f"    Transfer ratio      : {d['transfer_ratio']:.4f}")


if __name__ == "__main__":
    main()
