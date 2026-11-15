"""Teoría de errores transversal (usada por todos los módulos)."""
import numpy as np


def error_absoluto(ref, aprox):
    """|ref - aprox|. Para vectores devuelve la norma infinito de la diferencia."""
    return float(np.max(np.abs(np.asarray(ref, float) - np.asarray(aprox, float))))


def error_relativo(ref, aprox):
    """Error relativo en norma 2; devuelve None si la referencia es cero (sin dividir por cero)."""
    ref = np.asarray(ref, float)
    n = np.linalg.norm(ref)
    if n == 0:
        return None
    return float(np.linalg.norm(ref - np.asarray(aprox, float)) / n)


def error_porcentual(ref, aprox):
    e = error_relativo(ref, aprox)
    return None if e is None else 100.0 * e


def residuo(A, b, x):
    """Norma infinito de r = b - A x."""
    return float(np.max(np.abs(np.asarray(b, float) - np.asarray(A, float) @ np.asarray(x, float))))


def sensibilidad(A, b, db):
    """Compara la perturbación relativa de b con la del resultado y con la cota kappa*|db|/|b| (norma 2)."""
    A = np.asarray(A, float)
    b = np.asarray(b, float)
    db = np.asarray(db, float)
    x = np.linalg.solve(A, b)
    xp = np.linalg.solve(A, b + db)
    rel_b = np.linalg.norm(db) / np.linalg.norm(b)
    rel_x = np.linalg.norm(xp - x) / np.linalg.norm(x)
    kappa = np.linalg.cond(A, 2)
    return {"rel_b": float(rel_b), "rel_x": float(rel_x),
            "amplificacion": float(rel_x / rel_b), "cota": float(kappa * rel_b), "kappa": float(kappa)}
