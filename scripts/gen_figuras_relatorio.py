"""
gen_figuras_relatorio.py
========================
Gera as figuras estáticas do relatório focado no comportamento da bobina:

  distribuicao_inicial.png  — perfil V(x) em t=0+ (neutro aterrado) para vários
                              alpha, a partir do modelo real (initial_voltage_
                              distribution), mais a referência uniforme.

As curvas vêm do solver em src/ (não são desenhadas à mão).

Uso:  python scripts/gen_figuras_relatorio.py
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.models.distributed_coil import DistributedCoil
from src.sources.impulse_source import ImpulseSource
from src.utils.simulation_config import SimulationConfig

OUT = ROOT / "relatorio" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def perfil(alpha: float, N: int = 200, C_total: float = 1e-9):
    cs = C_total / alpha**2
    cfg = SimulationConfig(
        n_sections=N, C_total=C_total, C_series_total=cs,
        model_type="pi", termination="grounded",
    )
    x, V = DistributedCoil(cfg).initial_voltage_distribution(v_input=1.0)
    return x, V


fig, ax = plt.subplots(figsize=(8.0, 4.6))
for alpha in (1.0, 3.0, 5.0, 8.0):
    x, V = perfil(alpha)
    ax.plot(x * 100, V * 100, lw=2.4 if alpha == 5 else 1.4,
            label=rf"$\alpha = {alpha:.0f}$")
ax.plot([0, 100], [100, 0], "k--", lw=1.0, label=r"uniforme ($\alpha\to 0$)")
ax.set_xlabel(r"posição ao longo da bobina $x$ (%)")
ax.set_ylabel(r"tensão inicial $v(x)/V_0$ (%)")
ax.set_title(r"Distribuição inicial de tensão em $t=0^+$ (neutro aterrado)")
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "distribuicao_inicial.png", dpi=150)
print(f"[OK] {OUT / 'distribuicao_inicial.png'}")


# --- fonte: onda quadrada PWM de 20 kHz (2 periodos) ---
sq = ImpulseSource(source_type="square", amplitude=1000.0,
                   t_front=0.2e-6, frequency=20000.0)
t_us = np.linspace(0.0, 100.0, 4000)
v = sq.evaluate_array(t_us * 1e-6)
fig2, ax2 = plt.subplots(figsize=(8.0, 3.0))
ax2.plot(t_us, v, color="#ff9f45", lw=2.0)
ax2.set_xlabel(r"tempo $t$ ($\mu$s)")
ax2.set_ylabel(r"$v_s$ (V)")
ax2.set_title("Fonte: onda quadrada PWM de 20 kHz (T = 50 us)")
ax2.set_ylim(-50, 1100)
ax2.grid(alpha=0.3)
fig2.tight_layout()
fig2.savefig(OUT / "onda_quadrada_fonte.png", dpi=150)
print(f"[OK] {OUT / 'onda_quadrada_fonte.png'}")
