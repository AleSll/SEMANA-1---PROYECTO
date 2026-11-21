"""Integración numérica: trapecio compuesto, Simpson 1/3 compuesto y Romberg."""
import numpy as np


def trapecio(f, a, b, n):
    x = np.linspace(a, b, n + 1)
    y = f(x)
    h = (b - a) / n
    return float(h * (y[0] / 2 + y[1:-1].sum() + y[-1] / 2))


def simpson13(f, a, b, n):
    if n % 2:
        raise ValueError("Simpson 1/3 compuesto requiere un número PAR de subintervalos.")
    x = np.linspace(a, b, n + 1)
    y = f(x)
    h = (b - a) / n
    return float(h / 3 * (y[0] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum() + y[-1]))


def trapecio_datos(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2))


def simpson_datos(x, y):
    """Simpson 1/3 sobre datos con paso uniforme y n par."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x) - 1
    if n % 2:
        raise ValueError("Simpson 1/3 requiere un número par de subintervalos.")
    h = (x[-1] - x[0]) / n
    return float(h / 3 * (y[0] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum() + y[-1]))


def romberg(f, a, b, niveles=6):
    """Tabla de Romberg R[i][j] (extrapolación de Richardson sobre el trapecio, n = 2^i subintervalos)."""
    R = [[0.0] * niveles for _ in range(niveles)]
    R[0][0] = trapecio(f, a, b, 1)
    for i in range(1, niveles):
        R[i][0] = trapecio(f, a, b, 2 ** i)
        for j in range(1, i + 1):
            R[i][j] = R[i][j - 1] + (R[i][j - 1] - R[i - 1][j - 1]) / (4 ** j - 1)
    return R


def tabla_refinamiento(f, a, b, ref, niveles=(1, 2, 3, 4, 5, 6, 7, 8)):
    """Trapecio, Simpson y Romberg para n = 2^k. Devuelve filas con valor y error absoluto frente a ref."""
    R = romberg(f, a, b, max(niveles) + 1)
    filas = []
    for k in niveles:
        n = 2 ** k
        t, s = trapecio(f, a, b, n), simpson13(f, a, b, n)
        r = R[k][k]
        filas.append({"n": n, "h": (b - a) / n, "trapecio": t, "e_trap": abs(t - ref),
                      "simpson": s, "e_simp": abs(s - ref), "romberg": r, "e_romb": abs(r - ref)})
    return filas
