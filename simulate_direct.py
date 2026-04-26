"""
simulate_direct.py
==================
Simula a bobina distribuída (Pi-ladder, N=20) sob surto 1,2/50 µs.
Resolve o sistema de EDOs equivalente ao que o ATP resolveria e
gera os gráficos Plotly idênticos ao run_atp.py.

Circuito:
  - N=20 seções Pi
  - L_total = 10 mH  =>  L_sec = 0.5 mH  (por seção)
  - R_total = 5 Ω    =>  R_sec = 0.25 Ω
  - C_total = 1 nF   =>  C_sec = 50 pF (internos), C_end = 25 pF (extremos)
  - Fonte dupla exponencial: v(t) = A1*(exp(-α*t) - exp(-β*t))
    A1=1035.1 V, α=13863 s⁻¹, β=2.5e6 s⁻¹  =>  pico ~1 kV em ~2.09 µs
  - Terminação: circuito aberto (N20)
"""

import pathlib
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Parâmetros do circuito ────────────────────────────────────────────────────
N       = 20
L_sec   = 5e-4        # H
R_sec   = 0.25        # Ω
C_int   = 5e-11       # F  (nós internos N1..N19)
C_end   = 2.5e-11     # F  (nós extremos N0, N20)

# Fonte dupla-exponencial (IEC 60060, 1.2/50 µs, 1 kVp)
A1      = 1035.1      # V
alpha   = 13863.0     # s⁻¹  (cauda 50 µs)
beta    = 2.5e6       # s⁻¹  (frente 1.2 µs)

# Simulação
T_MAX   = 200e-6      # s
DT      = 10e-9       # s

OUTPUT_DIR   = pathlib.Path(r"E:\surto-1\output\atp")
HTML_FILE    = OUTPUT_DIR / "surto_bobina.html"
NODES_LABELS = {
    0:  "Entrada — N0",
    5:  "25 % da bobina — N5",
    10: "50 % da bobina — N10",
    15: "75 % da bobina — N15",
    20: "Saída — N20 (circuito aberto)",
}
TIME_SCALE  = 1e6     # s → µs
VOLT_SCALE  = 1e-3    # V → kV
TITLE = "Resposta ao surto 1,2/50 µs — bobina distribuída Pi (N=20)"

# ── Estado ─────────────────────────────────────────────────────────────────────
# y = [V1, V2, ..., V20,  I0, I1, ..., I19]
#       índices 0..N-1    índices N..2N-1
# V0(t) = fonte (conhecida), V20 é estado livre (circuito aberto).

def source_voltage(t):
    return A1 * (np.exp(-alpha * t) - np.exp(-beta * t))

def C_node(k):
    """Capacitância de nó k (0..N) para o terra."""
    return C_end if (k == 0 or k == N) else C_int

def ode(t, y):
    V = np.empty(N + 1)
    V[0]    = source_voltage(t)          # nó 0 — tensão forçada
    V[1:N+1] = y[:N]                     # estados V1..V20

    I = y[N:]                            # correntes I0..I19

    dy = np.empty(2 * N)

    # dV_k/dt para k = 1..N
    for k in range(1, N + 1):
        I_in  = I[k - 1]                 # corrente da seção k-1 → k
        I_out = I[k] if k < N else 0.0   # corrente da seção k → k+1 (0 se aberto)
        dy[k - 1] = (I_in - I_out) / C_node(k)

    # dI_k/dt para k = 0..N-1
    for k in range(N):
        dy[N + k] = (V[k] - V[k + 1] - R_sec * I[k]) / L_sec

    return dy

# ── Integração ────────────────────────────────────────────────────────────────
print("Simulando circuito Pi-ladder  (N=20, IEC 60060 1,2/50 µs) ...")
t_span  = (0, T_MAX)
t_eval  = np.arange(0, T_MAX + DT, DT)
y0      = np.zeros(2 * N)

sol = solve_ivp(
    ode, t_span, y0,
    method="RK45",
    t_eval=t_eval,
    rtol=1e-6, atol=1e-10,
    dense_output=False,
)

if not sol.success:
    raise RuntimeError(f"Integração falhou: {sol.message}")

t_us = sol.t * TIME_SCALE   # eixo tempo em µs

# Montar tensões em cada nó de interesse
node_voltages = {}
for k in NODES_LABELS:
    if k == 0:
        node_voltages[k] = source_voltage(sol.t) * VOLT_SCALE
    else:
        node_voltages[k] = sol.y[k - 1] * VOLT_SCALE   # V_k = estado k-1

print(f"  Passos: {len(sol.t)}  |  tempo máx: {sol.t[-1]*1e6:.1f} µs")

# ── Gráficos ──────────────────────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COLOR_MAP = {
    0:  "#1f77b4",
    5:  "#ff7f0e",
    10: "#2ca02c",
    15: "#d62728",
    20: "#9467bd",
}

# --- Figura 1: curvas sobrepostas ---
fig1 = go.Figure()
for k, label in NODES_LABELS.items():
    fig1.add_trace(go.Scatter(
        x=t_us, y=node_voltages[k],
        mode="lines", name=label,
        line=dict(color=COLOR_MAP[k], width=1.8),
    ))
fig1.update_layout(
    title=dict(text=TITLE, font_size=16),
    xaxis=dict(title="Tempo (µs)", gridcolor="#e0e0e0"),
    yaxis=dict(title="Tensão (kV)", gridcolor="#e0e0e0"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="white",
    paper_bgcolor="white",
    hovermode="x unified",
    width=1100, height=500,
)

# --- Figura 2: subplots individuais ---
rows = len(NODES_LABELS)
fig2 = make_subplots(
    rows=rows, cols=1,
    shared_xaxes=True,
    subplot_titles=[label for label in NODES_LABELS.values()],
    vertical_spacing=0.06,
)
for row, (k, label) in enumerate(NODES_LABELS.items(), start=1):
    fig2.add_trace(
        go.Scatter(
            x=t_us, y=node_voltages[k],
            mode="lines", name=label,
            line=dict(color=COLOR_MAP[k], width=1.6),
            showlegend=False,
        ),
        row=row, col=1,
    )
    fig2.update_yaxes(title_text="kV", row=row, col=1, gridcolor="#e0e0e0")
fig2.update_xaxes(title_text="Tempo (µs)", row=rows, col=1, gridcolor="#e0e0e0")
fig2.update_layout(
    title=dict(text=TITLE + " — subplots", font_size=14),
    plot_bgcolor="white",
    paper_bgcolor="white",
    height=200 * rows,
    width=1100,
)

# --- Salvar HTML único com as duas figuras ---
html_overlay  = fig1.to_html(full_html=False, include_plotlyjs="cdn")
html_subplots = fig2.to_html(full_html=False, include_plotlyjs=False)

with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'>
<title>Resposta ao surto — Bobina distribuída</title>
<style>body{{font-family:sans-serif;margin:20px;background:#fafafa}}</style>
</head><body>
<h2>{TITLE}</h2>
<p>Simulação Python (scipy RK45) — circuito idêntico ao arquivo ATP</p>
{html_overlay}
<hr style='margin:30px 0'>
{html_subplots}
</body></html>""")

print(f"HTML salvo em: {HTML_FILE}")
