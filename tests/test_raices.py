import math

import pytest

from motor_numerico.raices import biseccion, newton, orden_convergencia, secante

D = lambda t: 0.0005 * t ** 2 + 0.015 * t - 0.30
dD = lambda t: 0.001 * t + 0.015
RAIZ = (-0.015 + math.sqrt(0.015 ** 2 + 4 * 0.0005 * 0.30)) / 0.001


def test_los_tres_metodos_encuentran_la_raiz_del_modulo_2():
    assert RAIZ == pytest.approx(13.72, abs=5e-3)
    for r in (biseccion(D, 0, 50, x_ref=RAIZ), newton(D, dD, 30, x_ref=RAIZ), secante(D, 0, 10, x_ref=RAIZ)):
        assert r.convergio and r.raiz == pytest.approx(RAIZ, abs=1e-8)


def test_newton_converge_cuadraticamente_en_raiz_simple():
    r = newton(D, dD, 30, x_ref=RAIZ)
    assert r.iteraciones <= 7 and orden_convergencia(r.historial) > 1.8


def test_biseccion_sin_cambio_de_signo():
    r = biseccion(lambda t: 0.05 * (t - 10) ** 2, 0, 20)
    assert not r.convergio and "cambio de signo" in r.mensaje


def test_raiz_doble_newton_lineal_y_modificado_en_un_paso():
    g = lambda t: 0.05 * (t - 10) ** 2
    dg = lambda t: 0.1 * (t - 10)
    r = newton(g, dg, 14, x_ref=10)
    assert r.convergio and r.iteraciones > 25 and orden_convergencia(r.historial) == pytest.approx(1.0, abs=0.05)
    m = newton(g, dg, 14, x_ref=10, m=2)
    assert m.convergio and m.iteraciones == 1 and m.raiz == pytest.approx(10.0)


def test_derivada_nula_y_division_por_cero():
    assert not newton(lambda x: x ** 2 + 1, lambda x: 2 * x, 0).convergio
    assert not secante(lambda x: 1.0, 0, 1).convergio
