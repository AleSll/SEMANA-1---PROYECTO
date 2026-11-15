"""Sistemas lineales A x = b: Jacobi, Gauss-Seidel, LU y gradiente conjugado."""
from dataclasses import dataclass, field

import numpy as np

from .errores import residuo

DIVERGENCIA = 1e15  # se detiene un iterativo si el residuo supera este valor


@dataclass
class Resultado:
    metodo: str
    x: np.ndarray
    iteraciones: int
    convergio: bool
    residuo: float
    historial: list = field(default_factory=list)  # (k, x, residuo, error o None)


def _paso(hist, k, x, A, b, x_ref):
    r = residuo(A, b, x)
    e = None if x_ref is None else float(np.max(np.abs(x - x_ref)))
    hist.append((k, x.copy(), r, e))
    return r


def jacobi(A, b, x0=None, tol=1e-8, max_iter=100_000, x_ref=None):
    A = np.asarray(A, float); b = np.asarray(b, float)
    x = np.zeros(len(b)) if x0 is None else np.asarray(x0, float).copy()
    D = np.diag(A); R = A - np.diagflat(D); hist = []
    for k in range(1, max_iter + 1):
        x = (b - R @ x) / D
        r = _paso(hist, k, x, A, b, x_ref)
        if r < tol:
            return Resultado("Jacobi", x, k, True, r, hist)
        if not np.isfinite(r) or r > DIVERGENCIA:
            return Resultado("Jacobi", x, k, False, r, hist)
    return Resultado("Jacobi", x, max_iter, False, r, hist)


def gauss_seidel(A, b, x0=None, tol=1e-8, max_iter=100_000, x_ref=None):
    A = np.asarray(A, float); b = np.asarray(b, float)
    n = len(b)
    x = np.zeros(n) if x0 is None else np.asarray(x0, float).copy()
    hist = []
    for k in range(1, max_iter + 1):
        for i in range(n):
            x[i] = (b[i] - A[i, :i] @ x[:i] - A[i, i + 1:] @ x[i + 1:]) / A[i, i]
        r = _paso(hist, k, x, A, b, x_ref)
        if r < tol:
            return Resultado("Gauss-Seidel", x, k, True, r, hist)
        if not np.isfinite(r) or r > DIVERGENCIA:
            return Resultado("Gauss-Seidel", x, k, False, r, hist)
    return Resultado("Gauss-Seidel", x, max_iter, False, r, hist)


def factorizacion_lu(A):
    """A = L U sin pivoteo (válida para A simétrica definida positiva)."""
    U = np.asarray(A, float).copy(); n = len(U); L = np.eye(n)
    for k in range(n - 1):
        for i in range(k + 1, n):
            L[i, k] = U[i, k] / U[k, k]
            U[i, k:] -= L[i, k] * U[k, k:]
    return L, U


def lu(A, b, x_ref=None):
    A = np.asarray(A, float); b = np.asarray(b, float)
    L, U = factorizacion_lu(A); n = len(b)
    y = np.zeros(n)
    for i in range(n):
        y[i] = b[i] - L[i, :i] @ y[:i]
    x = np.zeros(n)
    for i in reversed(range(n)):
        x[i] = (y[i] - U[i, i + 1:] @ x[i + 1:]) / U[i, i]
    hist = []
    r = _paso(hist, 1, x, A, b, x_ref)
    return Resultado("LU", x, 1, True, r, hist)


def gradiente_conjugado(A, b, x0=None, tol=1e-8, max_iter=1000, x_ref=None):
    """Solo para A simétrica definida positiva."""
    A = np.asarray(A, float); b = np.asarray(b, float)
    x = np.zeros(len(b)) if x0 is None else np.asarray(x0, float).copy()
    r = b - A @ x; p = r.copy(); hist = []
    for k in range(1, max_iter + 1):
        Ap = A @ p
        alfa = (r @ r) / (p @ Ap)
        x = x + alfa * p
        r_nuevo = r - alfa * Ap
        res = _paso(hist, k, x, A, b, x_ref)
        if res < tol:
            return Resultado("Gradiente conjugado", x, k, True, res, hist)
        beta = (r_nuevo @ r_nuevo) / (r @ r)
        p = r_nuevo + beta * p
        r = r_nuevo
    return Resultado("Gradiente conjugado", x, max_iter, False, res, hist)


def es_spd(A, tol=1e-12):
    A = np.asarray(A, float)
    return bool(np.allclose(A, A.T, atol=tol) and np.all(np.linalg.eigvalsh(A) > 0))


def radio_espectral(A, metodo):
    """Radio espectral de la matriz de iteración ('jacobi' o 'gauss_seidel')."""
    A = np.asarray(A, float)
    if metodo == "jacobi":
        D = np.diagflat(np.diag(A)); T = -np.linalg.inv(D) @ (A - D)
    elif metodo == "gauss_seidel":
        L = np.tril(A); T = -np.linalg.inv(L) @ (A - L)
    else:
        raise ValueError("metodo debe ser 'jacobi' o 'gauss_seidel'")
    return float(np.max(np.abs(np.linalg.eigvals(T))))


def resolver_todos(A, b, x_ref, x0=None, tol=1e-8):
    """Ejecuta los cuatro métodos sobre el mismo sistema."""
    return [jacobi(A, b, x0, tol, x_ref=x_ref), gauss_seidel(A, b, x0, tol, x_ref=x_ref),
            lu(A, b, x_ref=x_ref), gradiente_conjugado(A, b, x0, tol, x_ref=x_ref)]
