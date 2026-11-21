import numpy as np
import pytest

from motor_numerico.interpolacion import (constante_lebesgue, diferencias_divididas, lagrange, newton_dd,
                                          spline_natural)

XN = np.linspace(0, 2 * np.pi, 9)
YN = np.sin(XN)
OCULTOS = np.array([1.0, 3.0, 5.0])


def test_pasan_por_los_nodos():
    Q, _, _ = newton_dd(XN, YN)
    for fn in (lagrange(XN, YN), Q, spline_natural(XN, YN)):
        assert np.allclose(fn(XN), YN, atol=1e-9)


def test_lagrange_y_newton_son_el_mismo_polinomio():
    Q, _, _ = newton_dd(XN, YN)
    t = np.linspace(0, 2 * np.pi, 50)
    assert np.allclose(lagrange(XN, YN)(t), Q(t), atol=1e-9)


def test_errores_en_puntos_ocultos_9_nodos():
    e_lag = np.abs(lagrange(XN, YN)(OCULTOS) - np.sin(OCULTOS))
    e_spl = np.abs(spline_natural(XN, YN)(OCULTOS) - np.sin(OCULTOS))
    assert np.allclose(e_lag, [2.05e-4, 2.62e-5, 1.58e-4], rtol=1e-2)
    assert np.allclose(e_spl, [7.45e-4, 2.98e-4, 8.95e-4], rtol=1e-2)


def test_spline_reproduce_una_recta_y_dd_de_un_polinomio():
    x = np.array([0.0, 1.0, 2.5, 4.0])
    assert np.allclose(spline_natural(x, 2 * x + 1)(np.array([0.3, 1.7, 3.2])), 2 * np.array([0.3, 1.7, 3.2]) + 1)
    T = diferencias_divididas(x, x ** 2)           # la 2.ª diferencia dividida de x^2 vale 1
    assert T[0, 2] == pytest.approx(1.0) and T[0, 3] == pytest.approx(0.0, abs=1e-12)


def test_lebesgue_equiespaciados_mucho_mayor_que_chebyshev():
    eq = np.linspace(0, 1, 20)
    ch = 0.5 * (1 + np.cos(np.pi * (2 * np.arange(20) + 1) / 40))[::-1]
    assert constante_lebesgue(eq) > 1000 * constante_lebesgue(ch)
