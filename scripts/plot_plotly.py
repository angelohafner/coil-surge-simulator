"""
plot_plotly.py
==============
Visualizações Plotly (HTML interativo + PNG) da resposta da escada Pi nos
nós de 0 %, 25 %, 50 %, 75 % e 100 % da bobina, geradas pelo simulador
Python deste repositório (pacote ``src/``).

Substitui os antigos ``simulate_direct.py`` e ``save_images.py``, que
duplicavam o modelo físico com parâmetros hard-coded próprios (auditoria,
achado A3) e caminhos absolutos ``E:\\`` (achado A4). Aqui toda a física vem
de ``src/`` e os parâmetros de ``config/default_case.json``.

Procedência: os gráficos produzidos por este script são SIMULAÇÃO PYTHON.
Para resultados reais do ATP use ``run_atp.py``; para a validação cruzada
quantitativa use ``scripts/compare_python_atp.py``.

Uso:
    python scripts/plot_plotly.py
    python scripts/plot_plotly.py --t-total 2e-4 --out output/python_plotly
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.simulation_config import SimulationConfig
from src.sources.impulse_source import ImpulseSource
from src.models.distributed_coil import DistributedCoil
from src.solvers.time_domain_solver import TimeDomainSolver

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
OBS_FRACTIONS = (0.0, 0.25, 0.50, 0.75, 1.0)   # posições observadas
TIME_SCALE = 1e6    # s  -> µs
VOLT_SCALE = 1e-3   # V  -> kV


def node_labels(n_sections: int) -> dict[int, str]:
    """Nó observado -> rótulo, para as frações de OBS_FRACTIONS."""
    labels: dict[int, str] = {}
    for frac in OBS_FRACTIONS:
        k = int(round(frac * n_sections))
        if k == 0:
            labels[k] = "Entrada — nó 0"
        elif k == n_sections:
            labels[k] = f"Saída — nó {k} (terminação)"
        else:
            labels[k] = f"{int(round(100 * frac))} % da bobina — nó {k}"
    return labels


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "config" / "default_case.json"))
    ap.add_argument("--t-total", type=float, default=200e-6,
                    help="janela simulada [s] (default 2e-4, igual ao caso ATP)")
    ap.add_argument("--out", default=str(ROOT / "output" / "python_plotly"))
    ap.add_argument("--sem-png", action="store_true",
                    help="não gera PNGs (dispensa o pacote kaleido)")
    args = ap.parse_args()

    cfg = SimulationConfig.from_json(args.config).copy_with(
        model_type="pi", t_total=args.t_total)
    source = ImpulseSource(cfg.source_type, cfg.V_amplitude,
                           cfg.t_front, cfg.t_tail)
    res = TimeDomainSolver(DistributedCoil(cfg), source, cfg).solve()

    labels = node_labels(cfg.n_sections)
    t_us = res["t"] * TIME_SCALE
    title = (f"Resposta ao surto {cfg.t_front*1e6:.1f}/{cfg.t_tail*1e6:.0f} µs — "
             f"escada Pi (N={cfg.n_sections}) — simulação Python "
             f"(scipy {cfg.solver_method})")

    volt = {k: res["V_nodes"][k] * VOLT_SCALE for k in labels}

    # ── Figura 1: curvas sobrepostas ───────────────────────────────────
    fig1 = go.Figure()
    for i, (k, label) in enumerate(labels.items()):
        fig1.add_trace(go.Scatter(
            x=t_us, y=volt[k], mode="lines", name=label,
            line=dict(color=PALETTE[i % len(PALETTE)], width=1.8)))
    fig1.update_layout(
        title=dict(text=title, font_size=15),
        xaxis=dict(title="Tempo (µs)", gridcolor="#e0e0e0"),
        yaxis=dict(title="Tensão (kV)", gridcolor="#e0e0e0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified", width=1100, height=500)

    # ── Figura 2: subplots individuais ─────────────────────────────────
    rows = len(labels)
    fig2 = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                         subplot_titles=list(labels.values()),
                         vertical_spacing=0.06)
    for row, (k, _label) in enumerate(labels.items(), start=1):
        fig2.add_trace(
            go.Scatter(x=t_us, y=volt[k], mode="lines", showlegend=False,
                       line=dict(color=PALETTE[(row - 1) % len(PALETTE)],
                                 width=1.6)),
            row=row, col=1)
        fig2.update_yaxes(title_text="kV", row=row, col=1,
                          gridcolor="#e0e0e0")
    fig2.update_xaxes(title_text="Tempo (µs)", row=rows, col=1,
                      gridcolor="#e0e0e0")
    fig2.update_layout(title=dict(text=title + " — por nó", font_size=14),
                       plot_bgcolor="white", paper_bgcolor="white",
                       height=200 * rows, width=1100)

    # ── Saídas ──────────────────────────────────────────────────────────
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_path = out_dir / "surto_bobina_python.html"
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>\n"
        "<title>Resposta ao surto — simulação Python</title>\n"
        "<style>body{font-family:sans-serif;margin:20px;background:#fafafa}"
        "</style></head><body>\n"
        f"<h2>{title}</h2>\n"
        "<p><b>Procedência:</b> simulação Python (pacote src/, "
        f"scipy {cfg.solver_method}). Estes gráficos NÃO são saída do ATP; "
        "a validação cruzada com o ATP real está em "
        "output/atp/comparacao_python_atp.*</p>\n"
        + fig1.to_html(full_html=False, include_plotlyjs="cdn")
        + "\n<hr style='margin:30px 0'>\n"
        + fig2.to_html(full_html=False, include_plotlyjs=False)
        + "\n</body></html>")
    html_path.write_text(html, encoding="utf-8")
    print(f"[OUT] {html_path}")

    if not args.sem_png:
        try:
            fig1.write_image(str(out_dir / "grafico_overlay_python.png"), scale=2)
            fig2.write_image(str(out_dir / "grafico_subplots_python.png"), scale=2)
            print(f"[OUT] {out_dir / 'grafico_overlay_python.png'}")
            print(f"[OUT] {out_dir / 'grafico_subplots_python.png'}")
        except Exception as exc:
            print(f"[AVISO] PNGs não gerados ({exc}). Instale 'kaleido' ou use --sem-png.")


if __name__ == "__main__":
    main()
