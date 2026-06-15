# Distributed Coil — Surge (Impulse) Response Simulator

Simulates how a high-voltage surge propagates along a coil modelled by
distributed parameters (cascaded Pi or T sections).  The tool produces
numerical results (CSV), static figures (PNG) and animated GIFs that
clearly show travelling waves, reflections and the non-uniform initial
voltage distribution.  The same case is described as an ATP/EMTP deck
(`surto_bobina.atp`) and the two solutions are cross-validated
quantitatively (see *Validation* below).

---

## Quick start

```bash
# 1. Install dependencies (tested versions pinned in requirements.txt)
pip install -r requirements.txt

# 2. Run with the bundled default case
python main.py

# 3. (Optional) Use a custom configuration
python main.py --config config/my_case.json

# 4. Run the test suite
python -m pytest
```

All output lands in `output/`:

```
output/
  csv/                node_voltages.csv  section_currents.csv
                      summary_nodes.csv  summary_scalars.csv
  run_metadata.json   provenance: config, git commit, versions, timestamp
  figures/            io_voltage.png  section_voltages.png  max_voltage.png
                      gradient.png  heatmap.png
  t_model/            same set of csv/figures/metadata for the T model
  low_c/  high_c/     csv + metadata for the capacitance variants
  gifs/               voltage_wave_pi.gif   voltage_wave_t.gif
                      voltage_wave_grounded.gif
                      heatmap_anim.gif       heatmap_grounded.gif
                      comparison_capacitance.gif
                      comparison_model.gif
```

---

## Project structure

```
project_root/
  main.py                 entry point (Pi, T, grounded, low-C, high-C)
  run_atp.py              runs ATP on surto_bobina.atp, parses the .pl4,
                          plots REAL ATP results (Plotly HTML)
  surto_bobina.atp        ATP/EMTP deck of the default Pi case
  requirements.txt        pinned, tested dependency versions
  config/
    default_case.json     editable simulation parameters
  scripts/
    plot_plotly.py        Plotly HTML/PNG views of the PYTHON simulation
                          (replaces the old simulate_direct/save_images)
    compare_python_atp.py quantitative Python x ATP cross-validation
  src/
    models/
      coil_section.py     CoilSection  — per-section data container
      distributed_coil.py DistributedCoil — ODE right-hand side (Pi and T)
    solvers/
      time_domain_solver.py TimeDomainSolver — solve_ivp wrapper
    sources/
      impulse_source.py   ImpulseSource — double-exp / ramp-exp waveforms
    visualization/
      plot_generator.py   PlotGenerator — static PNG figures
      gif_generator.py    GifGenerator  — animated GIFs
    utils/
      simulation_config.py SimulationConfig — validated parameter dataclass
      result_processor.py  ResultProcessor — CSV export + derived quantities
  tests/                  pytest suite (waveform IEC, regression, physics)
  docs/
    evidencias_atp_falha/ evidence of the original failed ATP run (KILL=6)
                          and of the corrected, successful run
  relatorio/              LaTeX technical report (Portuguese)
  output/                 created automatically at run time (not versioned)
```

---

## Input data provenance

The default-case parameters (`L_total = 10 mH`, `R_total = 5 Ω`,
`C_total = 1 nF`, `N = 20`, 1.2/50 µs, 1 kV) are a **didactic,
illustrative case**: round-number values chosen to produce clearly
visible travelling-wave behaviour (surge impedance ≈ 3162 Ω, one-way
travel time ≈ 3.16 µs).  They do **not** describe a specific physical
coil.  For a real study, replace them with measured or design values and
record their source in the config file kept under version control —
every run stamps the full configuration into `run_metadata.json`.

---

## Physical model

### Coil as a cascade of N sections

The coil is represented by **N identical lumped sections** connected in
cascade.  Each section models a small segment of the winding.

| Parameter | Symbol | Per-section value |
|-----------|--------|-------------------|
| Series inductance | L_sec | L_total / N |
| Series resistance | R_sec | R_total / N |
| Shunt capacitance to ground | C_sec | C_total / N |

### Pi-section topology

```
         R_sec/2      L_sec      R_sec/2
 o──[/\/\──UUUU──/\/\]──o
 |                        |
[C_sec/2]           [C_sec/2]
 |                        |
GND                      GND
```

When N sections are cascaded the half-caps at internal junctions add up
to a full C_sec.  Only the input and output terminal caps remain C_sec/2.

### T-section topology

```
    R_sec/2   L_sec/2     L_sec/2   R_sec/2
o──[/\/\──UUUU]──o──[UUUU──/\/\]──o
                  |
               [C_sec]
                  |
                 GND
```

