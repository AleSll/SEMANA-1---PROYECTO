"""EDO y(t)' = f(t, y): Runge-Kutta de 2.º orden (variante declarada) y de 4.º orden, paso fijo.

RK2: variante por defecto = HEUN (trapecio explícito):  k1 = f(t,y); k2 = f(t+h, y+h k1); y+ = y + h/2 (k1+k2).
     Alternativa: 'punto_medio':  k2 = f(t+h/2, y+h/2 k1);  y+ = y + h k2.   Ambas son de orden 2.
"""
import numpy as np


def rk2(f, t0, y0, h, n, variante="heun"):
    t = t0 + h * np.arange(n + 1)
    y = np.zeros((n + 1, len(y0)))
    y[0] = y0
    for i in range(n):
        k1 = np.asarray(f(t[i], y[i]), float)
        if variante == "heun":
            k2 = np.asarray(f(t[i] + h, y[i] + h * k1), float)
            y[i + 1] = y[i] + h / 2 * (k1 + k2)
        elif variante == "punto_medio":
            k2 = np.asarray(f(t[i] + h / 2, y[i] + h / 2 * k1), float)
            y[i + 1] = y[i] + h * k2
        else:
            raise ValueError("variante debe ser 'heun' o 'punto_medio'")
    return t, y


def rk4(f, t0, y0, h, n):
    t = t0 + h * np.arange(n + 1)
    y = np.zeros((n + 1, len(y0)))
    y[0] = y0
    for i in range(n):
        k1 = np.asarray(f(t[i], y[i]), float)
        k2 = np.asarray(f(t[i] + h / 2, y[i] + h / 2 * k1), float)
        k3 = np.asarray(f(t[i] + h / 2, y[i] + h / 2 * k2), float)
        k4 = np.asarray(f(t[i] + h, y[i] + h * k3), float)
        y[i + 1] = y[i] + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return t, y


def factor_amplificacion(metodo, z):
    """Función de estabilidad R(z), z = h·λ, para y' = λ y.  |R|<1: el esquema decae; |R|>1: crece."""
    if metodo == "rk2":
        return 1 + z + z ** 2 / 2
    if metodo == "rk4":
        return 1 + z + z ** 2 / 2 + z ** 3 / 6 + z ** 4 / 24
    raise ValueError("metodo debe ser 'rk2' o 'rk4'")


def orden_empirico(errores, hs):
    """Orden p ≈ log2(e(h)/e(h/2)) para hs decrecientes a la mitad."""
    ps = []
    for i in range(1, len(errores)):
        if errores[i] > 1e-15 and errores[i - 1] > 1e-15:
            ps.append(float(np.log(errores[i - 1] / errores[i]) / np.log(hs[i - 1] / hs[i])))
        else:
            ps.append(None)
    return ps
