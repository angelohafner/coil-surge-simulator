"""
Validação da fonte de onda quadrada (PWM) adicionada ao ImpulseSource, e
regressão garantindo que double_exp / ramp_exp permanecem intactos.

A onda quadrada é unipolar 0 -> A, periodo T = 1/f, com bordas trapezoidais de
duracao t_rise (= t_front) e dv/dt = +-A/t_rise nas bordas. Cada borda e um
mini-surto: a frente rapida concentra a tensao na entrada como no impulso.
"""
import numpy as np
import pytest

from src.sources.impulse_source import ImpulseSource

F = 20_000.0          # 20 kHz
T = 1.0 / F           # 50 us
A = 1000.0            # 1 kV
TR = 0.2e-6           # tempo de borda (t_rise)


def _sq():
    return ImpulseSource(source_type="square", amplitude=A, t_front=TR, frequency=F)


def test_platos_e_amplitude():
    s = _sq()
    assert s(0.0) == pytest.approx(0.0)                       # inicio
    assert s(TR + (T / 2 - TR) / 2) == pytest.approx(A)       # plato alto
    assert s(T / 2 + TR + (T / 2 - TR) / 2) == pytest.approx(0.0)  # plato baixo


def test_bordas_lineares():
    s = _sq()
    assert s(TR / 2) == pytest.approx(A / 2, rel=1e-6)            # subida
    assert s(T / 2 + TR / 2) == pytest.approx(A / 2, rel=1e-6)    # descida


def test_derivada_bordas_e_platos():
    s = _sq()
    assert s.derivative(TR / 2) == pytest.approx(A / TR)              # subida
    assert s.derivative(T / 2 + TR / 2) == pytest.approx(-A / TR)     # descida
    assert s.derivative(TR + (T / 2 - TR) / 2) == pytest.approx(0.0)  # plato alto
    assert s.derivative(T / 2 + TR + (T / 2 - TR) / 2) == pytest.approx(0.0)


def test_periodicidade():
    s = _sq()
    for t in np.linspace(0, T, 37):
        assert s(t) == pytest.approx(s(t + 5 * T), abs=1e-9)


def test_evaluate_array_bate_com_call():
    s = _sq()
    ts = np.linspace(0, 3 * T, 500)
    assert np.allclose(s.evaluate_array(ts), [s(t) for t in ts], atol=1e-9)


def test_pico_e_peak_time():
    s = _sq()
    ts = np.linspace(0, 2 * T, 5000)
    assert np.max(s.evaluate_array(ts)) == pytest.approx(A)
    assert s.peak_time == pytest.approx(TR)


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        ImpulseSource(source_type="square", t_front=0.0, frequency=F)   # borda nula
    with pytest.raises(ValueError):
        ImpulseSource(source_type="square", t_front=T, frequency=F)     # borda >= T/2
    with pytest.raises(ValueError):
        ImpulseSource(source_type="square", t_front=TR, frequency=0.0)  # f invalida


def test_regressao_double_exp_intacto():
    s = ImpulseSource(source_type="double_exp", amplitude=A,
                      t_front=1.2e-6, t_tail=50e-6)
    assert s(s.peak_time) == pytest.approx(A, rel=1e-6)   # pico normalizado = A
    assert s(-1e-9) == 0.0


def test_regressao_ramp_exp_intacto():
    s = ImpulseSource(source_type="ramp_exp", amplitude=A,
                      t_front=1.2e-6, t_tail=50e-6)
    assert s(0.6e-6) == pytest.approx(A * 0.6e-6 / 1.2e-6)   # rampa linear
    assert s(1.2e-6) == pytest.approx(A)                      # fim da frente
