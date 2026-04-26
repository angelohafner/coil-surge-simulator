"""
Salva os gráficos como imagens PNG para exibição direta.
"""
import pathlib
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Parâmetros ────────────────────────────────────────────────────────────────
N       = 20
L_sec   = 5e-4; R_sec = 0.25
C_int   = 5e-11; C_end = 2.5e-11
A1      = 1035.1; alpha = 13863.0; beta = 2.5e6
T_MAX   = 200e-6; DT   = 10e-9

OUTPUT_DIR = pathlib.Path(r"E:\surto-1\output\atp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NODES_LABELS = {0:"N0 — Entrada", 5:"N5 — 25%", 10:"N10 — 50%", 15:"N15 — 75%", 20:"N20 — Saída (aberto)"}
COLOR_MAP = {0:"#1f77b4", 5:"#ff7f0e", 10:"#2ca02c", 15:"#d62728", 20:"#9467bd"}

def source_voltage(t):
    return A1 * (np.exp(-alpha*t) - np.exp(-beta*t))

def C_node(k):
    return C_end if (k == 0 or k == N) else C_int

def ode(t, y):
    V = np.empty(N+1)
    V[0] = source_voltage(t)
    V[1:N+1] = y[:N]
    I = y[N:]
    dy = np.empty(2*N)
    for k in range(1, N+1):
        I_in  = I[k-1]
        I_out = I[k] if k < N else 0.0
        dy[k-1] = (I_in - I_out) / C_node(k)
    for k in range(N):
        dy[N+k] = (V[k] - V[k+1] - R_sec*I[k]) / L_sec
    return dy

t_eval = np.arange(0, T_MAX+DT, DT)
sol = solve_ivp(ode, (0, T_MAX), np.zeros(2*N), method="RK45",
                t_eval=t_eval, rtol=1e-6, atol=1e-10)

t_us = sol.t * 1e6

node_voltages = {}
for k in NODES_LABELS:
    node_voltages[k] = (source_voltage(sol.t) if k == 0 else sol.y[k-1]) * 1e-3

TITLE = "Resposta ao surto 1,2/50 µs — bobina distribuída Pi (N=20)"

# ── Figura 1: curvas sobrepostas ──────────────────────────────────────────────
fig1 = go.Figure()
for k, label in NODES_LABELS.items():
    fig1.add_trace(go.Scatter(x=t_us, y=node_voltages[k],
                              mode="lines", name=label,
                              line=dict(color=COLOR_MAP[k], width=2)))
fig1.update_layout(
    title=dict(text=TITLE, font_size=15),
    xaxis=dict(title="Tempo (µs)", gridcolor="#e0e0e0"),
    yaxis=dict(title="Tensão (kV)", gridcolor="#e0e0e0"),
    plot_bgcolor="white", paper_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    width=1100, height=480,
)
fig1.write_image(str(OUTPUT_DIR/"grafico_overlay.png"), scale=2)
print("Salvo: grafico_overlay.png")

# ── Figura 2: subplots ────────────────────────────────────────────────────────
rows = len(NODES_LABELS)
fig2 = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                     subplot_titles=list(NODES_LABELS.values()),
                     vertical_spacing=0.05)
for row, (k, label) in enumerate(NODES_LABELS.items(), start=1):
    fig2.add_trace(
        go.Scatter(x=t_us, y=node_voltages[k], mode="lines",
                   line=dict(color=COLOR_MAP[k], width=1.6), showlegend=False),
        row=row, col=1)
    fig2.update_yaxes(title_text="kV", row=row, col=1, gridcolor="#e0e0e0")
fig2.update_xaxes(title_text="Tempo (µs)", row=rows, col=1, gridcolor="#e0e0e0")
fig2.update_layout(title=TITLE+" — subplots",
                   plot_bgcolor="white", paper_bgcolor="white",
                   height=220*rows, width=1100)
fig2.write_image(str(OUTPUT_DIR/"grafico_subplots.png"), scale=2)
print("Salvo: grafico_subplots.png")
print("Concluído!")
