"""Raíces de f(t) = 0: bisección, Newton-Raphson (con multiplicidad opcional) y secante.

Cada método devuelve un dict con la raíz, el número de iteraciones, si convergió, el residuo |f(raíz)|
y el historial (una fila por iteración) para construir las tablas y las gráficas.
Criterio de parada: tamaño del paso (o semiancho del intervalo) < tol. No se usa |f| < tol porque en una
raíz múltiple |f| pequeño NO implica raíz cercana (ver Módulo 1, escenario MAL CONDICIONADO).
"""
import math


def _err(x, ref):
    return None if ref is None else abs(x - ref)


def biseccion(f, a, b, tol=1e-10, max_iter=200, raiz_ref=None):
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("Bisección no aplicable: f(a) y f(b) tienen el mismo signo (no hay cambio de signo).")
    hist, c, fc = [], a, fa
    for k in range(1, max_iter + 1):
        c = 0.5 * (a + b)
        fc = f(c)
        hist.append({"k": k, "a": a, "b": b, "x": c, "fx": fc, "err": _err(c, raiz_ref), "paso": 0.5 * (b - a)})
        if fc == 0 or 0.5 * (b - a) < tol:
            return {"metodo": "Bisección", "raiz": c, "iteraciones": k, "convergio": True, "residuo": abs(fc), "historial": hist}
        if fa * fc < 0:
            b, fb = c, fc
        else:
            a, fa = c, fc
    return {"metodo": "Bisección", "raiz": c, "iteraciones": max_iter, "convergio": False, "residuo": abs(fc), "historial": hist}


def newton(f, df, x0, tol=1e-10, max_iter=100, raiz_ref=None, m=1, nombre=None):
    """Newton-Raphson. m = multiplicidad conocida de la raíz (m=1: clásico; m>1: método modificado)."""
    nombre = nombre or ("Newton-Raphson" if m == 1 else f"Newton modificado (m={m})")
    x, hist = x0, []
    for k in range(1, max_iter + 1):
        if f(x) == 0:       # ya es raíz exacta (evita declarar fallo cuando además f'(x) = 0)
            return {"metodo": nombre, "raiz": x, "iteraciones": k - 1, "convergio": True, "residuo": 0.0, "historial": hist}
        d = df(x)
        if d == 0:
            return {"metodo": nombre, "raiz": x, "iteraciones": k - 1, "convergio": False, "residuo": abs(f(x)),
                    "historial": hist, "mensaje": "f'(x)=0: Newton no puede continuar."}
        xn = x - m * f(x) / d
        paso = abs(xn - x)
        x = xn
        hist.append({"k": k, "x": x, "fx": f(x), "err": _err(x, raiz_ref), "paso": paso})
        if paso < tol:
            return {"metodo": nombre, "raiz": x, "iteraciones": k, "convergio": True, "residuo": abs(f(x)), "historial": hist}
    return {"metodo": nombre, "raiz": x, "iteraciones": max_iter, "convergio": False, "residuo": abs(f(x)), "historial": hist}


def secante(f, x0, x1, tol=1e-10, max_iter=100, raiz_ref=None):
    hist = []
    f0, f1 = f(x0), f(x1)
    for k in range(1, max_iter + 1):
        if f1 == 0:
            return {"metodo": "Secante", "raiz": x1, "iteraciones": k - 1, "convergio": True, "residuo": 0.0, "historial": hist}
        if f1 == f0:
            return {"metodo": "Secante", "raiz": x1, "iteraciones": k - 1, "convergio": False, "residuo": abs(f1),
                    "historial": hist, "mensaje": "f(x1)=f(x0): la secante es horizontal."}
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        paso = abs(x2 - x1)
        x0, f0, x1, f1 = x1, f1, x2, f(x2)
        hist.append({"k": k, "x": x1, "fx": f1, "err": _err(x1, raiz_ref), "paso": paso})
        if paso < tol:
            return {"metodo": "Secante", "raiz": x1, "iteraciones": k, "convergio": True, "residuo": abs(f1), "historial": hist}
    return {"metodo": "Secante", "raiz": x1, "iteraciones": max_iter, "convergio": False, "residuo": abs(f1), "historial": hist}


def orden_observado(errores):
    """Estimación del orden p a partir de tres errores consecutivos: p ≈ ln(e_k+1/e_k) / ln(e_k/e_k-1)."""
    e = [x for x in errores if x and x > 1e-15]
    if len(e) < 3:
        return None
    p = [math.log(e[i + 1] / e[i]) / math.log(e[i] / e[i - 1]) for i in range(1, len(e) - 1)
         if e[i] != e[i - 1] and e[i + 1] != e[i]]
    return p[-1] if p else None
