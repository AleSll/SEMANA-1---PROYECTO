"""Utilidades comunes a los cuatro módulos: formato de ejecuciones, tablas, gráficos y validación."""
import math

import numpy as np

PISO_LOG = 1e-17  # valor mínimo para graficar errores nulos en escala logarítmica


class ErrorValidacion(ValueError):
    def __init__(self, mensajes):
        super().__init__("; ".join(mensajes))
        self.mensajes = list(mensajes)


def num(v):
    """Convierte a tipos JSON (float/None); NaN/inf -> None."""
    if v is None:
        return None
    v = float(v)
    return v if math.isfinite(v) else None


def lista(a):
    return [num(v) for v in np.asarray(a, float).ravel()]


def err_rel(ref, aprox):
    """Error relativo; None si la referencia es 0 (nunca se divide entre cero)."""
    ref = float(ref)
    return None if ref == 0 else abs(ref - float(aprox)) / abs(ref)


def log_seguro(v):
    v = num(v)
    return PISO_LOG if v is None or v <= PISO_LOG else v


def decimar(x, y, maximo=350):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) <= maximo:
        return x, y
    idx = np.unique(np.round(np.linspace(0, len(x) - 1, maximo)).astype(int))
    return x[idx], y[idx]


def fila(numero, aprox, residual=None, error_abs=None, error_rel=None):
    return {"numero": int(numero), "aprox": aprox, "residual": num(residual),
            "error_abs": num(error_abs), "error_rel": num(error_rel)}


def ejecucion(metodo, familia, filas, *, tolerancia=None, paso=None, max_iter=None, convergio=True, tiempo_ms=0.0,
              referencia="", valor=None, metricas=None, interpretacion="", mensaje=None):
    return {"metodo": metodo, "familia": familia, "tolerancia": num(tolerancia), "paso": num(paso),
            "max_iter": max_iter, "convergio": bool(convergio), "tiempo_ms": round(float(tiempo_ms), 3),
            "iteraciones": filas, "mensaje": mensaje,
            "resumen": {"referencia": referencia, "valor": valor,
                        "metricas": {k: num(v) for k, v in (metricas or {}).items()},
                        "interpretacion": interpretacion}}


def tabla(titulo, columnas, filas, nota=None):
    return {"titulo": titulo, "columnas": columnas, "filas": filas, "nota": nota}


def serie(nombre, x, y, tipo="linea", maximo=350):
    x, y = decimar(x, y, maximo)
    return {"nombre": nombre, "x": lista(x), "y": lista(y), "tipo": tipo}


def grafico(gid, titulo, xlabel, ylabel, series, logx=False, logy=False):
    return {"id": gid, "titulo": titulo, "xlabel": xlabel, "ylabel": ylabel, "logx": logx, "logy": logy,
            "series": series}


def validar(espec, defaults, valores):
    """Combina valores del usuario con los de defecto y valida rango/tipo. Devuelve el dict limpio."""
    limpio, errores = {}, []
    valores = valores or {}
    for k, d in defaults.items():
        v = valores.get(k, d)
        sp = espec[k]
        try:
            v = float(v)
        except (TypeError, ValueError):
            errores.append(f"{sp['label']}: debe ser un número.")
            continue
        if not math.isfinite(v):
            errores.append(f"{sp['label']}: debe ser finito.")
            continue
        if v < sp["min"] or v > sp["max"]:
            errores.append(f"{sp['label']}: {v:g} fuera del rango [{sp['min']:g}, {sp['max']:g}] {sp.get('unidad', '')}.")
            continue
        if sp.get("entero"):
            if abs(v - round(v)) > 1e-9:
                errores.append(f"{sp['label']}: debe ser entero.")
                continue
            v = int(round(v))
        limpio[k] = v
    extra = set(valores) - set(defaults)
    if extra:
        errores.append("Parámetros no reconocidos para este escenario: " + ", ".join(sorted(extra)))
    if errores:
        raise ErrorValidacion(errores)
    return limpio


def aplanar_valores(res):
    """Diccionario plano de números de un resultado, usado para comparar una simulación guardada con su relanzamiento."""
    out = {}
    for m in res["metodos"]:
        for k, v in m["resumen"]["metricas"].items():
            if v is not None:
                out[f"{m['metodo']}|{k}"] = v
        out[f"{m['metodo']}|n_iteraciones"] = float(len(m["iteraciones"]))
    for c in res.get("claves", []):
        if isinstance(c.get("valor"), (int, float)):
            out[f"clave|{c['etiqueta']}"] = float(c["valor"])
    return out


def fmt(v, d=4):
    if v is None:
        return "—"
    v = float(v)
    if v == 0:
        return "0"
    return f"{v:.{d}g}" if (abs(v) >= 1e-3 and abs(v) < 1e6) else f"{v:.2e}"
