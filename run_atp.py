"""
run_atp.py
==========
Executa ATP, lê o arquivo .pl4 resultante e salva gráficos interativos em HTML.
Script independente — não depende dos demais módulos do projeto.

Requisitos:
    pip install numpy plotly

Uso:
    python run_atp.py
"""

from __future__ import annotations

import struct
import subprocess
import sys
import pathlib

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ══════════════════════════════════════════════════════════════════════════════
#  PARÂMETROS — edite aqui
# ══════════════════════════════════════════════════════════════════════════════

ATP_EXE    = r"C:\ATP\ATP\GNUATP\tpbigG.exe"
ATP_FILE   = r"E:\surto-1\surto_bobina.atp"
OUTPUT_DIR = pathlib.Path(r"E:\surto-1\output\atp")

# Nós a plotar (devem constar na seção OUTPUT REQUEST do .atp)
NODES: list[str] = ["N0", "N5", "N10", "N15", "N20"]
NODE_LABELS: dict[str, str] = {
    "N0":  "Entrada — N0",
    "N5":  "25 % da bobina — N5",
    "N10": "50 % da bobina — N10",
    "N15": "75 % da bobina — N15",
    "N20": "Saída — N20 (circuito aberto)",
}

# Escalas para exibição nos gráficos
TIME_UNIT  = "µs";  TIME_SCALE  = 1e6    # s  → µs
VOLT_UNIT  = "kV";  VOLT_SCALE  = 1e-3   # V  → kV

TITLE         = "Resposta ao surto 1,2/50 µs — bobina distribuída Pi (N=20)"
HTML_FILENAME = "surto_bobina.html"

# Timeout máximo para o ATP (segundos)
ATP_TIMEOUT = 120


# ══════════════════════════════════════════════════════════════════════════════
#  EXECUÇÃO DO ATP
# ══════════════════════════════════════════════════════════════════════════════

def run_atp(exe: str, atp_file: str) -> tuple[pathlib.Path, pathlib.Path]:
    """
    Executa tpbigG.exe e retorna os caminhos (.lis, .pl4).

    Tenta duas formas de invocação:
      1. Argumento direto:   tpbigG.exe surto_bobina.atp
      2. Redirecionamento:   tpbigG.exe  <  surto_bobina.atp
    """
    exe_p = pathlib.Path(exe)
    atp_p = pathlib.Path(atp_file).resolve()

    if not exe_p.exists():
        raise FileNotFoundError(f"Executável ATP não encontrado: {exe}")
    if not atp_p.exists():
        raise FileNotFoundError(f"Arquivo .atp não encontrado: {atp_file}")

    def _find_outputs() -> tuple[pathlib.Path | None, pathlib.Path | None]:
        """Procura .lis e .pl4 nas duas localizações possíveis."""
        candidates = [atp_p.parent, exe_p.parent]
        lis = pl4 = None
        for d in candidates:
            l = d / atp_p.with_suffix(".lis").name
            p = d / atp_p.with_suffix(".pl4").name
            if l.exists() and lis is None:
                lis = l
            if p.exists() and pl4 is None:
                pl4 = p
        return lis, pl4

    # ATP precisa do arquivo 'startup' que fica na sua própria pasta
    common_kwargs = dict(
        capture_output=True,
        text=True,
        timeout=ATP_TIMEOUT,
        cwd=str(exe_p.parent),
    )

    # Tentativa 1: argumento com caminho absoluto
    print(f"[ATP] {exe_p.name}  {atp_p.name}")
    result = subprocess.run([str(exe_p), str(atp_p)], **common_kwargs)
    lis, pl4 = _find_outputs()

    # Tentativa 2: stdin (alguns builds antigos do ATP usam esta forma)
    if lis is None:
        print("[ATP] Tentando via stdin ...")
        with open(atp_p, "r") as f_in:
            result = subprocess.run(
                [str(exe_p)],
                stdin=f_in,
                **common_kwargs,
            )
        lis, pl4 = _find_outputs()

    _log_atp(result)

    if lis is None:
        raise RuntimeError(
            f"ATP não gerou arquivo .lis.  Código de saída: {result.returncode}\n"
            "Verifique se o caminho ATP_EXE está correto e se o .atp é válido."
        )

    if pl4 is None:
        raise RuntimeError(
            ".lis gerado, mas .pl4 não encontrado.\n"
            "Verifique se há nós na seção OUTPUT REQUEST do .atp."
        )

    print(f"[ATP] OK  —  .lis: {lis.name}  |  .pl4: {pl4.name}")
    return lis, pl4


