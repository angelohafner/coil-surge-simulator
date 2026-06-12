"""
Garante que entradas inválidas de configuração falham ruidosamente
(auditoria, achado A5: typo em `termination` virava 'resistive' silencioso).
"""
import json
import warnings

import pytest

from src.utils.simulation_config import SimulationConfig


def test_default_e_valido():
    SimulationConfig()  # não levanta


@pytest.mark.parametrize("kwargs", [
    {"termination": "opne"},          # typo — era o erro silencioso A5
    {"termination": "Open "},         # espaço extra
    {"model_type": "gamma"},
    {"source_type": "degrau"},
    {"n_sections": 0},
    {"n_sections": 2.5},
    {"L_total": -0.01},
    {"C_total": 0.0},
    {"t_front": 0.0},
    {"V_amplitude": -1.0},
    {"dt": 1e-4, "t_total": 5e-5},    # dt >= t_total
    {"termination": "resistive", "R_term": 0.0},
    {"rtol": 0.0},
    {"c_scenario_multipliers": [0.1, -10.0]},
])
def test_configuracao_invalida_levanta_valueerror(kwargs):
    with pytest.raises(ValueError):
        SimulationConfig(**kwargs)


def test_r_total_zero_e_permitido():
    SimulationConfig(R_total=0.0)  # caso sem perdas é físico e usado em teste


def test_termination_validas():
    SimulationConfig(termination="open")
    SimulationConfig(termination="resistive", R_term=3162.0)
    SimulationConfig(termination="OPEN")  # case-insensitive


def test_from_json_rejeita_chave_desconhecida(tmp_path):
    cfg = {"n_sections": 4, "C_Total": 1e-9}  # typo de capitalização
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(ValueError, match="C_Total"):
        SimulationConfig.from_json(str(path))


def test_from_json_avisa_chaves_ausentes(tmp_path):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps({"n_sections": 4}), encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cfg = SimulationConfig.from_json(str(path))
    assert cfg.n_sections == 4
    assert any("C_total" in str(w.message) for w in caught)


def test_copy_with_revalida():
    cfg = SimulationConfig()
    with pytest.raises(ValueError):
        cfg.copy_with(termination="aberto")
