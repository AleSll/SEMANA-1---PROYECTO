"""Interpolación: Lagrange, Newton (diferencias divididas) y spline cúbico natural."""
import numpy as np

from .sistemas_lineales import lu


def lagrange(xn, yn, x):
    xn, yn, x = np.asarray(xn, float), np.asarray(yn, float), np.atleast_1d(np.asarray(x, float))
    P = np.zeros_like(x)
    for i in range(len(xn)):
        L = np.ones_like(x)
        for j in range(len(xn)):
            if j != i:
                L *= (x - xn[j]) / (xn[i] - xn[j])
        P += yn[i] * L
    return P


def diferencias_divididas(xn, yn):
    """Tabla triangular de diferencias divididas. Devuelve la matriz (n×n); la fila 0 son los coeficientes."""
    xn, yn = np.asarray(xn, float), np.asarray(yn, float)
    n = len(xn)
    T = np.zeros((n, n))
    T[:, 0] = yn
    for j in range(1, n):
        for i in range(n - j):
            T[i, j] = (T[i + 1, j - 1] - T[i, j - 1]) / (xn[i + j] - xn[i])
    return T


def newton_dd(xn, yn, x):
    xn = np.asarray(xn, float)
    c = diferencias_divididas(xn, yn)[0]
    x = np.atleast_1d(np.asarray(x, float))
    P = np.full_like(x, c[-1])
    for k in range(len(c) - 2, -1, -1):        # esquema de Horner anidado
        P = P * (x - xn[k]) + c[k]
    return P


def spline_natural(xn, yn):
    """Spline cúbico natural (S''=0 en los extremos). Devuelve una función evaluable y las segundas derivadas M.

    Las segundas derivadas salen de un sistema tridiagonal simétrico, diagonalmente dominante, que se resuelve con LU
    (el mismo módulo de sistemas lineales de la Semana 1).
    """
    xn, yn = np.asarray(xn, float), np.asarray(yn, float)
    n = len(xn) - 1
    h = np.diff(xn)
    M = np.zeros(n + 1)
    if n >= 2:
        A = np.zeros((n - 1, n - 1))
        r = np.zeros(n - 1)
        for i in range(1, n):
            A[i - 1, i - 1] = 2 * (h[i - 1] + h[i])
            if i > 1:
                A[i - 1, i - 2] = h[i - 1]
            if i < n - 1:
                A[i - 1, i] = h[i]
            r[i - 1] = 6 * ((yn[i + 1] - yn[i]) / h[i] - (yn[i] - yn[i - 1]) / h[i - 1])
        M[1:n] = lu(A, r).x

    def S(x):
        x = np.atleast_1d(np.asarray(x, float))
        i = np.clip(np.searchsorted(xn, x) - 1, 0, n - 1)
        hi = h[i]
        a, b = xn[i + 1] - x, x - xn[i]
        return (M[i] * a ** 3 + M[i + 1] * b ** 3) / (6 * hi) + (yn[i] / hi - M[i] * hi / 6) * a \
            + (yn[i + 1] / hi - M[i + 1] * hi / 6) * b

    return S, M


def constante_lebesgue(xn, puntos=4001):
    """Λ = max_x Σ|L_i(x)|: factor máximo con que la interpolación polinomial amplifica errores en los datos."""
    xn = np.asarray(xn, float)
    x = np.linspace(xn.min(), xn.max(), puntos)
    S = np.zeros_like(x)
    for i in range(len(xn)):
        L = np.ones_like(x)
        for j in range(len(xn)):
            if j != i:
                L *= (x - xn[j]) / (xn[i] - xn[j])
        S += np.abs(L)
    return float(S.max())
