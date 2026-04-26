# Distributed Coil — Surge (Impulse) Response Simulator

Simulates how a high-voltage surge propagates along a coil modelled by
distributed parameters (cascaded Pi or T sections).  The tool produces
numerical results (CSV), static figures (PNG) and animated GIFs that
clearly show travelling waves, reflections and the non-uniform initial
voltage distribution.

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run with the bundled default case
python main.py

# 3. (Optional) Use a custom configuration
python main.py --config config/my_case.json
```

All output lands in `output/`:

```
output/
  csv/           node_voltages.csv  section_currents.csv  summary.csv
  figures/       io_voltage.png  section_voltages.png  max_voltage.png
                 gradient.png  heatmap.png
  t_model/       (same set of figures for the T model)
  gifs/          voltage_wave_pi.gif   voltage_wave_t.gif
                 heatmap_anim.gif
                 comparison_capacitance.gif
                 comparison_model.gif
```

---

## Project structure

```
project_root/
  main.py                 entry point
  requirements.txt
  config/
    default_case.json     editable simulation parameters
  src/
    models/
      coil_section.py     CoilSection  — per-section data container
      distributed_coil.py DistributedCoil — ODE right-hand side
    solvers/
      time_domain_solver.py TimeDomainSolver — RK45 wrapper
    sources/
      impulse_source.py   ImpulseSource — double-exp / ramp-exp waveforms
    visualization/
      plot_generator.py   PlotGenerator — static PNG figures
      gif_generator.py    GifGenerator  — animated GIFs
    utils/
      simulation_config.py SimulationConfig — parameter dataclass
      result_processor.py  ResultProcessor — CSV export + derived quantities
  output/                 created automatically at run time
```

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

    x = [ V_m0, …, V_m(N−1),   α₀, …, α_{N−1} ]

where V_mk is the voltage at the midpoint capacitor of section k, and αk
is the current at junction k (between sections k−1 and k).

KCL at midpoint k (0 ≤ k ≤ N−2):

    C_sec · dV_mk/dt = α_k − α_{k+1}

KCL at midpoint N−1 (open circuit):

    C_sec · dV_m(N−1)/dt = α_{N−1}

KVL for α₀ (left half of section 0):

    (L/2) · dα₀/dt = V_src − V_m0 − (R/2) · α₀

KVL for α_k (k ≥ 1, combined junction, full L and R):

    L · dα_k/dt = V_m(k−1) − V_mk − R · α_k

> The junction voltage V_{j_k} cancels when the right-half equation of
> section k−1 and the left-half equation of section k are added, because
> both carry the same current α_k.

### Solver

`scipy.integrate.solve_ivp(method='RK45')` with relative tolerance 1 × 10⁻⁷
and absolute tolerance 1 × 10⁻¹².  The adaptive step-size keeps the local
truncation error small while reporting results at equally-spaced intervals
given by the `dt` parameter.

---

## Impulse source

### Double-exponential  (default, IEC 60060 style)

    V(t) = V_amplitude · K · (e^{−αt} − e^{−βt})

    α = ln(2) / T₂          (T₂ = tail time, 50 % decay)
    β = 3.0   / T₁          (T₁ = front time, empirical)
    K = 1 / (e^{−αt_p} − e^{−βt_p})    normalisation to unit peak

For a standard **1.2 / 50 µs lightning impulse**: α ≈ 1.39 × 10⁴ s⁻¹,
β ≈ 2.50 × 10⁶ s⁻¹.

### Ramp-exponential  (alternative)

    V(t) = V_amplitude · t / T₁         for t ≤ T₁
    V(t) = V_amplitude · e^{−(t−T₁)/T₂} for t > T₁

---

## Configuration reference (`config/default_case.json`)

| Key | Unit | Default | Description |
|-----|------|---------|-------------|
| `n_sections` | — | 20 | Number of cascaded sections |
| `L_total` | H | 0.01 | Total coil inductance |
| `R_total` | Ω | 5.0 | Total series resistance |
| `C_total` | F | 1 × 10⁻⁹ | Total capacitance to ground |
| `model_type` | — | "pi" | `"pi"` or `"t"` |
| `source_type` | — | "double_exp" | `"double_exp"` or `"ramp_exp"` |
| `V_amplitude` | V | 1000 | Peak source voltage |
| `t_front` | s | 1.2 × 10⁻⁶ | Impulse front time T₁ |
| `t_tail` | s | 50 × 10⁻⁶ | Impulse tail time T₂ |
| `t_total` | s | 50 × 10⁻⁶ | Simulation duration |
| `dt` | s | 10 × 10⁻⁹ | Reporting time step |
| `termination` | — | "open" | `"open"` or `"resistive"` |
| `R_term` | Ω | 10⁶ | Load resistance (if `"resistive"`) |
| `output_dir` | — | "output" | Root folder for results |

---

## Output files

| File | Contents |
|------|----------|
| `csv/node_voltages.csv` | Voltage at every node, every time step |
| `csv/section_currents.csv` | Inductor current in every section |
| `csv/summary.csv` | Peak voltage and peak gradient per node |
| `figures/io_voltage.png` | Input vs output voltage time traces |
| `figures/section_voltages.png` | Voltage at 6 selected nodes vs time |
| `figures/max_voltage.png` | Bar chart of peak voltage per node |
| `figures/gradient.png` | Bar chart of peak ΔV between adjacent nodes |
| `figures/heatmap.png` | 2-D colour map: position × time |
| `gifs/voltage_wave_pi.gif` | Animated wave propagation (Pi model) |
| `gifs/voltage_wave_t.gif` | Animated wave propagation (T model) |
| `gifs/heatmap_anim.gif` | Animated heatmap with time cursor |
| `gifs/comparison_capacitance.gif` | Low-C vs high-C side-by-side |
| `gifs/comparison_model.gif` | Pi vs T model side-by-side |

---

## Physical interpretation of key results

* **Non-uniform initial distribution** — At t = 0⁺ (before current flows
  through inductors), the voltage appears only at the input node and the
  rest of the coil is at zero.  The energy is initially stored in the
  input capacitance.

* **Travelling wave** — The wave front propagates at speed
  v = 1 / √(L_total · C_total) along the coil.  For the default
  parameters (L = 10 mH, C = 1 nF), the one-way travel time is
  ≈ 3.2 µs.

* **Reflection at open end** — With an open-circuit termination the
  reflection coefficient is +1, so the reflected wave doubles the voltage
  at the output end.

* **Surge impedance** — Z₀ = √(L / C) ≈ 3162 Ω for the default case.
  Matching the termination to Z₀ eliminates reflections.

---

## Limitations

1. **No inter-winding (turn-to-turn) capacitance** — Including it would
   require additional state variables and complicates the topology
   significantly.  The model assumes only shunt (winding-to-ground) capacitance.

2. **Lumped-parameter approximation** — Accuracy improves with more sections
   (larger N) but computation time grows linearly.

3. **Linear model** — Core saturation, frequency-dependent skin-effect
   resistance and dielectric losses are not included.

4. **Double-exp front approximation** — The `β = 3/T₁` empirical relation
   is accurate to within ±10 % for standard lightning and switching impulse
   shapes.  For high accuracy use the exact IEC 60060-1 coefficients.

---

## Dependencies

| Package | Version |
|---------|---------|
| numpy | ≥ 1.24 |
| scipy | ≥ 1.10 |
| matplotlib | ≥ 3.7 |
| imageio | ≥ 2.27 |
| Pillow | ≥ 9.5 |

Install with:  `pip install -r requirements.txt`