def _log_atp(result: subprocess.CompletedProcess) -> None:
    combined = (result.stdout or "") + (result.stderr or "")
    erros = [l for l in combined.splitlines()
             if any(w in l.upper() for w in ("ERROR", "WARNING", "FATAL", "SEVERE"))]
    if erros:
        print("[ATP LOG]\n  " + "\n  ".join(erros[-30:]))


# ══════════════════════════════════════════════════════════════════════════════
#  PARSER .pl4
# ══════════════════════════════════════════════════════════════════════════════

class _PL4Error(ValueError):
    pass


def _attempt(raw: bytes, endian: str, fmt: str):
    """
    Tenta parsear .pl4 com uma combinação específica de endianness e formato.

    Formatos suportados
    -------------------
    'A'   binário direto:  float32 del_t, float32 t_max, int32 nVar
    'B'   binário direto:  float64 del_t, float64 t_max, int32 nVar
    'F32' Fortran seq:     record(int32 LUNIT4=4, int32 nVar, float32 del_t, float32 t_max)
    'F64' Fortran seq:     record(int32 LUNIT4=4, int32 nVar, float64 del_t, float64 t_max)

    Em todos os formatos, os nomes de variáveis são strings ASCII de 10 chars;
    os dados são float32 (A/F32) ou float64 (B/F64).
    """
    e = endian

    def i32(b, o=0): return struct.unpack_from(f"{e}i", b, o)[0]
    def u32(b, o=0): return struct.unpack_from(f"{e}I", b, o)[0]
    def f32(b, o=0): return struct.unpack_from(f"{e}f", b, o)[0]
    def f64(b, o=0): return struct.unpack_from(f"{e}d", b, o)[0]

    fortran = fmt.startswith("F")
    fsz = 8 if fmt in ("B", "F64") else 4          # tamanho do float de dados
    ftype = f"{e}f{fsz}"
    names_raw = b""
    hdr_end = 0

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    if fmt == "A":
        if len(raw) < 12:
            raise _PL4Error("curto para A")
        del_t, t_max, nvar = f32(raw, 0), f32(raw, 4), i32(raw, 8)
        hdr_end = 12

    elif fmt == "B":
        if len(raw) < 20:
            raise _PL4Error("curto para B")
        del_t, t_max, nvar = f64(raw, 0), f64(raw, 8), i32(raw, 16)
        hdr_end = 20

    else:  # F32 / F64
        if len(raw) < 12:
            raise _PL4Error("curto para Fortran")
        r1_len = u32(raw, 0)
        if not 8 <= r1_len <= 256:
            raise _PL4Error(f"r1_len={r1_len}")
        r1 = raw[4: 4 + r1_len]
        if len(r1) < r1_len:
            raise _PL4Error("r1 truncado")
        lunit = i32(r1, 0)
        if lunit != 4:
            raise _PL4Error(f"LUNIT4={lunit}")
        nvar = i32(r1, 4)
        del_t = f32(r1, 8) if fmt == "F32" else f64(r1, 8)
        t_max = f32(r1, 12) if fmt == "F32" else f64(r1, 16)
        off = 4 + r1_len + 4   # pula marcador final

        # Registro 2: nomes
        r2_len = u32(raw, off)
        if r2_len != nvar * 10:
            raise _PL4Error(f"r2_len={r2_len} ≠ {nvar}×10")
        off += 4
        names_raw = raw[off: off + r2_len]
        hdr_end = off + r2_len + 4   # pula marcador final

    # ── Validação básica ──────────────────────────────────────────────────────
    if not 0 < nvar <= 500:
        raise _PL4Error(f"nVar={nvar}")
    if not 1e-13 < del_t < 1e-1:
        raise _PL4Error(f"del_t={del_t:.2e}")
    if not del_t < t_max < 1e3:
        raise _PL4Error(f"t_max={t_max:.2e}")

    # ── Nomes das variáveis (formatos A/B: imediatamente após cabeçalho) ──────
    if not fortran:
        need = hdr_end + nvar * 10
        if len(raw) < need:
            raise _PL4Error("curto para nomes")
        names_raw = raw[hdr_end: hdr_end + nvar * 10]
        hdr_end += nvar * 10

    var_names = [
        names_raw[i * 10: i * 10 + 10].decode("ascii", errors="replace").strip()
        for i in range(nvar)
    ]

    # ── Dados ─────────────────────────────────────────────────────────────────
    ncols = nvar + 1  # tempo + nvar valores por passo

    if fortran:
        rows = []
        off = hdr_end
        while off + 8 <= len(raw):
            rl = u32(raw, off)
            if rl != ncols * fsz:
                break
            off += 4
            row = np.frombuffer(raw[off: off + rl], dtype=ftype)
            rows.append(row)
            off += rl + 4
        if len(rows) < 2:
            raise _PL4Error(f"passos={len(rows)}")
        matrix = np.stack(rows)
    else:
        rest = raw[hdr_end:]
        nsteps = len(rest) // (ncols * fsz)
        if nsteps < 2:
            raise _PL4Error(f"nsteps={nsteps}")
        matrix = np.frombuffer(
            rest[: nsteps * ncols * fsz], dtype=ftype
        ).reshape(nsteps, ncols)

    time = matrix[:, 0].copy()
    data = {var_names[i]: matrix[:, i + 1].copy() for i in range(nvar)}
    return time, data


