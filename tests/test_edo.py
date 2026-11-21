import math

import numpy as np
import pytest

from motor_numerico.edo import integrar, orden_observado


def test_desaceleracion_constante_es_exacta():
    f = lambda t, y: np.array([y[1], -0.5])
    for metodo in ("RK2", "RK4"):
        _, Y = integrar(metodo, f, 0.0, [0.0, 5.0], 0.5, 20)
        assert Y[-1, 0] == pytest.approx(25.0) and Y[-1, 1] == pytest.approx(0.0, abs=1e-12)


def test_ordenes_observados_con_desaceleracion_variable():
    a, k, v0 = 0.5, 0.1, 5.0
    T = math.log(1 + k * v0 / a) / k
    x_ref = v0 / k - a / k ** 2 * math.log(1 + k * v0 / a)
    f = lambda t, y: np.array([y[1], -(a + k * y[1])])
    hs = [0.5, 0.25, 0.125]
    for metodo, orden in (("RK2", 2), ("RK4", 4)):
        errs = []
        for h in hs:
            n = math.ceil(T / h)
            _, Y = integrar(metodo, f, 0.0, [0.0, v0], T / n, n)
            errs.append(abs(Y[-1, 0] - x_ref))
        assert orden_observado(hs, errs)[-1] == pytest.approx(orden, abs=0.15)


def test_oscilador_libre_contra_solucion_analitica():
    m, c, k, x0 = 100.0, 40.0, 400.0, 0.05
    w0 = math.sqrt(k / m); z = c / (2 * math.sqrt(k * m)); wd = w0 * math.sqrt(1 - z * z)
    x = lambda t: np.exp(-z * w0 * t) * (x0 * np.cos(wd * t) + z * w0 * x0 / wd * np.sin(wd * t))
    f = lambda t, y: np.array([y[1], (-c * y[1] - k * y[0]) / m])
    t, Y = integrar("RK4", f, 0.0, [x0, 0.0], 0.05, 400)
    assert np.max(np.abs(Y[:, 0] - x(t))) < 5e-7