---

## Numerical formulation — State-space ODE

The network is cast as a linear first-order system

    **dx/dt = f(t, x)**

with the source voltage V_src(t) as an external input.

### Pi-model state vector  (size 2N)

    x = [ V₁, V₂, …, V_N,   I₁, I₂, …, I_N ]

KCL at node k (1 ≤ k ≤ N−1):

    C_sec · dV_k/dt = I_k − I_{k+1}

KCL at output node N (open circuit):

    (C_sec/2) · dV_N/dt = I_N

KVL for section k (1 ≤ k ≤ N):

    L_sec · dI_k/dt = V_{k−1} − V_k − R_sec · I_k       (V₀ = V_src(t))

### T-model state vector  (size 2N for open circuit, 2N+1 for resistive)

    x = [ V_m0, …, V_m(N−1),   i_junction_0, …, i_junction_{N−1} ]

where V_mk is the voltage at the midpoint capacitor of section k, and
i_junction_k is the current at junction k (between sections k−1 and k).
With resistive termination an extra state i_out (current through the
last right half-inductor) is appended.

KCL at midpoint k (0 ≤ k ≤ N−2):

    C_sec · dV_mk/dt = i_junction_k − i_junction_{k+1}

KCL at midpoint N−1 (open circuit):

    C_sec · dV_m(N−1)/dt = i_junction_{N−1}

KVL for i_junction_0 (left half of section 0):

    (L/2) · d(i_junction_0)/dt = V_src − V_m0 − (R/2) · i_junction_0

KVL for i_junction_k (k ≥ 1, combined junction, full L and R):

    L · d(i_junction_k)/dt = V_m(k−1) − V_mk − R · i_junction_k

> The junction voltage V_{j_k} cancels when the right-half equation of
> section k−1 and the left-half equation of section k are added, because
> both carry the same current i_junction_k.

### Solver

`scipy.integrate.solve_ivp` with the method and tolerances taken from the
configuration (`solver_method`, `rtol`, `atol`; defaults RK45,
1 × 10⁻⁷, 1 × 10⁻¹²).  The adaptive step-size keeps the local truncation
error small while reporting results at equally-spaced intervals given by
the `dt` parameter.  For stiff variants (large C, very large N) switch
`solver_method` to `"Radau"`.

---

## Impulse source

### Double-exponential  (default, IEC 60060 style)

    V(t) = V_amplitude · K · (e^{−αt} − e^{−βt})

    α = ln(2) / T₂          (T₂ = tail time)
    β = FRONT_COEFF / T₁    (T₁ = front time; FRONT_COEFF = 3.0, empirical)
    K = 1 / (e^{−αt_p} − e^{−βt_p})    normalisation to unit peak

For a standard **1.2 / 50 µs lightning impulse**: α ≈ 1.39 × 10⁴ s⁻¹,
β ≈ 2.50 × 10⁶ s⁻¹.

**Measured IEC 60060-1 parameters of the implemented waveform**
(automated in `tests/test_impulse_source.py`):

| Quantity | Definition | Result | IEC tolerance |
|----------|------------|--------|---------------|
| Front time T₁ | 1.67·(t₉₀ − t₃₀) | 1.193 µs (−0.6 %) | ±30 % |
| Time to half-value T₂ | from virtual origin O₁ | 52.71 µs (+5.4 %) | ±20 % |
| Peak | normalised | V_amplitude exactly | — |

### Ramp-exponential  (alternative)

    V(t) = V_amplitude · t / T₁         for t ≤ T₁
    V(t) = V_amplitude · e^{−(t−T₁)/T₂} for t > T₁

---

## Modelling hypotheses (read before using results)

1. **Ideal voltage source (zero impedance).**  The input node voltage is
   imposed; consequently the input half-capacitance C_sec/2 of the first
   Pi section is connected directly across the source and carries no
   state variable in the Python model.  The ATP deck *does* include that
   capacitor at N0 — it draws current from the source but does not change
   any node voltage, which is why both solutions agree.
2. **α = ln2/T₂ is an approximation.**  It makes the *slow exponential
   alone* halve at T₂; the composite waveform's IEC half-value time comes
   out ≈ 52.7 µs (+5.4 %), within the ±20 % IEC tolerance.
3. **Transfer ratio slightly above 2.**  The open-circuit reflection
   doubles the incident wave; in a discrete LC ladder the dispersive
   oscillations can add a few % on top (default case: 2.039).  Values
   modestly above 2.0 are expected, not a numerical error.
