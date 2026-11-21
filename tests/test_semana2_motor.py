"""Pruebas de la Semana 2: raíces, integración, EDO, interpolación y los cuatro módulos (valores de referencia)."""
import math

import numpy as np
import pytest

from motor_numerico import edo, integracion, interpolacion, raices
from motor_numerico import modulos

T_STAR = (-0.015 + math.sqrt(0.000825)) / 0.001   # 13.7228...
f2 = lambda t: 0.0005 * t * t + 0.015 * t - 0.30


def test_raices_modulo2_semana1():
    b = raices.biseccion(f2, 0, 30, 1e-10, raiz_ref=T_STAR)
    assert [round(h["x"], 7) for h in b["historial"][:4]] == [15.0, 7.5, 11.25, 13.125]
    n = raices.newton(f2, lambda t: 0.001 * t + 0.015, 20, 1e-10, raiz_ref=T_STAR)
    assert n["historial"][0]["err"] == pytest.approx(0.563, abs=1e-3)
    assert n["historial"][1]["err"] == pytest.approx(5.41e-3, rel=1e-2)
    assert n["historial"][2]["err"] == pytest.approx(5.1e-7, rel=2e-2)
    s = raices.secante(f2, 0, 30, 1e-10)
    assert s["raiz"] == pytest.approx(T_STAR, abs=1e-8)


def test_raiz_doble_lineal_y_biseccion_inaplicable():
    g, dg = (lambda t: (t - 10) ** 2), (lambda t: 2 * (t - 10))
    n = raices.newton(g, dg, 5, 1e-10, raiz_ref=10)
    assert all(h["err"] / p == pytest.approx(0.5) for h, p in zip(n["historial"][1:6], [x["err"] for x in n["historial"][:5]]))
    m = raices.newton(g, dg, 5, 1e-10, raiz_ref=10, m=2)
    assert m["convergio"] and m["iteraciones"] == 1          # regresión: antes se declaraba fallo al caer en f'=0
    with pytest.raises(ValueError):
        raices.biseccion(g, 0, 20)


def test_integracion_ordenes():
    ref = 1 - math.exp(-1)
    e = lambda n, fn: abs(fn(lambda x: np.exp(-x), 0, 1, n) - ref)
    assert e(16, integracion.trapecio) / e(32, integracion.trapecio) == pytest.approx(4, rel=0.05)
    assert e(8, integracion.simpson13) / e(16, integracion.simpson13) == pytest.approx(16, rel=0.1)
    R = integracion.romberg(np.sin, 0, math.pi, 6)
    assert R[5][5] == pytest.approx(2.0, abs=1e-9)
    with pytest.raises(ValueError):
        integracion.simpson13(np.sin, 0, 1, 5)


def test_edo_ordenes_y_estabilidad():
    f = lambda t, y: np.array([-2 * y[0]])
    errs = {}
    for nombre, fun in (("rk2", edo.rk2), ("rk4", edo.rk4)):
        es = []
        for n in (10, 20, 40):
            t, y = fun(f, 0, [1.0], 1.0 / n, n)
            es.append(abs(y[-1, 0] - math.exp(-2)))
        errs[nombre] = math.log2(es[1] / es[2])
    assert errs["rk2"] == pytest.approx(2, abs=0.15) and errs["rk4"] == pytest.approx(4, abs=0.3)
    lam = complex(-0.999 * 2, 2 * math.sqrt(1 - 0.999 ** 2))
    assert abs(edo.factor_amplificacion("rk2", 1.2 * lam)) > 1 > abs(edo.factor_amplificacion("rk4", 1.2 * lam))


def test_interpolacion_ejemplo_semana1():
    xn = [0, 1, 2, 3]; yn = np.sin(xn)
    assert interpolacion.lagrange(xn, yn, 1.5)[0] == pytest.approx(0.975987, abs=1e-6)
    assert interpolacion.newton_dd(xn, yn, 1.5)[0] == pytest.approx(0.975987, abs=1e-6)
    S, _ = interpolacion.spline_natural(xn, yn)
    assert S(1.5)[0] == pytest.approx(0.996108, abs=1e-6)
    assert np.allclose(S(xn), yn)                              # el spline interpola los nodos
    assert interpolacion.diferencias_divididas(xn, yn)[0][3] == pytest.approx(-0.010393, abs=1e-6)


