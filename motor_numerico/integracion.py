"""Integración numérica: trapecio compuesto, Simpson 1/3 compuesto y Romberg."""
import numpy as np


def trapecio(f, a, b, n):
    x = np.linspace(a, b, n + 1)
    y = f(x)
    h = (b - a) / n
    return float(h * (y[0] / 2 + y[1:-1].sum() + y[-1] / 2))


def simpson13(f, a, b, n):
    if n % 2:
        raise ValueError("Simpson 1/3 compuesto requiere n par")
    x = np.linspace(a, b, n + 1)
    y = f(x)
    h = (b - a) / n
    return float(h / 3 * (y[0] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum() + y[-1]))


def trapecio_datos(y, h):
    y = np.asarray(y, float)
    return float(h * (y[0] / 2 + y[1:-1].sum() + y[-1] / 2))


def simpson_datos(y, h):
    y = np.asarray(y, float)
    if (len(y) - 1) % 2:
        raise ValueError("Simpson 1/3 requiere un número par de subintervalos")
    return float(h / 3 * (y[0] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum() + y[-1]))


def romberg(f, a, b, niveles=6):
    """Devuelve (valor, tabla R). R[i][0] es el trapecio con 2^i subintervalos y
    R[i][j] = (4^j R[i][j-1] - R[i-1][j-1]) / (4^j - 1)."""
    R = np.zeros((niveles, niveles))
    for i in range(niveles):
        R[i, 0] = trapecio(f, a, b, 2 ** i)
        for j in range(1, i + 1):
            R[i, j] = (4 ** j * R[i, j - 1] - R[i - 1, j - 1]) / (4 ** j - 1)
    return float(R[niveles - 1, niveles - 1]), R


def tabla_refinamiento(f, a, b, ns, ref):
    """Filas (n, h, trapecio, error, Simpson, error) para cada número de subintervalos n (par)."""
    filas = []
    for n in ns:
        t = trapecio(f, a, b, n); s = simpson13(f, a, b, n)
        filas.append((n, (b - a) / n, t, abs(t - ref), s, abs(s - ref)))
    return filas