4. **T model, open circuit: output node = last midpoint.**  Both points
   share one state variable, so the last spatial gap is structurally zero;
   CSV reports it empty and the gradient plot omits it (see data
   dictionary).
5. **Linear, frequency-independent model** — see *Limitations*.

---

## Configuration reference (`config/default_case.json`)

| Key | Unit | Default | Description |
|-----|------|---------|-------------|
| `n_sections` | — | 20 | Number of cascaded sections |
| `L_total` | H | 0.01 | Total coil inductance |
| `R_total` | Ω | 5.0 | Total series resistance |
| `C_total` | F | 1 × 10⁻⁹ | Total capacitance to ground |
| `C_series_total` | F | 0 | Total series (turn-to-turn) capacitance, end-to-end. `0` disables it (shunt-only model, default). When `> 0` it couples adjacent nodes and makes the t = 0⁺ distribution non-uniform (∝ cosh/sinh, with α = √(`C_total`/`C_series_total`)). Pi model only. |
| `model_type` | — | "pi" | `"pi"` or `"t"` |
| `source_type` | — | "double_exp" | `"double_exp"`, `"ramp_exp"`, or `"square"` (20 kHz PWM; see the square-wave Manim variant) |
| `V_amplitude` | V | 1000 | Peak source voltage |
| `t_front` | s | 1.2 × 10⁻⁶ | Impulse front time T₁ |
| `t_tail` | s | 50 × 10⁻⁶ | Impulse tail time T₂ |
| `t_total` | s | 20 × 10⁻⁶ | Main simulation duration |
| `dt` | s | 10 × 10⁻⁹ | Reporting time step |
| `solver_method` | — | "RK45" | scipy method (`"Radau"` for stiff cases) |
| `rtol` / `atol` | — | 1e-7 / 1e-12 | solver tolerances |
| `termination` | — | "open" | `"open"` or `"resistive"` |
| `R_term` | Ω | 10⁶ | Load resistance (if `"resistive"`) |
| `c_scenario_multipliers` | — | [0.1, 10] | C_total factors for the variant scenarios |
| `output_dir` | — | "output" | Root folder for results |

`termination="grounded"` is also supported. It ties the final coil terminal
directly to the reference node, so the surge source is between reference and
the coil input and the coil returns to reference at its far end.

The bundled default case uses a 20 µs reporting window for the main CSV and
static figures. For longer animations or late-time reflection studies, use a
custom config with `t_total = 50e-6` or larger.

All parameters are **validated on load**: out-of-range values, unknown
keys and invalid enumerations raise an error listing every problem;
missing keys fall back to defaults with an explicit warning.

---

## Output files — data dictionary

| File | Contents |
|------|----------|
| `csv/node_voltages.csv` | `time_s` + voltage per node. Pi: `V_source, V_node_1..N`. T: `V_source, V_mid_0..N-1, V_out` (open circuit: `V_out` duplicates `V_mid_N-1` — hypothesis 4) |
| `csv/section_currents.csv` | `time_s` + currents. Pi: `I_sec_1..N`. T: `I_junction_0..N-1, I_out` (`I_out` ≡ 0 for open termination, by definition) |
| `csv/summary_nodes.csv` | per node: `node_idx, position_norm, V_max_V, dV_max_V` (gap to next node; empty when there is no next node or the gap is structural — hypothesis 4) |
| `csv/summary_scalars.csv` | `transfer_ratio`, `V_peak_in_V`, `V_peak_out_V` |
| `run_metadata.json` | scenario name, ISO timestamp, git commit, library versions, full config |
| `figures/*.png` | io_voltage, section_voltages, max_voltage, gradient, heatmap |
| `gifs/*.gif` | wave animations, including the grounded-end Pi case, and scenario comparisons |

`main.py` also writes `output/grounded/` for the Pi model with the final coil
terminal tied to the reference node.

---

## ATP cross-validation

The repository carries an ATP/EMTP deck of the same default Pi case
(`surto_bobina.atp`) and tooling to validate the Python solver against it.

**Prerequisites:** an ATP installation (GNU `tpbigG.exe`).  The
executable is located via `--atp-exe`, the `ATP_EXE` environment
variable, or the default `C:\ATP\ATP\GNUATP\tpbigG.exe`.

```bash
# run ATP and plot the REAL ATP results (HTML)
python run_atp.py

# quantitative comparison (peaks, max/RMS error per node, figure)
python scripts/compare_python_atp.py

# Python-side Plotly views of the same nodes
python scripts/plot_plotly.py
```

