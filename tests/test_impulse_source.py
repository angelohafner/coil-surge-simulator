"""
Valida a forma de onda dupla exponencial contra a definição da IEC 60060-1:
  - tempo de frente T1 = 1,67*(t90 - t30), alvo 1,2 µs, tolerância ±30 %;
  - tempo até meio valor T2 (da origem virtual O1), alvo 50 µs, tol. ±20 %;
  - pico igual a V_amplitude (normalização K).
"""
import numpy as np
import pytest

from src.sources.impulse_source import ImpulseSource


def _waveform(amplitude=1000.0, t_front=1.2e-6, t_tail=50e-6):
    src = ImpulseSource("double_exp", amplitude, t_front, t_tail)
    t = np.linspace(0.0, 200e-6, 2_000_001)
    return src, t, src.evaluate_array(t)


def _front_crossing(t, v, ipk, level):
    """Instante (interpolado) em que a frente cruza `level` pela 1a vez."""
    i = int(np.argmax(v[: ipk + 1] >= level))
    assert i > 0, "nível não cruzado na frente"
    return t[i - 1] + (level - v[i - 1]) * (t[i] - t[i - 1]) / (v[i] - v[i - 1])


def test_pico_normalizado_em_v_amplitude():
    src, t, v = _waveform()
    ipk = int(v.argmax())
    assert v[ipk] == pytest.approx(1000.0, rel=1e-6)
    # instante do pico ~2,09 µs e coerente com a propriedade peak_time
    assert t[ipk] == pytest.approx(src.peak_time, abs=2e-9)
    assert src.peak_time == pytest.approx(2.089e-6, rel=1e-3)


def test_frente_iec_dentro_da_tolerancia():
    _src, t, v = _waveform()
    ipk = int(v.argmax())
    vpk = v[ipk]
    t30 = _front_crossing(t, v, ipk, 0.30 * vpk)
    t90 = _front_crossing(t, v, ipk, 0.90 * vpk)
    T1 = 1.67 * (t90 - t30)
    # IEC 60060-1: 1,2 µs ± 30 %
    assert T1 == pytest.approx(1.2e-6, rel=0.30)
    # valor de referência medido na auditoria (12/06/2026): 1,193 µs
    assert T1 == pytest.approx(1.193e-6, rel=0.01)


def test_cauda_iec_dentro_da_tolerancia():
    _src, t, v = _waveform()
    ipk = int(v.argmax())
    vpk = v[ipk]
    t30 = _front_crossing(t, v, ipk, 0.30 * vpk)
    t90 = _front_crossing(t, v, ipk, 0.90 * vpk)
    # origem virtual O1 (reta por t30/t90 extrapolada a v=0)
    t_o1 = t30 - 0.3 * (t90 - t30) / 0.6
    # meio valor na cauda
    ih = ipk + int(np.argmax(v[ipk:] <= 0.5 * vpk))
    ta, tb, va, vb = t[ih - 1], t[ih], v[ih - 1], v[ih]
    t50 = ta + (0.5 * vpk - va) * (tb - ta) / (vb - va)
    T2 = t50 - t_o1
    # IEC 60060-1: 50 µs ± 20 %
    assert T2 == pytest.approx(50e-6, rel=0.20)
    # valor de referência medido na auditoria: 52,71 µs (+5,4 %)
    assert T2 == pytest.approx(52.71e-6, rel=0.01)


def test_ramp_exp_basico():
    src = ImpulseSource("ramp_exp", 500.0, 1e-6, 10e-6)
    assert src(0.0) == 0.0
    assert src(0.5e-6) == pytest.approx(250.0)
    assert src(1e-6) == pytest.approx(500.0)
    # decaimento exponencial após a frente
    assert src(1e-6 + 10e-6) == pytest.approx(500.0 * np.exp(-1.0), rel=1e-9)
    # vetorizado consistente com escalar
    t = np.array([-1e-6, 0.3e-6, 2e-6])
    v = src.evaluate_array(t)
    assert v[0] == 0.0
    assert v[1] == pytest.approx(src(0.3e-6))
    assert v[2] == pytest.approx(src(2e-6))


def test_source_type_invalido_e_ruidoso():
    with pytest.raises(ValueError):
        ImpulseSource("degrau", 1000.0, 1.2e-6, 50e-6)
