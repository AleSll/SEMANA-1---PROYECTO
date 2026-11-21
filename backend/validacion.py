"""Validación de parámetros de entrada de cada módulo y escenario."""
import math

from motor_numerico.casos import ESCENARIOS, PARAMETROS

DOS_PI = 2 * math.pi


def _num(p, clave, errores, minimo=None, maximo=None, estricto_min=False, entero=False):
    v = p.get(clave)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        errores.append(f"«{clave}» debe ser un número")
        return None
    if entero and float(v) != int(v):
        errores.append(f"«{clave}» debe ser entero")
    if minimo is not None and (v <= minimo if estricto_min else v < minimo):
        errores.append(f"«{clave}» debe ser {'mayor que' if estricto_min else 'mayor o igual que'} {minimo}")
    if maximo is not None and v > maximo:
        errores.append(f"«{clave}» debe ser menor o igual que {maximo}")
    return v


def _lista(p, clave, errores, minimo=None, maximo=None, estricto_min=False, entero=False, largo=(1, 8)):
    v = p.get(clave)
    if not isinstance(v, (list, tuple)) or not (largo[0] <= len(v) <= largo[1]):
        errores.append(f"«{clave}» debe ser una lista de {largo[0]} a {largo[1]} números")
        return []
    ok = []
    for i, x in enumerate(v):
        sub = {f"{clave}[{i + 1}]": x}
        _num(sub, f"{clave}[{i + 1}]", errores, minimo, maximo, estricto_min, entero)
        ok.append(x)
    return ok


def validar(modulo, escenario, parametros):
    """Devuelve la lista de errores (vacía si los parámetros son válidos)."""
    if modulo not in PARAMETROS:
        return [f"Módulo inválido: {modulo}"]
    if escenario not in ESCENARIOS:
        return [f"Escenario inválido: {escenario}"]
    base = PARAMETROS[modulo][escenario]
    if parametros is None:
        return []
    if not isinstance(parametros, dict):
        return ["Los parámetros deben ser un objeto"]
    errores = [f"Parámetro desconocido: «{k}»" for k in parametros if k not in base]
    p = {**base, **parametros}
    if errores:
        return errores
    chequeo = {1: _m1, 2: _m2, 3: _m3, 4: _m4}[modulo]
    chequeo(escenario, p, errores)
    return errores


def _m1(esc, p, e):
    if esc == "MAL_CONDICIONADO":
        _num(p, "c", e, 0, estricto_min=True); _num(p, "t_raiz", e, 0, estricto_min=True); _num(p, "x0_newton", e)
        if isinstance(p["x0_newton"], (int, float)) and p["x0_newton"] == p["t_raiz"]:
            e.append("«x0_newton» no debe coincidir con la raíz")
        return
    v0 = _num(p, "v0", e, 0, 100, estricto_min=True); a = _num(p, "a", e, 0, 20, estricto_min=True)
    _num(p, "tr", e, 0, 30); _num(p, "k_arrastre", e, 0, 5)
    hs = _lista(p, "pasos", e, 0, estricto_min=True, largo=(1, 4))
    if v0 and a and hs and min(hs) > 0 and (v0 / a) / min(hs) > 200000:
        e.append("Hay demasiados pasos: aumente «pasos» o reduzca v0/a")


def _m2(esc, p, e):
    if esc == "MAL_CONDICIONADO":
        _num(p, "D_min", e, 0); _num(p, "beta", e, 0, estricto_min=True); _num(p, "t_min", e, 0, estricto_min=True)
        _num(p, "umbral", e); _num(p, "delta_umbral", e, 0, estricto_min=True)
        if isinstance(p["umbral"], (int, float)) and isinstance(p["D_min"], (int, float)) and p["umbral"] < p["D_min"]:
            e.append("«umbral» no puede ser menor que «D_min» (no habría raíz real)")
        return
    D0 = _num(p, "D0", e, 0); _num(p, "alpha", e, 0); _num(p, "beta", e, 0, estricto_min=True)
    u = _num(p, "umbral", e, 0, estricto_min=True)
    if D0 is not None and u is not None and u <= D0:
        e.append("«umbral» debe ser mayor que «D0»: el indicador ya lo superó en t = 0")


def _m3(esc, p, e):
    _num(p, "m", e, 0, estricto_min=True); _num(p, "k", e, 0, estricto_min=True)
    _num(p, "x0", e); _num(p, "v0", e); T = _num(p, "T", e, 0, 120, estricto_min=True)
    m, k = p.get("m"), p.get("k")
    ok = all(isinstance(v, (int, float)) and v > 0 for v in (m, k))
    if esc == "MAL_CONDICIONADO":
        h = _num(p, "h", e, 0, estricto_min=True)
        cs = _lista(p, "amortiguamientos", e, 0, estricto_min=True, largo=(1, 4))
        if T and h and T / h > 100000:
            e.append("Hay demasiados pasos: aumente «h»")
        if ok and cs and not any(c < 2 * math.sqrt(k * m) for c in cs):
            e.append("Al menos un «amortiguamientos» debe ser menor que el crítico 2·sqrt(k·m)")
        return
    c = _num(p, "c", e, 0, estricto_min=True)
    if esc == "NORMAL":
        h = _num(p, "h", e, 0, estricto_min=True)
        _num(p, "F0", e, 0); _num(p, "w", e, 0)
        if ok and c and c >= 2 * math.sqrt(k * m):
            e.append("El escenario NORMAL requiere régimen subamortiguado (c < 2·sqrt(k·m))")
        if T and h and T / h > 100000:
            e.append("Hay demasiados pasos: aumente «h»")
    else:
        F0 = _num(p, "F0", e, 0); w = _num(p, "w", e, 0)
        hs = _lista(p, "pasos", e, 0, estricto_min=True, largo=(1, 3))
        if T and hs:
            n_ref = round(T / 1e-3)
            for h in hs:
                n = round(T / h)
                if h <= 0 or abs(T / h - n) > 1e-9 or n < 1 or n_ref % n:
                    e.append(f"El paso h = {h} s debe dividir a T y ser múltiplo de 0.001 s (la referencia usa h = 0.001 s)")
                    break


def _m4(esc, p, e):
    _num(p, "sigma", e, 0, 1); _num(p, "semilla", e, 0, 10 ** 9, entero=True)
    _lista(p, "ocultos", e, 0, DOS_PI, largo=(1, 6))
    if esc == "ESTRES":
        ns = _lista(p, "n_nodos", e, 3, 60, entero=True, largo=(1, 5))
    else:
        _num(p, "n_nodos", e, 3, 60, entero=True)
