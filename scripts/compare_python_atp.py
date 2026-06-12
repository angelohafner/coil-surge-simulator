"""
compare_python_atp.py
=====================
Comparação quantitativa entre o modelo Python (src/) e o resultado real
do ATP (.pl4) para a escada Pi de N=20 seções sob impulso 1,2/50 µs.

Pré-requisito: o arquivo .pl4 deve ter sido gerado por uma execução real
do ATP sobre surto_bobina.atp (ICAT=1 mantém o .pl4 em disco).

Saídas (em --out, default output/atp/):
  comparacao_python_atp.csv   erro máximo e RMS por nó (V e % de 1 kV)
  comparacao_python_atp.png   curvas sobrepostas Python × ATP por nó

Uso:
    python scripts/compare_python_atp.py [--pl4 caminho.pl4] [--out pasta]
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run_atp import read_pl4                          # parser .pl4
from src.utils.simulation_config import SimulationConfig
from src.sources.impulse_source import ImpulseSource
from src.models.distributed_coil import DistributedCoil
from src.solvers.time_domain_solver import TimeDomainSolver

# Nós comparados: índice do nó Python -> nome do nó ATP
NODE_MAP = {0: "N0", 5: "N5", 10: "N10", 15: "N15", 20: "N20"}

# Fonte do deck ATP (cartão tipo 15) — usada na checagem analítica de N0
ATP_A1 = 1035.1     # V
ATP_ALPHA = 13863.0  # s^-1
ATP_BETA = 2.5e6     # s^-1


def match_node(data: dict[str, np.ndarray], node: str) -> str:
    """Casamento EXATO (após strip/upper) do nome do nó nas chaves do .pl4."""
    for key in data:
        if key.strip().upper() == node.upper():
            return key
    raise KeyError(
        f"Nó '{node}' não encontrado no .pl4. Chaves: {sorted(data.keys())}"
    )


def run_python(config_path: pathlib.Path, t_total: float) -> dict:
    cfg = SimulationConfig.from_json(str(config_path))
    cfg = cfg.copy_with(model_type="pi", t_total=t_total)
    source = ImpulseSource(cfg.source_type, cfg.V_amplitude, cfg.t_front, cfg.t_tail)
    coil = DistributedCoil(cfg)
    return TimeDomainSolver(coil, source, cfg).solve()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pl4", default=str(ROOT / "surto_bobina.pl4"))
    ap.add_argument("--config", default=str(ROOT / "config" / "default_case.json"))
    ap.add_argument("--out", default=str(ROOT / "output" / "atp"))
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── ATP ────────────────────────────────────────────────────────────
    t_atp, data = read_pl4(args.pl4)
    print(f"[ATP] {len(t_atp)} passos, t_max = {t_atp[-1]*1e6:.1f} us")

    # Checagem analítica da fonte (confirma interpretação do cartão tipo 15)
    key_n0 = match_node(data, "N0")
    v_analitico = ATP_A1 * (np.exp(-ATP_ALPHA * t_atp) - np.exp(-ATP_BETA * t_atp))
    err_fonte = np.max(np.abs(data[key_n0] - v_analitico))
    print(f"[CHECK] max|V_ATP(N0) - dupla exponencial analítica| = {err_fonte:.4f} V")
    if err_fonte > 1.0:  # 0,1% de 1 kV
        raise RuntimeError(
            f"V(N0) do ATP não confere com a dupla exponencial ({err_fonte:.2f} V) — "
            "verificar interpretação do cartão de fonte."
        )

    # ── Python (mesma janela de tempo do ATP) ──────────────────────────
    res = run_python(pathlib.Path(args.config), t_total=float(t_atp[-1]))
    t_py = res["t"]
    V_py = res["V_nodes"]          # (21, n_t)

    # ── Métricas por nó (ATP interpolado na grade Python) ──────────────
    # Além do erro pontual na janela completa, reporta:
    #  - erro na janela inicial (0-30 us), onde ocorrem a frente de onda e a
    #    primeira reflexão (região de interesse dielétrico) e a deriva de
    #    fase trapezoidal(ATP) x RK45(Python) ainda é pequena;
    #  - diferença dos PICOS por nó, grandeza usada em coordenação de
    #    isolamento.
    T_INICIAL = 30e-6
    w = t_py <= T_INICIAL
    rows = []
    series = {}
    for k, node in NODE_MAP.items():
        v_atp = np.interp(t_py, t_atp, data[match_node(data, node)])
        v_py = V_py[k]
        err = v_py - v_atp
        vmax_py = float(np.max(np.abs(v_py)))
        vmax_atp = float(np.max(np.abs(v_atp)))
        rows.append({
            "node": node,
            "pos_pct": int(round(100 * k / 20)),
            "vmax_python_V": vmax_py,
            "vmax_atp_V": vmax_atp,
            "dif_pico_pct": 100.0 * (vmax_py - vmax_atp) / vmax_atp,
            "max_abs_err_V": float(np.max(np.abs(err))),
            "rms_err_V": float(np.sqrt(np.mean(err**2))),
            "max_err_30us_V": float(np.max(np.abs(err[w]))),
            "rms_err_30us_V": float(np.sqrt(np.mean(err[w] ** 2))),
        })
        series[node] = (v_py, v_atp)

    vref = 1000.0  # pico nominal da fonte [V]
    csv_path = out_dir / "comparacao_python_atp.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# Comparacao Python (scipy RK45, src/) x ATP (tpbigG, surto_bobina.pl4)"])
        w.writerow(["# Erros em V e em % do pico nominal da fonte (1000 V)."])
        w.writerow(["# Nota: fonte Python usa K calculado (pico exato 1000.0 V); deck ATP usa"])
        w.writerow(["#       A1=1035.1 fixo (pico ~999.97 V): diferenca sistematica ~0.003%."])
        w.writerow(["node", "pos_pct", "vmax_python_V", "vmax_atp_V",
                    "dif_pico_pct", "max_abs_err_V", "rms_err_V",
                    "max_err_pct", "rms_err_pct",
                    "max_err_0a30us_V", "rms_err_0a30us_V"])
        for r in rows:
            w.writerow([r["node"], r["pos_pct"],
                        f"{r['vmax_python_V']:.4f}", f"{r['vmax_atp_V']:.4f}",
                        f"{r['dif_pico_pct']:.4f}",
                        f"{r['max_abs_err_V']:.4f}", f"{r['rms_err_V']:.4f}",
                        f"{100*r['max_abs_err_V']/vref:.4f}",
                        f"{100*r['rms_err_V']/vref:.4f}",
                        f"{r['max_err_30us_V']:.4f}",
                        f"{r['rms_err_30us_V']:.4f}"])
    print(f"[OUT] {csv_path}")

    # ── Figura ──────────────────────────────────────────────────────────
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(NODE_MAP), 1, figsize=(9, 12), sharex=True)
    t_us = t_py * 1e6
    for ax, (k, node) in zip(axes, NODE_MAP.items()):
        v_py, v_atp = series[node]
        ax.plot(t_us, v_py, label="Python (RK45)", color="tab:blue", lw=1.2)
        ax.plot(t_us, v_atp, label="ATP (trapezoidal)", color="tab:red",
                lw=1.0, ls="--")
        r = next(x for x in rows if x["node"] == node)
        ax.set_title(
            f"{node} ({r['pos_pct']} %)  —  erro máx {r['max_abs_err_V']:.1f} V "
            f"({100*r['max_abs_err_V']/vref:.2f} %),  RMS {r['rms_err_V']:.1f} V",
            fontsize=9,
        )
        ax.set_ylabel("Tensão [V]")
        ax.grid(True, alpha=0.4)
        ax.legend(fontsize=8, loc="upper right")
    axes[-1].set_xlabel("Tempo [µs]")
    fig.suptitle("Validação cruzada Python × ATP — escada Pi N=20, impulso 1,2/50 µs",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    png_path = out_dir / "comparacao_python_atp.png"
    fig.savefig(png_path, dpi=150)
    print(f"[OUT] {png_path}")

    # ── Resumo ──────────────────────────────────────────────────────────
    print("\nResumo da validação cruzada (janela completa 0-200 µs):")
    for r in rows:
        print(f"  {r['node']:>4} ({r['pos_pct']:3d}%):  "
              f"pico Py {r['vmax_python_V']:8.2f} V | pico ATP {r['vmax_atp_V']:8.2f} V "
              f"(dif {r['dif_pico_pct']:+6.3f} %) | "
              f"max|err| {r['max_abs_err_V']:7.2f} V | "
              f"max|err| 0-30µs {r['max_err_30us_V']:6.2f} V")
    worst_peak = max(rows, key=lambda r: abs(r["dif_pico_pct"]))
    worst_w = max(rows, key=lambda r: r["max_err_30us_V"])
    print(f"\n  Pior diferença de pico: {worst_peak['node']} "
          f"({worst_peak['dif_pico_pct']:+.3f} %)")
    print(f"  Pior erro pontual 0-30 µs: {worst_w['node']} "
          f"({100*worst_w['max_err_30us_V']/vref:.3f} % de 1 kV)")


if __name__ == "__main__":
    main()
