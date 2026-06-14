"""
gen_deck_gerador.py
===================
Gera o deck ATP do caso do GERADOR síncrono (neutro solidamente aterrado,
COM capacitância série turn-to-turn) — surto_bobina_gerador.atp.

Difere do deck original surto_bobina.atp (open / somente-shunt) em três pontos:
  1. capacitância série C_s,sec = N * C_series_total = 20 * 40 pF = 800 pF
     (= 8.E-4 uF) entre cada par de nós adjacentes (N0-N1 ... N19-N20);
  2. neutro aterrado: ramo de impedância desprezível N20 -> referência;
  3. sem shunt em N20 (curto-circuitado pelo aterramento) — os nós ativos
     1..N-1 ficam com shunt cheio (50 pF), como no modelo Python grounded.

O alinhamento de COLUNA FIXA é construído programaticamente (BUS1 3-8,
BUS2 9-14, R 27-32, L 33-38, C 39-44) para evitar o KILL=6 por campo fora de
coluna que abortou a primeira versão do deck original.

Uso:  python scripts/gen_deck_gerador.py
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "surto_bobina_gerador.atp"

N = 20
R_SEC = "0.25"      # ohm   (R_total/N = 5/20)
L_SEC = "0.5"       # mH    (L_total/N = 10e-3/20), XOPT=0 -> mH
C_SHUNT = "5.E-5"   # uF    (C_total/N = 1e-9/20 = 50 pF), COPT=0 -> uF
C_SHUNT_END = "2.5E-5"  # uF (C_total/2N = 25 pF) no nó de entrada N0
C_SERIES = "8.E-4"  # uF    (C_s,sec = N*C_series_total = 20*40pF = 800 pF)
R_GND = "1.E-6"     # ohm   aterramento de N20 (impedância desprezível)


# ── construtores de cartão em coluna fixa ───────────────────────────────────
def _rl(b1: str, b2: str) -> str:
    # "  " + BUS1(3-8) + BUS2(9-14) + ref(15-26) + R(27-32) + L(33-38)
    return "  " + b1.ljust(6) + b2.ljust(6) + " " * 12 + R_SEC.ljust(6) + L_SEC


def _cap_series(b1: str, b2: str) -> str:
    # BUS1 e BUS2 preenchidos; C em 39-44 (R/L em branco)
    return "  " + b1.ljust(6) + b2.ljust(6) + " " * 24 + C_SERIES


def _cap_shunt(b1: str, c: str) -> str:
    # BUS2 em branco (= terra); C em 39-44
    return "  " + b1.ljust(6) + " " * 6 + " " * 24 + c


def _r_ground(b1: str) -> str:
    # ramo R-only de b1 à referência (BUS2 em branco); R em 27-32
    return "  " + b1.ljust(6) + " " * 6 + " " * 12 + R_GND.ljust(6)


def node(k: int) -> str:
    return f"N{k}"


lines: list[str] = []
add = lines.append

add("BEGIN NEW DATA CASE")
add("C ===================================================================")
add("C  DISTRIBUTED COIL - SURGE (1.2/50 us) RESPONSE - GENERATOR CASE")
add("C  Pi-ladder, N = 20, neutro SOLIDAMENTE ATERRADO, COM cap. serie")
add("C  L_total = 10 mH | R_total = 5 ohm | C_total (shunt) = 1 nF")
add("C  C_series_total = 40 pF (ponta-a-ponta) -> alpha = sqrt(Cg/Cs) = 5")
add("C  Source: double-exponential 1.0 kVp  (IEC 60060 - 1.2/50 us)")
add("C  Termination: GROUNDED  (V(N20) = 0)")
add("C ===================================================================")
add("C  Diferencas vs surto_bobina.atp (open/somente-shunt):")
add("C   - capacitores SERIE entre nos adjacentes: C_s,sec = N*C_series_total")
add("C     = 20 * 40 pF = 800 pF = 8.E-4 uF  (cada ramo N{k}-N{k+1})")
add("C   - N20 aterrado por ramo R = 1.E-6 ohm (impedancia desprezivel)")
add("C   - sem shunt em N20 (curto pelo aterramento); nos 1..19 com 50 pF")
add("C ===================================================================")
add("C  XOPT = 0 -> indutancias em mH ; COPT = 0 -> capacitancias em uF")
add("C  Per section: R_sec=0.25 ohm, L_sec=0.5 mH, C_shunt=50 pF, C_s=800 pF")
add("C ===================================================================")
add("C  Misc. data cards")
add("C  dT [s]   Tmax [s] XOPT    COPT    Epsiln  Tolmat  Tstart")
add("   1.E-8   2.E-4      0.      0.   1.E-5   1.E-5     -1.")
add("C  Iout    Iplot   Idoubl  Kssout  Maxout  Ipun    Memsav  Icat")
add("    1000       1       0       0       0       0       0       1")
add("C ===================================================================")
add("C  BRANCH DATA  (fixed-column: BUS1 3-8, BUS2 9-14, R 27-32, L 33-38, C 39-44)")
add("C  Column ruler:")
add("C  1234567890123456789012345678901234567890123456")
add("C  --- Series R-L branches: R_sec = 0.25 ohm, L_sec = 0.5 mH ---")
for k in range(N):
    add(_rl(node(k), node(k + 1)))
add("C")
add("C  --- Series (turn-to-turn) capacitors: C_s,sec = 8.E-4 uF (800 pF) ---")
for k in range(N):
    add(_cap_series(node(k), node(k + 1)))
add("C")
add("C  --- Shunt capacitors to ground (BUS2 blank = ground) ---")
add("C  N0 = entrada (fonte ideal: shunt irrelevante); N1..N19 = 50 pF")
add("C  N20 SEM shunt (aterrado abaixo).")
add(_cap_shunt(node(0), C_SHUNT_END))
for k in range(1, N):
    add(_cap_shunt(node(k), C_SHUNT))
add("C")
add("C  --- Neutro solidamente aterrado: N20 -> referencia (R desprezivel) ---")
add(_r_ground(node(N)))
add("BLANK card ending branches")
add("BLANK card ending switches")
add("C ===================================================================")
add("C  SOURCE DATA - type 15 double-exponential (A, B entered NEGATIVE)")
add("C  v(t) = AMP * [exp(A*t) - exp(B*t)]")
add("C ===================================================================")
add("15N0          1035.1   -13863.    -2.5E6        0.        0.        0.     2.E-4")
add("BLANK card ending sources")
add("C ===================================================================")
add("C  OUTPUT REQUEST  (node voltages to ground)")
add("C  Nodes: input (N0), 25% (N5), 50% (N10), 75% (N15), output (N20=0)")
add("C ===================================================================")
add("  N0    N5    N10   N15   N20")
add("BLANK card ending node voltage output requests")
add("BLANK card ending plot cards")
add("BEGIN NEW DATA CASE")
add("BLANK")

OUT.write_text("\n".join(lines) + "\n", encoding="ascii")
print(f"[OK] {OUT}  ({len(lines)} linhas)")