def _attempt_pisa(raw: bytes):
    """
    Formato 'PISA / C-like' gravado pelo GNU ATP (tpbigG.exe, ICAT=1).

    Layout observado (validado contra surto_bobina.pl4, 2026-06-12):
      [0:19]   data/hora ASCII, ex. '12-Jun-26  07:51:02'
      [19:23]  int32 LE  = número de colunas de dados (tempo + nvar)
      [43:47]  int32 LE  = tamanho do arquivo em bytes + 1  (validador)
      [64:64+6*nvar]  nomes das variáveis em campos ASCII de 6 chars
      [hdr:]   linhas float32 LE: (t, v1..v_nvar); hdr tipicamente 144,
               localizado por varredura com validação do eixo de tempo
               (t[0]=0, espaçamento uniforme e crescente).
    """
    if len(raw) < 200:
        raise _PL4Error("curto para PISA")
    ncols = struct.unpack_from("<i", raw, 19)[0]
    if not 2 <= ncols <= 501:
        raise _PL4Error(f"PISA ncols={ncols}")
    fsz = struct.unpack_from("<i", raw, 43)[0]
    if fsz != len(raw) + 1:
        raise _PL4Error(f"PISA size={fsz} != {len(raw) + 1}")
    nvar = ncols - 1
    names = [
        raw[64 + 6 * i: 64 + 6 * (i + 1)].decode("ascii", "replace").strip()
        for i in range(nvar)
    ]
    rowbytes = 4 * ncols
    for hdr in range(96, 513, 4):
        rest = len(raw) - hdr
        if rest <= rowbytes or rest % rowbytes:
            continue
        m = np.frombuffer(raw, dtype="<f4", offset=hdr,
                          count=rest // 4).reshape(-1, ncols)
        t = m[:, 0].astype(np.float64)
        if t[0] != 0.0 or len(t) < 2:
            continue
        dt = np.diff(t)
        if dt.min() <= 0 or not np.allclose(dt, dt[0], rtol=1e-3):
            continue
        data = {names[i]: m[:, i + 1].astype(np.float64).copy()
                for i in range(nvar)}
        return t.copy(), data
    raise _PL4Error("PISA: nenhum offset de dados consistente")


def read_pl4(filepath: str | pathlib.Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """
    Lê um arquivo .pl4 do ATP/EMTP.

    Tenta primeiro o formato PISA/C-like do GNU ATP e depois, automaticamente,
    8 combinações:
        endianness  ×  formato de cabeçalho
        (LE, BE)    ×  (F32, F64, A, B)

    Retorna
    -------
    time : np.ndarray   —  vetor de tempo em segundos
    data : dict[str, np.ndarray]  —  nome_variável → valores em Volts
    """
    raw = pathlib.Path(filepath).read_bytes()
    print(f"[PL4] {pathlib.Path(filepath).name}  ({len(raw):,} bytes)")

    errors: list[str] = []
    try:
        t, d = _attempt_pisa(raw)
        print(f"[PL4] OK  fmt=PISA(GNU)  passos={len(t)}  vars={list(d.keys())}")
        return t, d
    except Exception as exc:
        errors.append(f"  PISA: {exc}")
    for endian, elabel in [("<", "LE"), (">", "BE")]:
        for fmt in ("F32", "F64", "A", "B"):
            try:
                t, d = _attempt(raw, endian, fmt)
                print(f"[PL4] OK  endian={elabel}  fmt={fmt}  "
                      f"passos={len(t)}  vars={list(d.keys())}")
                return t, d
            except Exception as exc:
                errors.append(f"  {elabel}/{fmt}: {exc}")

    raise RuntimeError(
        "Não foi possível interpretar o .pl4.\n"
        "Tentativas:\n" + "\n".join(errors)
    )


# ══════════════════════════════════════════════════════════════════════════════
#  GRÁFICOS PLOTLY
# ══════════════════════════════════════════════════════════════════════════════

_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#17becf",
]


def _match(data: dict, node: str) -> str | None:
    """Retorna a chave do dict que contém o nome do nó (ignora prefixos ATP)."""
    for k in data:
        if node.upper() in k.upper():
            return k
    return None


def plot_results(
    time: np.ndarray,
    data: dict[str, np.ndarray],
    nodes: list[str],
    labels: dict[str, str],
    out_path: pathlib.Path,
    *,
    title: str,
    t_unit: str,
    t_scale: float,
    v_unit: str,
    v_scale: float,
) -> None:
    """Gera um HTML com dois gráficos Plotly: sobreposição + subplots por nó."""

    t = time * t_scale

    matched = {n: _match(data, n) for n in nodes}
    valid   = [n for n in nodes if matched[n] is not None]
    missing = [n for n in nodes if matched[n] is None]

    if missing:
        print(f"[PLOT] Nós não encontrados no .pl4: {missing}")
        print(f"       Chaves disponíveis: {list(data.keys())}")
    if not valid:
        raise RuntimeError("Nenhum nó pôde ser plotado.")

    # ── Figura 1: todos os nós sobrepostos ────────────────────────────────────
    fig_over = go.Figure()
    for i, node in enumerate(valid):
        v = data[matched[node]] * v_scale
        fig_over.add_trace(go.Scatter(
            x=t, y=v,
            name=labels.get(node, node),
            line=dict(color=_PALETTE[i % len(_PALETTE)], width=2),
        ))
    fig_over.update_layout(
        title=dict(text=title, font_size=15),
        xaxis_title=f"Tempo ({t_unit})",
        yaxis_title=f"Tensão ({v_unit})",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"),
        template="plotly_white",
        height=500,
        hovermode="x unified",
    )

    # ── Figura 2: subplots individuais ────────────────────────────────────────
    n = len(valid)
    fig_sub = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        subplot_titles=[labels.get(nd, nd) for nd in valid],
        vertical_spacing=0.06,
    )
    for row, node in enumerate(valid, start=1):
        v = data[matched[node]] * v_scale
        fig_sub.add_trace(
            go.Scatter(
                x=t, y=v,
                name=labels.get(node, node),
                line=dict(color=_PALETTE[(row - 1) % len(_PALETTE)], width=1.6),
                showlegend=False,
            ),
            row=row, col=1,
        )
        fig_sub.update_yaxes(
            title_text=v_unit, title_font_size=11,
            row=row, col=1,
        )
    fig_sub.update_xaxes(title_text=f"Tempo ({t_unit})", row=n, col=1)
    fig_sub.update_layout(
        title=dict(text=f"{title} — por nó", font_size=15),
        template="plotly_white",
        height=max(320, 200 * n),
        hovermode="x unified",
    )

    # ── HTML combinado ─────────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = (
        "<!DOCTYPE html><html>\n"
        "<head><meta charset='utf-8'>"
        f"<title>{title}</title></head>\n"
        "<body>\n"
        + fig_over.to_html(full_html=False, include_plotlyjs="cdn")
        + "\n<hr style='margin:36px 0'>\n"
        + fig_sub.to_html(full_html=False, include_plotlyjs=False)
        + "\n</body></html>"
    )
    out_path.write_text(html, encoding="utf-8")
    print(f"[PLOT] Salvo: {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    try:
        # 1. Rodar ATP
        _, pl4_path = run_atp(ATP_EXE, ATP_FILE)

        # 2. Ler .pl4
        time, data = read_pl4(pl4_path)

        # 3. Gerar HTML
        plot_results(
            time, data,
            nodes=NODES,
            labels=NODE_LABELS,
            out_path=OUTPUT_DIR / HTML_FILENAME,
            title=TITLE,
            t_unit=TIME_UNIT,
            t_scale=TIME_SCALE,
            v_unit=VOLT_UNIT,
            v_scale=VOLT_SCALE,
        )

    except (FileNotFoundError, RuntimeError) as exc:
        sys.exit(f"[ERRO] {exc}")


if __name__ == "__main__":
    main()
