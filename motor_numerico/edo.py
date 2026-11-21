"""EDO y = f(t, y): RK2 (variante de Heun, o trapecio mejorado) y RK4 clásico."""
import numpy as np


def _paso_rk2(f, t, y, h):
    """Heun: k1 = f(t, y); k2 = f(t+h, y+h k1); y' = y + h (k1 + k2) / 2."""
    k1 = f(t, y)
    k2 = f(t + h, y + h * k1)
    return y + h * (k1 + k2) / 2


def _paso_rk4(f, t, y, h):
    k1 = f(t, y)
    k2 = f(t + h / 2, y + h * k1 / 2)
    k3 = f(t + h / 2, y + h * k2 / 2)
    k4 = f(t + h, y + h * k3)
    return y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6


METODOS = {"RK2": _paso_rk2, "RK4": _paso_rk4}


def integrar(metodo, f, t0, y0, h, n):
    """Avanza n pasos de tamaño h. Devuelve (t, Y) con Y de forma (n+1, dim)."""
    paso = METODOS[metodo]
    y = np.atleast_1d(np.asarray(y0, float))
    t = t0 + h * np.arange(n + 1)
    Y = np.zeros((n + 1, len(y)))
    Y[0] = y
    for k in range(n):
        y = paso(f, t[k], y, h)
        Y[k + 1] = y
    return t, Y


def orden_observado(hs, errores):
    """Orden p estimado entre pasos consecutivos: p = log(e1/e2) / log(h1/h2)."""
    return [float(np.log(errores[i] / errores[i + 1]) / np.log(hs[i] / hs[i + 1]))
            if errores[i] > 0 and errores[i + 1] > 0 else None for i in range(len(hs) - 1)]
