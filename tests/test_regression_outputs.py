"""
Regressão numérica do caso padrão e sanidade dos CSVs exportados.

Valores de referência fixados na auditoria/correção de 12/06/2026
(baseline da Fase 0) e validados contra execução real do ATP
(picos concordando em <= 0,03 %):
  Pi: Vpk_in = 1000.0000 V, Vpk_out = 2039.3086 V
  T : Vpk_out = 2039.3090 V
"""
import csv

import numpy as np
import pytest

from src.models.distributed_coil import DistributedCoil
from src.sources.impulse_source import ImpulseSource
from src.solvers.time_domain_solver import TimeDomainSolver
from src.utils.result_processor import ResultProcessor
from src.utils.simulation_config import SimulationConfig

REF_VPK_OUT_PI = 2039.3086  # V
REF_VPK_OUT_T = 2039.3090   # V


def _run(cfg: SimulationConfig) -> dict:
    source = ImpulseSource(cfg.source_type, cfg.V_amplitude,
                           cfg.t_front, cfg.t_tail)
    return TimeDomainSolver(DistributedCoil(cfg), source, cfg).solve()


def test_regressao_pi_caso_padrao():
    res = _run(SimulationConfig(model_type="pi"))
    vpk_in = float(np.max(np.abs(res["V_nodes"][0])))
    vpk_out = float(np.max(np.abs(res["V_nodes"][-1])))
    # o pico real da fonte cai entre pontos da grade de reporte (dt=1e-8),
    # então o máximo amostrado fica ~4e-9 abaixo de 1000 V
    assert vpk_in == pytest.approx(1000.0, rel=1e-6)
    assert vpk_out == pytest.approx(REF_VPK_OUT_PI, rel=1e-6)


def test_regressao_t_caso_padrao():
    res = _run(SimulationConfig(model_type="t"))
    vpk_out = float(np.max(np.abs(res["V_nodes"][-1])))
    assert vpk_out == pytest.approx(REF_VPK_OUT_T, rel=1e-6)


def test_csvs_sao_legiveis_programaticamente(tmp_path):
    cfg = SimulationConfig(n_sections=4, t_total=5e-6, dt=1e-8)
    res = _run(cfg)
    proc = ResultProcessor(res, str(tmp_path))
    proc.save_csv()

    # node_voltages.csv: tempo + (N+1) nós, todas as linhas numéricas
    volts = np.genfromtxt(tmp_path / "csv" / "node_voltages.csv",
                          delimiter=",", names=True)
    assert len(volts.dtype.names) == 1 + (cfg.n_sections + 1)
    assert len(volts) == len(res["t"])
    assert not np.isnan(volts["time_s"]).any()

    # section_currents.csv
    curr = np.genfromtxt(tmp_path / "csv" / "section_currents.csv",
                         delimiter=",", names=True)
    assert len(curr) == len(res["t"])

    # summary por nó é CSV puro e re-lível
    with open(tmp_path / "csv" / "summary_nodes.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == cfg.n_sections + 1
    assert {"node_idx", "position_norm", "V_max_V", "dV_max_V"} <= set(rows[0])

    # escalares em arquivo proprio chave,valor
    with open(tmp_path / "csv" / "summary_scalars.csv", encoding="utf-8") as f:
        scalars = dict(csv.reader(f))
    for key in ("transfer_ratio", "V_peak_in_V", "V_peak_out_V"):
        float(scalars[key])  # parseável
