"""Interpolación: Lagrange, Newton (diferencias divididas) y spline cúbico natural."""
import numpy as np


def lagrange(xn, yn):
    """Devuelve P(x) = sum_i y_i L_i(x)."""
    xn = np.asarray(xn, float); yn = np.asarray(yn, float)

    def P(x):
        x = np.asarray(x, float)
        total = np.zeros_like(x)
        for i in range(len(xn)):
            Li = np.ones_like(x)
            for j in range(len(xn)):
                if j != i:
                    Li = Li * (x - xn[j]) / (xn[i] - xn[j])
            total = total + yn[i] * Li
        return total
    return P


def diferencias_divididas(xn, yn):
    """Tabla triangular de diferencias divididas; la primera fila de cada columna son los coeficientes."""
    xn = np.asarray(xn, float)
    n = len(xn)
    tabla = np.zeros((n, n))
    tabla[:, 0] = yn
    for j in range(1, n):
        for i in range(n - j):
            tabla[i, j] = (tabla[i + 1, j - 1] - tabla[i, j - 1]) / (xn[i + j] - xn[i])
    return tabla


def newton_dd(xn, yn):
    """Devuelve (P, coeficientes, tabla): polinomio de Newton evaluado en forma anidada."""
    xn = np.asarray(xn, float)
    tabla = diferencias_divididas(xn, yn)
    coef = tabla[0, :].copy()

    def P(x):
        x = np.asarray(x, float)
        r = np.full_like(x, coef[-1])
        for k in range(len(coef) - 2, -1, -1):
            r = r * (x - xn[k]) + coef[k]
        return r
    return P, coef, tabla


def spline_natural(xn, yn):
    """Spline cúbico natural (S'' = 0 en los extremos). Resuelve el sistema tridiagonal para S''."""
    xn = np.asarray(xn, float); yn = np.asarray(yn, float)
    n = len(xn) - 1
    h = np.diff(xn)
    M = np.zeros(n + 1)
    if n >= 2:
        a = h[:-1].copy(); b = 2 * (h[:-1] + h[1:]); c = h[1:].copy()
        d = 6 * ((yn[2:] - yn[1:-1]) / h[1:] - (yn[1:-1] - yn[:-2]) / h[:-1])
        for i in range(1, n - 1):                       # eliminación hacia adelante (Thomas)
            w = a[i] / b[i - 1]
            b[i] -= w * c[i - 1]
            d[i] -= w * d[i - 1]
        m = np.zeros(n - 1)
        m[-1] = d[-1] / b[-1]
        for i in range(n - 3, -1, -1):                  # sustitución regresiva
            m[i] = (d[i] - c[i] * m[i + 1]) / b[i]
        M[1:n] = m

    def S(x):
        x = np.asarray(x, float)
        i = np.clip(np.searchsorted(xn, x) - 1, 0, n - 1)
        hi = h[i]
        A = (xn[i + 1] - x) / hi
        B = (x - xn[i]) / hi
        return (A * yn[i] + B * yn[i + 1]
                + ((A ** 3 - A) * M[i] + (B ** 3 - B) * M[i + 1]) * hi ** 2 / 6)
    return S


def constante_lebesgue(xn, puntos=2000):
    """Constante de Lebesgue de los nodos: amplificación máxima de perturbaciones en los datos."""
    xn = np.asarray(xn, float)
    t = np.linspace(xn[0], xn[-1], puntos)
    suma = np.zeros_like(t)
    for i in range(len(xn)):
        Li = np.ones_like(t)
        for j in range(len(xn)):
            if j != i:
                Li = Li * (t - xn[j]) / (xn[i] - xn[j])
        suma += np.abs(Li)
    return float(suma.max())