Latest validation (12 Jun 2026, deck rev. with type-15 source, L in mH,
ICAT=1): node peaks agree within **0.03 %**; point-wise error within the
0–30 µs dielectric-interest window ≤ **1.1 %** of the 1 kV peak; late-time
point-wise differences (up to 9 % at 200 µs) are phase drift between
ATP's fixed-step trapezoidal rule and adaptive RK45, not model
divergence.  Full numbers: `output/atp/comparacao_python_atp.csv` and the
report's Section 6.

> **History note:** before 12 Jun 2026 the deck did not run at all
> (KILL = 6, column misalignment; plus latent mH and source-type-15
> errors).  The evidence and the corrected-run listing are preserved in
> `docs/evidencias_atp_falha/`.

---

## Reproducing the report figures

The LaTeX report lives in `relatorio/` (compile with
`latexmk -pdf relatorio.tex`).  Static figures are copies of `output/`
artifacts, renamed by provenance: `pi_*`/`t_*` from `main.py`,
`python_*` from `scripts/plot_plotly.py`, `atp_*` only for figures
containing real ATP data (`scripts/compare_python_atp.py`).

## Manim technical presentation

`manim_presentation.py` builds a didactic Manim Community presentation that
runs the real model on the fly (it re-simulates the Pi cases from
`config/default_case.json` instead of reading pre-made CSVs). The flow tells
the surge story end to end, focused on the shorted-end (grounded) case:

1. **Title** — a surge entering a distributed coil.
2. **Impulse source** — the 1.2/50 µs waveform and its notable points.
3. **Circuit** — the grounded-end ladder (TikZ).
4. **Initial distribution (t = 0⁺)** — at the surge front the inductors block
   current, so the coil splits the voltage like a capacitive divider. The
   slide sweeps the winding distribution factor
   `α = √(C_total/C_series_total)` from ~0.6 (uniform) up to 10 (crowded onto
   the entrance turns), reading out how much of the voltage the first 10 % of
   the winding holds, then **settles on `α = 5`** — the value carried into the
   next slide. The curve comes straight from
   `DistributedCoil.initial_voltage_distribution()` (the series/turn-to-turn
   capacitance added in *Limitations* item 1).
5. **Initial → final distribution** — the grounded time-domain animation,
   now solved **with** series capacitance (`α = 5`): the profile starts
   crowded at the entrance and relaxes toward the uniform (final) reference,
   while the per-section local-`ΔV` bars show the stress migrating from the
   entrance into the winding interior.

```bash
python main.py                       # optional: refresh output/ artifacts
manim -pql --fps 15 manim_presentation.py SurgePresentation
```

Iterate on a single slide without rendering the whole deck (the preview
classes use a short run time):

```bash
manim -pql manim_presentation.py InitialDistributionScene   # the t=0+ slide
manim -pql manim_presentation.py GroundedReturnPreview      # the time-domain slide
```

The distributed-circuit slides use TikZ sources in `assets/`.
`tikz_ladder_grounded_circuit.tex` is the active visual for the shorted-end
presentation. `tikz_ladder_circuit.tex` is kept for comparison or future
open-end variants. Mathematical symbols and units are rendered with LaTeX
where appropriate, while ordinary explanatory text uses native Manim text with
a standard system font for readability at 480p. Regenerate the PNG assets
after editing the TikZ files with:

```bash
cd assets
pdflatex -interaction=nonstopmode -halt-on-error tikz_ladder_circuit.tex
pdftocairo -png -transp -r 300 -singlefile tikz_ladder_circuit.pdf tikz_ladder_circuit
pdflatex -interaction=nonstopmode -halt-on-error tikz_ladder_grounded_circuit.tex
pdftocairo -png -transp -r 300 -singlefile tikz_ladder_grounded_circuit.pdf tikz_ladder_grounded_circuit
```

### Square-wave (PWM) variant — `manim_square_wave.py`

`manim_square_wave.py` builds an **analogous presentation for a 20 kHz square wave**
(`SquareWavePresentation`), reusing `manim_presentation.py`'s `VisualFactory`/helpers
without modifying it. The physics: a square wave is the output of a PWM inverter, and
**every switching edge is a mini-surge** — its fast `dv/dt` crowds the voltage onto the
entrance turns exactly like the 1.2/50 µs impulse (same `sinh(α(1−x))/sinh(α)`, α = 5).
The difference is **repetition**: the impulse does it once, the square wave 40000×/s,
the insulation-ageing mechanism in inverter-fed machines. The time-domain slide animates
the profile re-crowding and relaxing at each edge, with the per-section local-`ΔV` bars
(same as the surge presentation). It is driven by the `source_type="square"` waveform
added to `ImpulseSource` (unipolar trapezoidal, edge time `t_front`, frequency 20 kHz).

