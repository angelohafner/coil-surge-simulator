"""
Validação da distribuição INICIAL de tensão (t=0+) com capacitância série,
contra a teoria clássica de surtos em enrolamentos (Greenwood, "Electrical
Transients in Power Systems"; Blume & Boyajian, "Abnormal voltages in
transformers").

No instante do degrau de surto os indutores bloqueiam a corrente e a tensão
se distribui pela rede puramente capacitiva (série C_s entre nós + shunt C_g
para a referência), com parâmetro de distribuição
alpha = sqrt(C_g/C_s) = sqrt(C_total/C_series_total):

  neutro aterrado : V(x)/V0 = sinh(alpha*(1-x)) / sinh(alpha)
  neutro isolado  : V(x)/V0 = cosh(alpha*(1-x)) / cosh(alpha)

Quanto maior alpha, mais a tensão se concentra nas primeiras seções (fator de
concentração na entrada: alpha*coth(alpha) aterrado, alpha*tanh(alpha)
isolado) — o mecanismo que estressa o isolamento de entrada de
transformadores/reatores e que o modelo só-shunt (C_series_total=0) não
reproduz.
"""
import numpy as np
import pytest

from src.models.distributed_coil import DistributedCoil
from src.sources.impulse_source import ImpulseSource
from src.solvers.time_domain_solver import TimeDomainSolver
from src.utils.simulation_config import SimulationConfig


def _coil(termination, N=200, C_total=1e-9, C_series_total=1e-11):
    """Bobina Pi com capacitância série; alpha = sqrt(C_total/C_series_total)."""
    cfg = SimulationConfig(
        n_sections=N, C_total=C_total, C_series_total=C_series_total,
        model_type="pi", termination=termination,
    )
    return DistributedCoil(cfg), float(np.sqrt(C_total / C_series_total))


def test_serie_desligada_por_padrao():
    """Sem C_series_total a distribuição inicial é degenerada e o caminho
    diagonal (só-shunt) permanece em uso."""
    coil = DistributedCoil(SimulationConfig())
    assert coil.has_series_c is False
    assert coil.alpha_dist == float("inf")
    assert coil._cap_lu is None
    with pytest.raises(ValueError):
        coil.initial_voltage_distribution()


def test_distribuicao_inicial_aterrada_bate_sinh():
    coil, alpha = _coil("grounded")
    x, V = coil.initial_voltage_distribution(v_input=1.0)
    analytic = np.sinh(alpha * (1.0 - x)) / np.sinh(alpha)
    assert V[0] == pytest.approx(1.0)
    assert V[-1] == pytest.approx(0.0, abs=1e-12)   # neutro aterrado
    assert np.max(np.abs(V - analytic)) < 5e-3


def test_distribuicao_inicial_isolada_bate_cosh():
    coil, alpha = _coil("open")
    x, V = coil.initial_voltage_distribution(v_input=1.0)
    analytic = np.cosh(alpha * (1.0 - x)) / np.cosh(alpha)
    assert V[0] == pytest.approx(1.0)
    # o meio-capacitor terminal C/2 introduz desvio O(1/N) perto da saída
    assert np.max(np.abs(V - analytic)) < 1e-2


def test_concentracao_na_entrada_cresce_com_alpha():
    """A queda de tensão na primeira seção (estresse de entrada) cresce com
    alpha: enrolamento mais 'concentrado' = primeira espira mais solicitada."""
    quedas = []
    for cs in (1e-9, 1e-10, 1e-11):     # alpha = 1, ~3.16, 10
        coil, _ = _coil("grounded", C_series_total=cs)
        _, V = coil.initial_voltage_distribution()
        quedas.append(V[0] - V[1])
    assert quedas[0] < quedas[1] < quedas[2]


def test_fator_de_concentracao_aterrado():
    """O gradiente inicial na entrada vale ~ alpha*coth(alpha) vezes o
    gradiente da distribuição uniforme (V0 por comprimento unitário)."""
    coil, alpha = _coil("grounded", N=400)
    x, V = coil.initial_voltage_distribution(v_input=1.0)
    # gradiente discreto na entrada, normalizado pelo passo dx=1/N
    grad_entrada = (V[0] - V[1]) / (x[1] - x[0])
    esperado = alpha / np.tanh(alpha)        # alpha*coth(alpha)
    assert grad_entrada == pytest.approx(esperado, rel=2e-2)


def test_convergencia_para_o_continuo():
    """O erro contra a solução analítica decresce ao refinar N."""
    errs = []
    for N in (25, 100, 400):
        coil, alpha = _coil("grounded", N=N)
        x, V = coil.initial_voltage_distribution()
        analytic = np.sinh(alpha * (1.0 - x)) / np.sinh(alpha)
        errs.append(float(np.max(np.abs(V - analytic))))
    assert errs[2] < errs[1] < errs[0]


def test_transitorio_aceita_serie_e_preserva_entrada():
    """O solver transitório roda com C_series_total>0, permanece finito e o
    nó de entrada continua igual à fonte imposta."""
    cfg = SimulationConfig(
        n_sections=20, C_series_total=1e-11, t_total=5e-6, dt=2e-8,
    )
    src = ImpulseSource(cfg.source_type, cfg.V_amplitude, cfg.t_front, cfg.t_tail)
    res = TimeDomainSolver(DistributedCoil(cfg), src, cfg).solve()
    vpk_in = float(np.max(np.abs(res["V_nodes"][0])))
    assert vpk_in == pytest.approx(1000.0, rel=1e-3)
    assert np.all(np.isfinite(res["V_nodes"]))
