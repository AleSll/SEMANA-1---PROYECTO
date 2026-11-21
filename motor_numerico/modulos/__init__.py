"""Registro de los cuatro módulos de SIMTELE-RISK y punto de entrada único `ejecutar`."""
from . import m1_detencion, m2_deterioro, m3_oscilaciones, m4_sensores
from .comun import ErrorValidacion, aplanar_valores, validar

MODELO_VERSION = "2.0"
ESCENARIOS = ["NORMAL", "ESTRES", "MAL_CONDICIONADO"]
NOMBRE_ESCENARIO = {"NORMAL": "NORMAL", "ESTRES": "ESTRÉS", "MAL_CONDICIONADO": "MAL CONDICIONADO"}
MODULOS = {1: m1_detencion, 2: m2_deterioro, 3: m3_oscilaciones, 4: m4_sensores}


def _mod(modulo):
    try:
        return MODULOS[int(modulo)]
    except (KeyError, ValueError, TypeError):
        raise ErrorValidacion([f"Módulo inválido: {modulo!r}. Use 1, 2, 3 o 4."])


def _esc(escenario):
    e = str(escenario).upper().replace("É", "E").replace(" ", "_")
    if e not in ESCENARIOS:
        raise ErrorValidacion([f"Escenario inválido: {escenario!r}. Use NORMAL, ESTRES o MAL_CONDICIONADO."])
    return e


def catalogo():
    out = []
    for i, m in MODULOS.items():
        out.append({"id": i, "nombre": m.NOMBRE, "pregunta": m.PREGUNTA, "modelo": m.MODELO, "metodos": m.METODOS,
                    "escenarios": {e: {"defecto": m.DEFAULTS[e], "espec": {k: m.ESPEC[k] for k in m.DEFAULTS[e]}} for e in ESCENARIOS}})
    return out


def validar_parametros(modulo, escenario, parametros=None):
    m, e = _mod(modulo), _esc(escenario)
    return m.__name__, e, validar(m.ESPEC, m.DEFAULTS[e], parametros)


def ejecutar(modulo, escenario, parametros=None):
    m, e = _mod(modulo), _esc(escenario)
    p = validar(m.ESPEC, m.DEFAULTS[e], parametros)
    try:
        res = m.ejecutar(e, p)
    except ValueError as ex:
        raise ErrorValidacion([str(ex)])
    res.update({"modulo": int(modulo), "nombre_modulo": m.NOMBRE, "escenario": e, "parametros": p, "modelo_version": MODELO_VERSION})
    return res