```bash
manim -ql manim_square_wave.py SquareWavePresentation        # quick preview
manim manim_square_wave.py SquareWavePresentation            # 1080p60
manim -ql manim_square_wave.py SquareEvolutionPreview        # just the time-domain slide
```

**Validation (composite).** The square-wave case has no *direct* ATP run — ATP has no
native square-wave source (it would require TACS). It relies on composite validation: the
ladder network is already cross-validated against ATP in the impulse case, the
`source_type="square"` waveform is validated analytically
(`tests/test_square_source.py`), and a discretisation check (N = 20 vs N = 40, peaks within
1.1 %) confirms numerical convergence. Details in `RELATORIO_VALIDACAO_ONDA_QUADRADA.md`.

---

## Physical interpretation of key results

* **Non-uniform initial distribution** — At t = 0⁺ (before current flows
  through inductors), the voltage appears only at the input node and the
  rest of the coil is at zero.  The energy is initially stored in the
  input capacitance.

* **Travelling wave** — The wave front propagates with a one-way travel
  time of √(L_total · C_total).  For the default parameters
  (L = 10 mH, C = 1 nF) that is ≈ 3.2 µs.

* **Reflection at open end** — With an open-circuit termination the
  reflection coefficient is +1, so the reflected wave approximately
  doubles the voltage at the output end (hypothesis 3).

* **Surge impedance** — Z₀ = √(L / C) ≈ 3162 Ω for the default case.
  Matching the termination to Z₀ eliminates reflections (covered by an
  automated test).

---

## Limitations

1. **Inter-winding (turn-to-turn) capacitance is optional** — By default the
   model uses only shunt (winding-to-ground) capacitance.  Set
   `C_series_total > 0` (Pi model) to add a series capacitor across each
   section's R–L branch; this couples adjacent nodes (the nodal capacitance
   matrix becomes tridiagonal, LU-factored once) and reproduces the
   non-uniform initial voltage distribution `V(x) ∝ cosh/sinh(α(1−x))` with
   `α = √(C_total/C_series_total)` — the mechanism that overstresses the
   entrance turns.  Validated analytically in
   `tests/test_initial_distribution.py`.

2. **Lumped-parameter approximation** — Accuracy improves with more
   sections (larger N); the test suite includes a convergence check
   (N = 8 → 64).

3. **Linear model** — Core saturation, frequency-dependent skin-effect
   resistance and dielectric losses are not included.

4. **Double-exp front approximation** — β = FRONT_COEFF/T₁ reproduces the
   IEC front time within −0.6 % for the 1.2/50 µs shape (measured, see
   the waveform table above).  For exact IEC coefficients fit α, β
   numerically.

---

## Validation summary

| Check | Where | Result |
|-------|-------|--------|
| Waveform vs IEC 60060-1 | `tests/test_impulse_source.py` | T₁ −0.6 %, T₂ +5.4 % (within tolerance) |
| Regression (default case) | `tests/test_regression_outputs.py` | Vpk_out Pi = 2039.3086 V, T = 2039.3090 V |
| Energy conservation (R = 0) | `tests/test_model_physics.py` | drift < 10⁻⁵ |
| Discretisation convergence | `tests/test_model_physics.py` | peak steps 110 → 75 → 14 V (N 8→64) |
| Matched termination | `tests/test_model_physics.py` | no doubling at R_term = Z₀ (Pi and T) |
| Independent solver (ATP) | `scripts/compare_python_atp.py` | peaks ≤ 0.03 %, window error ≤ 1.1 % |
| Initial distribution vs sinh theory | `tests/test_initial_distribution.py` | matches sinh/cosh, error < 5×10⁻³ |
| Square-wave source | `tests/test_square_source.py` | period, amplitude, dv/dt, periodicity; double_exp/ramp_exp regression intact |
| Square-wave response (composite) | N = 20 vs N = 40; `RELATORIO_VALIDACAO_ONDA_QUADRADA.md` | network via ATP + analytic source; peaks converge within 1.1 % |

---

## Dependencies

Tested, pinned versions in `requirements.txt` (Python 3.13.5, Windows 11):
numpy 2.4.2, scipy 1.17.1, matplotlib 3.10.8, imageio 2.37.3,
Pillow 12.1.1, plotly 6.6.0, kaleido 1.2.0, pytest 9.0.2.

Install with:  `pip install -r requirements.txt`