def test_modulo1_valores_analiticos():
    r = modulos.ejecutar(1, "NORMAL")
    c = {k["etiqueta"]: k["valor"] for k in r["claves"]}
    assert c["t_det (s)"] == pytest.approx(10.0) and c["d_total (m)"] == pytest.approx(32.5)
    e = modulos.ejecutar(1, "ESTRES")
    ce = {k["etiqueta"]: k["valor"] for k in e["claves"]}
    assert ce["t_det (s)"] == pytest.approx(math.log(2) / 0.05, rel=1e-9)
    assert ce["Error máx. x RK4 (m)"] < ce["Error máx. x RK2 (m)"] / 1000


def test_modulo2_reproduce_semana1():
    r = modulos.ejecutar(2, "NORMAL")
    it = {m["metodo"]: m["resumen"]["metricas"]["iteraciones"] for m in r["metodos"]}
    assert (it["Jacobi"], it["Gauss-Seidel"], it["Gradiente conjugado"]) == (24, 13, 4)
    assert dict((k["etiqueta"], k["valor"]) for k in r["claves"])["t* (meses)"] == pytest.approx(T_STAR)
    m = modulos.ejecutar(2, "MAL_CONDICIONADO")
    mm = {x["metodo"]: x for x in m["metodos"]}
    assert not mm["Jacobi"]["convergio"] and mm["Gauss-Seidel"]["resumen"]["metricas"]["iteraciones"] == 3230
    assert mm["Gradiente conjugado"]["resumen"]["metricas"]["iteraciones"] == 5


def test_modulo3_analitica_vs_independiente_y_rk2_inestable():
    from motor_numerico.modulos.m3_oscilaciones import referencia_independiente, solucion_analitica
    x, *_ = solucion_analitica(100, 40, 400, 0.05, 0, 20, 1.9)
    sol = referencia_independiente(100, 40, 400, 0.05, 0, 20, 1.9, 40)
    t = np.linspace(0, 40, 300)
    assert np.max(np.abs(x(t) - sol.sol(t)[0])) < 1e-9
    r = modulos.ejecutar(3, "MAL_CONDICIONADO")
    mm = {m["metodo"]: m for m in r["metodos"]}
    assert not mm["RK2 (Heun)"]["convergio"] and mm["RK4"]["convergio"]
    n = modulos.ejecutar(3, "NORMAL")
    assert dict((k["etiqueta"], k["valor"]) for k in n["claves"])["∫x²dt (m²·s)"] == pytest.approx(3.25e-3, rel=1e-3)


def test_modulo4_ruido_y_lebesgue():
    r = modulos.ejecutar(4, "MAL_CONDICIONADO")
    c = {k["etiqueta"]: k["valor"] for k in r["claves"]}
    assert c["Constante de Lebesgue Λ"] > 1e4
    assert c["Error oculto máx. polinomio"] > 100 * c["Error oculto máx. spline"]
    n = modulos.ejecutar(4, "NORMAL")
    assert dict((k["etiqueta"], k["valor"]) for k in n["claves"])["Error oculto máx. polinomio"] < 2e-3


def test_validacion_de_parametros():
    with pytest.raises(modulos.ErrorValidacion) as e:
        modulos.ejecutar(3, "NORMAL", {"m": -1, "k": 400})
    assert "fuera del rango" in str(e.value)
    with pytest.raises(modulos.ErrorValidacion):
        modulos.ejecutar(9, "NORMAL")
    with pytest.raises(modulos.ErrorValidacion):
        modulos.ejecutar(3, "NORMAL", {"c": 5000.0, "m": 1.0, "k": 1.0})     # ζ ≥ 1: referencia analítica no aplicable


def test_error_relativo_nunca_divide_entre_cero():
    from motor_numerico.modulos.comun import err_rel
    assert err_rel(0, 1) is None
