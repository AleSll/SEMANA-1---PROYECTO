import numpy as np
import pytest

from motor_numerico.integracion import romberg, simpson13, simpson_datos, trapecio, trapecio_datos


def test_exactitud_en_polinomios():
    assert trapecio(lambda t: 5 - 0.5 * t, 0, 10, 4) == pytest.approx(25.0)          # lineal
    q = lambda t: 0.05 * (np.asarray(t) - 10) ** 2
    assert simpson13(q, 0, 10, 2) == pytest.approx(50 / 3)                           # cuadrática
    assert trapecio(q, 0, 10, 10) == pytest.approx(50 / 3, rel=1e-2) and trapecio(q, 0, 10, 10) != pytest.approx(50 / 3, abs=1e-6)


def test_orden_de_convergencia():
    e_t = [abs(trapecio(np.sin, 0, np.pi, n) - 2) for n in (8, 16)]
    e_s = [abs(simpson13(np.sin, 0, np.pi, n) - 2) for n in (8, 16)]
    assert e_t[0] / e_t[1] == pytest.approx(4, rel=0.05)
    assert e_s[0] / e_s[1] == pytest.approx(16, rel=0.1)


def test_romberg_y_simpson_requiere_n_par():
    val, R = romberg(np.sin, 0, np.pi, 6)
    assert val == pytest.approx(2.0, abs=1e-10) and R[0, 0] == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(ValueError):
        simpson13(np.sin, 0, 1, 5)


def test_versiones_con_datos():
    t = np.linspace(0, 2, 5)
    assert trapecio_datos(t ** 2, 0.5) == pytest.approx(2.75) and simpson_datos(t ** 2, 0.5) == pytest.approx(8 / 3)
