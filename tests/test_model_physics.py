"""
Testes físicos do modelo:
  - conservação de energia no caso sem perdas (R = 0, fonte nula);
  - convergência Pi x T com o refinamento da discretização (N crescente);
  - terminação resistiva casada (R_term = Z0) elimina a duplicação por
    reflexão em ambos os modelos (exercita o ramo resistivo, inclusive o
    estado extra beta do modelo T).
"""
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from src.models.distributed_coil import DistributedCoil
from src.sources.impulse_source import ImpulseSource
from src.solvers.time_domain_solver import TimeDomainSolver
from src.utils.simulation_config import SimulationConfig


def _vpk_out(cfg: SimulationConfig) -> float:
    source = ImpulseSource(cfg.source_type, cfg.V_amplitude,
                           cfg.t_front, cfg.t_tail)
    res = TimeDomainSolver(DistributedCoil(cfg), source, cfg).solve()
    return float(np.max(np.abs(res["V_nodes"][-1])))


def test_conservacao_energia_sem_perdas():
    """R = 0 e fonte ~nula: energia eletromagnética total deve ser constante.

    O estado inicial carrega um capacitor interno. Com a fonte ideal em
    ~0 V o nó de entrada fica em curto (potência trocada = V0*I1 = 0) e,
    sem resistência, a energia 0,5*C*V^2 + 0,5*L*I^2 deve se conservar.
    Valida a estrutura KCL/KVL e o mapeamento C_sec / C_sec/2 do Pi.
    """
    cfg = SimulationConfig(n_sections=6, R_total=0.0, V_amplitude=1e-30,
                           t_total=2e-5, dt=2e-8)
    coil = DistributedCoil(cfg)
    source = ImpulseSource("double_exp", 1e-30, cfg.t_front, cfg.t_tail)

    n = cfg.n_sections
    x0 = coil.initial_state()
    x0[2] = 100.0  # carrega o capacitor do nó interno 3 com 100 V

    C_node = np.full(n, coil.C_sec)
    C_node[-1] = coil.C_sec / 2.0

    def energy(x):
        return (0.5 * np.sum(C_node * x[:n] ** 2)
                + 0.5 * coil.L_sec * np.sum(x[n:] ** 2))

    t_eval = np.arange(0.0, cfg.t_total, cfg.dt)
    sol = solve_ivp(lambda t, x: coil.derivatives(t, x, source),
                    (0.0, t_eval[-1]), x0, method="RK45",
                    t_eval=t_eval, rtol=1e-9, atol=1e-14)
    assert sol.success
    energies = np.array([energy(sol.y[:, i]) for i in range(sol.y.shape[1])])
    drift = np.max(np.abs(energies - energies[0])) / energies[0]
    assert drift < 1e-5, f"deriva de energia {drift:.2e} (esperado < 1e-5)"


def test_convergencia_com_refino_da_discretizacao():
    """O pico de saída deve convergir (sequência de Cauchy) conforme N
    dobra: |Vpk(2N) - Vpk(N)| decrescente. Medido em 12/06/2026:
    N=8..64 -> 2206.1, 2095.7, 2020.2, 2005.8 V (diferenças 110/75/14)."""
    base = SimulationConfig(t_total=30e-6, dt=2e-8)
    peaks = [_vpk_out(base.copy_with(n_sections=n)) for n in (8, 16, 32, 64)]
    steps = [abs(b - a) for a, b in zip(peaks, peaks[1:])]
    assert steps[2] < steps[1] < steps[0], (
        f"picos não convergem com N: {peaks} (passos {steps})")


def test_pi_e_t_equivalentes_no_pico_de_saida():
    """Pi e T discretizam a mesma estrutura distribuída: com o mesmo N o
    pico de saída deve coincidir (diferença medida ~2e-4 V; bound 0,1 V)."""
    base = SimulationConfig(t_total=30e-6, dt=2e-8)
    for n in (8, 32):
        pk = {m: _vpk_out(base.copy_with(n_sections=n, model_type=m))
              for m in ("pi", "t")}
        assert abs(pk["pi"] - pk["t"]) < 0.1, (
            f"N={n}: Pi={pk['pi']:.4f} V difere de T={pk['t']:.4f} V")


@pytest.mark.parametrize("model", ["pi", "t"])
def test_terminacao_casada_elimina_duplicacao(model):
    """Com R_term = Z0 = sqrt(L/C) a reflexão na saída é ~nula: o pico de
    saída deve ficar próximo do pico incidente (sem a duplicação do caso
    aberto). Bound largo para acomodar discretização e perdas."""
    z0 = np.sqrt(0.01 / 1e-9)  # ~3162 ohm
    cfg = SimulationConfig(n_sections=10, model_type=model, t_total=30e-6,
                           dt=2e-8, termination="resistive", R_term=z0)
    vpk = _vpk_out(cfg)
    assert 500.0 < vpk < 1400.0, (
        f"pico {vpk:.0f} V incompatível com terminação casada ({model})")


def test_aberto_duplica_aproximadamente():
    """Sanidade física: terminação aberta deve amplificar o pico de saída
    para perto de 2x a entrada (reflexão +1)."""
    cfg = SimulationConfig(n_sections=10, t_total=30e-6, dt=2e-8)
    vpk = _vpk_out(cfg)
    assert 1.7 * 1000.0 < vpk < 2.3 * 1000.0


@pytest.mark.parametrize("model", ["pi", "t"])
def test_terminacao_aterrada_prende_no_final_na_referencia(model):
    """A grounded termination closes the surge-source loop through reference."""
    cfg = SimulationConfig(
        n_sections=8,
        model_type=model,
        termination="grounded",
        t_total=20e-6,
        dt=2e-8,
    )
    source = ImpulseSource(cfg.source_type, cfg.V_amplitude,
                           cfg.t_front, cfg.t_tail)
    res = TimeDomainSolver(DistributedCoil(cfg), source, cfg).solve()
    assert float(np.max(np.abs(res["V_nodes"][-1]))) == pytest.approx(0.0, abs=1e-12)
    assert float(np.max(np.abs(res["V_nodes"][1:-1]))) > 100.0
