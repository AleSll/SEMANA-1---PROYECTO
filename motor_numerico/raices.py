"""Raíces de f(x) = 0: bisección, Newton-Raphson y secante."""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class ResultadoRaiz:
    metodo: str
    raiz: float
    iteraciones: int
    convergio: bool
    residual: float                      # |f(raiz)|
    historial: list = field(default_factory=list)   # (k, x, f(x), error_abs o None)
    mensaje: str = ""


def _fila(k, x, fx, x_ref):
    return (k, float(x), float(fx), None if x_ref is None else float(abs(x - x_ref)))


def biseccion(f, a, b, tol=1e-10, max_iter=200, x_ref=None):
    """Requiere cambio de signo en [a, b]. Para si el semi-intervalo o |f| es menor que tol."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return ResultadoRaiz("Bisección", float("nan"), 0, False, float("nan"), [],
                             "No hay cambio de signo en [a, b]: no se puede acotar la raíz")
    hist = []
    c, fc = a, fa
    for k in range(1, max_iter + 1):
        c = 0.5 * (a + b)
        fc = f(c)
        hist.append(_fila(k, c, fc, x_ref))
        if abs(fc) < tol or 0.5 * (b - a) < tol:
            return ResultadoRaiz("Bisección", c, k, True, abs(fc), hist)
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return ResultadoRaiz("Bisección", c, max_iter, False, abs(fc), hist, "Máximo de iteraciones")


def newton(f, df, x0, tol=1e-10, max_iter=100, x_ref=None, m=1):
    """Newton-Raphson. m > 1 aplica el método modificado x - m f/f' para raíces de multiplicidad m.
    Criterio de parada: |x_k - x_(k-1)| < tol."""
    x = float(x0)
    hist = []
    nombre = "Newton-Raphson" if m == 1 else f"Newton modificado (m={m})"
    for k in range(1, max_iter + 1):
        fx = f(x)
        if fx == 0:                       # ya es una raíz exacta
            return ResultadoRaiz(nombre, x, k - 1, True, 0.0, hist)
        d = df(x)
        if d == 0:
            return ResultadoRaiz(nombre, x, k - 1, False, abs(fx), hist,
                                 "Derivada nula: el método no puede continuar")
        x_nuevo = x - m * fx / d
        hist.append(_fila(k, x_nuevo, f(x_nuevo), x_ref))
        if abs(x_nuevo - x) < tol:
            return ResultadoRaiz(nombre, x_nuevo, k, True, abs(f(x_nuevo)), hist)
        x = x_nuevo
    return ResultadoRaiz(nombre, x, max_iter, False, abs(f(x)), hist, "Máximo de iteraciones")


def secante(f, x0, x1, tol=1e-10, max_iter=100, x_ref=None):
    """Secante. Criterio de parada: |x_k - x_(k-1)| < tol."""
    xa, xb = float(x0), float(x1)
    fa, fb = f(xa), f(xb)
    hist = []
    for k in range(1, max_iter + 1):
        if fb == fa:
            return ResultadoRaiz("Secante", xb, k - 1, False, abs(fb), hist,
                                 "f(x_k) = f(x_(k-1)): división por cero")
        xc = xb - fb * (xb - xa) / (fb - fa)
        fc = f(xc)
        hist.append(_fila(k, xc, fc, x_ref))
        if abs(xc - xb) < tol:
            return ResultadoRaiz("Secante", xc, k, True, abs(fc), hist)
        xa, fa, xb, fb = xb, fb, xc, fc
    return ResultadoRaiz("Secante", xb, max_iter, False, abs(fb), hist, "Máximo de iteraciones")


def orden_convergencia(historial):
    """Estima el orden p a partir de e_(k+1) ~ e_k^p usando los errores del historial."""
    e = [h[3] for h in historial if h[3] is not None and h[3] > 1e-14]
    ps = [np.log(e[i + 1] / e[i + 2]) / np.log(e[i] / e[i + 1]) for i in range(len(e) - 2)
          if e[i] != e[i + 1] and e[i + 1] != e[i + 2]]
    return float(ps[-1]) if ps else None
