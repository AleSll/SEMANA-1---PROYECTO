"""Los cuatro módulos de SIMTELE-RISK y sus tres escenarios (NORMAL, ESTRES, MAL_CONDICIONADO).

Cada función `modulo1..modulo4` devuelve un diccionario con:
  parametros, referencia, tablas (lista de {nombre, columnas, filas}) y graficos (series para dibujar).
Todos los datos son sintéticos y los parámetros son supuestos.
"""
import functools
import json
import math
import threading
import time
from pathlib import Path

import numpy as np

from . import edo, integracion as integ, interpolacion as interp, raices
from .errores import sensibilidad
from .sistemas_lineales import es_spd, radio_espectral, resolver_todos

ESCENARIOS = ("NORMAL", "ESTRES", "MAL_CONDICIONADO")
RUTA_SISTEMAS = Path(__file__).resolve().parents[1] / "datos_ejemplo" / "sistemas_semana1.json"

PARAMETROS = {
    1: {
        "NORMAL": {"v0": 5.0, "a": 0.5, "tr": 1.5, "pasos": [0.5], "k_arrastre": 0.1},
        "ESTRES": {"v0": 7.0, "a": 0.3, "tr": 2.0, "pasos": [2.0, 0.05], "k_arrastre": 0.1},
        "MAL_CONDICIONADO": {"c": 0.05, "t_raiz": 10.0, "x0_newton": 14.0},
    },
    2: {
        "NORMAL": {"D0": 0.10, "alpha": 0.015, "beta": 0.0005, "umbral": 0.40},
        "ESTRES": {"D0": 0.10, "alpha": 0.025, "beta": 0.0008, "umbral": 0.40},
        "MAL_CONDICIONADO": {"D_min": 0.20, "beta": 0.0005, "t_min": 20.0, "umbral": 0.20, "delta_umbral": 1e-4},
    },
    3: {
        "NORMAL": {"m": 100.0, "c": 40.0, "k": 400.0, "x0": 0.05, "v0": 0.0, "F0": 0.0, "w": 0.0,
                   "T": 20.0, "h": 0.05},
        "ESTRES": {"m": 100.0, "c": 40.0, "k": 400.0, "x0": 0.0, "v0": 0.0, "F0": 20.0, "w": 2.0,
                   "T": 60.0, "pasos": [0.1, 0.5]},
        "MAL_CONDICIONADO": {"m": 100.0, "k": 400.0, "x0": 0.05, "v0": 0.0, "T": 20.0, "h": 0.05,
                             "amortiguamientos": [399.0, 400.0]},
    },
    4: {
        "NORMAL": {"n_nodos": 9, "ocultos": [1.0, 3.0, 5.0], "sigma": 0.0, "semilla": 42},
        "ESTRES": {"n_nodos": [5, 9, 15], "ocultos": [1.0, 3.0, 5.0], "sigma": 0.05, "semilla": 42},
        "MAL_CONDICIONADO": {"n_nodos": 20, "ocultos": [0.1, 3.0, 6.2], "sigma": 1e-3, "semilla": 42},
    },
}


# ---------------------------------------------------------------- registro de ejecuciones
# Cada método ejecutado se registra (con sus iteraciones) para poder guardarlo en la base de datos.
_REG = []
_LOCK = threading.RLock()


def _fila_it(k, aprox, residual=None, error_abs=None, ref=None):
    err_rel = None
    if error_abs is not None and ref not in (None, 0):
        err_rel = float(error_abs / abs(ref))
    return {"numero": int(k), "aproximacion": [float(v) for v in np.atleast_1d(aprox)],
            "residual": None if residual is None else float(residual),
            "error_abs": None if error_abs is None else float(error_abs), "error_rel": err_rel}


def _registrar(metodo, iteraciones, convergio=True, tolerancia=None, paso=None, max_iter=None,
               referencia=None, tiempo_ms=None):
    _REG.append({"metodo": metodo, "tolerancia": tolerancia, "paso": paso, "max_iter": max_iter,
                 "convergio": bool(convergio), "tiempo_ms": tiempo_ms, "referencia": referencia,
                 "iteraciones": iteraciones})


def _reg_edo(nombre, h, t, Y, ref=None, comp=0, maximo=500):
    """Registra una integración de EDO: un registro por paso (se submuestrea a lo sumo a `maximo`)."""
    salto = max(1, len(t) // maximo)
    its = []
    for k in range(0, len(t), salto):
        e = None if ref is None else abs(Y[k, comp] - ref[k])
        its.append(_fila_it(k, Y[k], None, e, None if ref is None else ref[k]))
    _registrar(nombre, its, paso=h, referencia="solución analítica o de referencia")


def _reg_refinamiento(f, a, b, ns, ref):
    its_t, its_s = [], []
    for n in ns:
        t_ = integ.trapecio(f, a, b, n); s_ = integ.simpson13(f, a, b, n)
        its_t.append(_fila_it(n, [t_], None, abs(t_ - ref), ref))
        its_s.append(_fila_it(n, [s_], None, abs(s_ - ref), ref))
    _registrar("Trapecio compuesto", its_t, paso=(b - a) / ns[-1], referencia=f"integral = {ref:.10g}")
    _registrar("Simpson 1/3 compuesto", its_s, paso=(b - a) / ns[-1], referencia=f"integral = {ref:.10g}")


def _reg_romberg(R, ref):
    its = [_fila_it(i + 1, [R[i, i]], None, abs(R[i, i] - ref), ref) for i in range(R.shape[0])]
    _registrar("Romberg", its, referencia=f"integral = {ref:.10g}")


def _con_registro(fn):
    """Decorador: reinicia el registro, ejecuta el módulo y adjunta `ejecuciones` al resultado."""
    @functools.wraps(fn)
    def envoltura(escenario, p=None):
        with _LOCK:
            _REG.clear()
            t0 = time.perf_counter()
            r = fn(escenario, p)
            ms = (time.perf_counter() - t0) * 1000
            ejecs = list(_REG)
            for e in ejecs:
                e["tiempo_ms"] = ms / max(1, len(ejecs))
            r["ejecuciones"] = ejecs
            _REG.clear()
            return r
    return envoltura


# ---------------------------------------------------------------- utilidades
def _f(x):
    return None if x is None else float(x)


def _tabla(nombre, columnas, filas):
    return {"nombre": nombre, "columnas": columnas,
            "filas": [[(float(v) if isinstance(v, (np.floating, np.integer)) else v) for v in fila]
                      for fila in filas]}


def _resumir(t, y, maximo=400):
    paso = max(1, len(t) // maximo)
    return [float(v) for v in np.asarray(t)[::paso]], [float(v) for v in np.asarray(y)[::paso]]


def _tabla_raices(resultados, x_ref):
    for r in resultados:
        its = [_fila_it(h[0], [h[1]], abs(h[2]), h[3], x_ref) for h in r.historial]
        _registrar(r.metodo, its, r.convergio, tolerancia=1e-10, max_iter=200,
                   referencia=None if x_ref is None else f"raíz de referencia = {x_ref:.10g}")
    filas = [[r.metodo, r.iteraciones, r.convergio, _f(r.raiz),
              None if x_ref is None or not np.isfinite(r.raiz) else abs(r.raiz - x_ref),
              _f(r.residual), r.mensaje] for r in resultados]
    return _tabla("Raíces: método, iteraciones, error y residual",
                  ["Método", "Iteraciones", "Convergió", "Raíz", "Error abs.", "|f(raíz)|", "Observación"], filas)


def _param(modulo, escenario, p):
    if escenario not in ESCENARIOS:
        raise ValueError(f"Escenario inválido: {escenario}")
    return {**PARAMETROS[modulo][escenario], **(p or {})}


# ---------------------------------------------------------------- Módulo 1
def modulo1(escenario, p=None):
    p = _param(1, escenario, p)
    if escenario == "MAL_CONDICIONADO":
        return _m1_mal(p)
    v0, a, tr, k = p["v0"], p["a"], p["tr"], p["k_arrastre"]
    T = v0 / a
    d_f = v0 ** 2 / (2 * a)
    ref = {"t_det": T, "d_frenado": d_f, "d_total": v0 * tr + d_f}
    tablas, graficos = [], []

    f_const = lambda t, y: np.array([y[1], -a])
    filas = []
    for h in p["pasos"]:
        n = math.ceil(T / h)
        for m in ("RK2", "RK4"):
            t_, Y = edo.integrar(m, f_const, 0.0, [0.0, v0], T / n, n)
            _reg_edo(f"{m} (h = {h} s)", T / n, t_, Y, ref=v0 * t_ - a * t_ ** 2 / 2)
            filas.append([m, h, n, Y[-1, 0], abs(Y[-1, 0] - d_f), Y[-1, 1], abs(Y[-1, 1])])
    tablas.append(_tabla("EDO con desaceleración constante: estado en t = v0/a",
                         ["Método", "h nominal (s)", "Pasos", "x(T) (m)", "Error x", "v(T) (m/s)", "Error v"], filas))

    v_fun = lambda t: v0 - a * np.asarray(t)
    filas = [[n, T / n, tr_, e_t, s, e_s] for n, _, tr_, e_t, s, e_s in
             integ.tabla_refinamiento(v_fun, 0.0, T, [2, 4, 8, 16], d_f)]
    _reg_refinamiento(v_fun, 0.0, T, [2, 4, 8, 16], d_f)
    val, R = integ.romberg(v_fun, 0.0, T, 4)
    _reg_romberg(R, d_f)
    filas.append(["Romberg (4 niveles)", None, val, abs(val - d_f), None, None])
    tablas.append(_tabla("Distancia de frenado = integral de v(t): trapecio, Simpson y Romberg",
                         ["n", "h", "Trapecio", "Error", "Simpson 1/3", "Error"], filas))

    g = lambda t: v0 - a * t
    dg = lambda t: -a
    tablas.append(_tabla_raices([raices.biseccion(g, 0.0, 2 * T, x_ref=T), raices.newton(g, dg, T / 4, x_ref=T),
                                 raices.secante(g, 0.0, T / 2, x_ref=T)], T)
                  | {"nombre": "Instante de detención v(t) = 0"})

    # Ampliación: desaceleración variable a(v) = a + k v, con solución analítica
    T_v = math.log(1 + k * v0 / a) / k
    x_v = v0 / k - a / k ** 2 * math.log(1 + k * v0 / a)
    ref["ampliacion"] = {"t_det": T_v, "d_frenado": x_v, "k": k}
    f_var = lambda t, y: np.array([y[1], -(a + k * y[1])])
    hs = [1.0, 0.5, 0.25, 0.125]
    filas = []
    for m in ("RK2", "RK4"):
        errs = []
        for h in hs:
            n = math.ceil(T_v / h)
            t_, Y = edo.integrar(m, f_var, 0.0, [0.0, v0], T_v / n, n)
            x_an = (v0 + a / k) * (1 - np.exp(-k * t_)) / k - a * t_ / k
            _reg_edo(f"{m} con a(v) (h = {h} s)", T_v / n, t_, Y, ref=x_an)
            errs.append(abs(Y[-1, 0] - x_v))
        ords = [None] + edo.orden_observado(hs, errs)
        filas += [[m, h, e, o] for h, e, o in zip(hs, errs, ords)]
    tablas.append(_tabla("Ampliación a(v) = a + k v: error de la distancia de frenado y orden observado",
                         ["Método", "h (s)", "Error x(T)", "Orden p"], filas))

    n = math.ceil(T / p["pasos"][0])
    t, Y = edo.integrar("RK4", f_const, 0.0, [0.0, v0], T / n, n)
    graficos.append({"titulo": "Velocidad y posición durante el frenado", "x": [float(u) for u in t],
                     "series": {"v(t) RK4": [float(u) for u in Y[:, 1]], "x(t) RK4": [float(u) for u in Y[:, 0]],
                                "v(t) analítica": [float(u) for u in v_fun(t)]}, "xlabel": "t (s)"})
    e2 = [r_ for r_ in filas if r_[0] == "RK2"]; e4 = [r_ for r_ in filas if r_[0] == "RK4"]
    graficos.append({"titulo": "Error vs paso (ampliación a(v))", "x": hs, "escala": "loglog", "xlabel": "h (s)",
                     "series": {"RK2": [r_[2] for r_ in e2], "RK4": [r_[2] for r_ in e4]}})
    return {"modulo": 1, "escenario": escenario, "parametros": p, "referencia": ref,
            "tablas": tablas, "graficos": graficos}


def _m1_mal(p):
    c, ts = p["c"], p["t_raiz"]
    g = lambda t: c * (t - ts) ** 2
    dg = lambda t: 2 * c * (t - ts)
    area = c * ts ** 3 / 3
    res = [raices.biseccion(g, 0.0, 2 * ts, x_ref=ts), raices.newton(g, dg, p["x0_newton"], x_ref=ts),
           raices.newton(g, dg, p["x0_newton"], x_ref=ts, m=2), raices.secante(g, p["x0_newton"], p["x0_newton"] - 1, x_ref=ts)]
    tablas = [_tabla_raices(res, ts)]
    g_fun = lambda t: c * (np.asarray(t) - ts) ** 2
    filas = [[n, h, t_, e_t, s, e_s] for n, h, t_, e_t, s, e_s in integ.tabla_refinamiento(g_fun, 0.0, ts, [2, 4, 8, 16], area)]
    _reg_refinamiento(g_fun, 0.0, ts, [2, 4, 8, 16], area)
    val, R_ = integ.romberg(g_fun, 0.0, ts, 3)
    _reg_romberg(R_, area)
    filas.append(["Romberg (3 niveles)", None, val, abs(val - area), None, None])
    tablas.append(_tabla("Distancia = integral de v(t) (v cuadrática): trapecio, Simpson y Romberg",
                         ["n", "h", "Trapecio", "Error", "Simpson 1/3", "Error"], filas))
    newt = res[1]
    n_max = max(len(r.historial) for r in res[1:])
    serie = lambda r: [(h[3] if h[3] and h[3] > 0 else 1e-17) for h in r.historial] + [None] * (n_max - len(r.historial))
    graficos = [{"titulo": "Error vs iteración en la raíz doble t = 10", "escala": "semilogy", "xlabel": "iteración",
                 "x": list(range(1, n_max + 1)),
                 "series": {"Newton-Raphson": serie(res[1]), "Newton modificado (m=2)": serie(res[2]),
                            "Secante": serie(res[3])}},
                {"titulo": "v(t) = 0.05 (t-10)^2", "x": [float(u) for u in np.linspace(0, 20, 200)], "xlabel": "t (s)",
                 "series": {"v(t)": [float(u) for u in g_fun(np.linspace(0, 20, 200))]}}]
    ref = {"raiz": ts, "multiplicidad": 2, "distancia": area,
           "orden_newton_observado": raices.orden_convergencia(newt.historial)}
    return {"modulo": 1, "escenario": "MAL_CONDICIONADO", "parametros": p, "referencia": ref,
            "tablas": tablas, "graficos": graficos}


# ---------------------------------------------------------------- Módulo 2
def _raiz_cuadratica(D0, al, be, umbral):
    return (-al + math.sqrt(al ** 2 + 4 * be * (umbral - D0))) / (2 * be)


def _lineales(escenario):
    datos = json.loads(RUTA_SISTEMAS.read_text(encoding="utf-8"))
    A = np.array(datos["normal"]["A"], float); x_ref = np.array(datos["normal"]["x_ref"], float)
    if escenario == "NORMAL":
        b, M = A @ x_ref, A
    elif escenario == "ESTRES":
        b, M = np.array(datos["estres"]["b"], float), A
        x_ref = np.linalg.solve(M, b)
    else:
        M = np.array(datos["mal_condicionado"]["A"], float); b = M @ x_ref
    res = resolver_todos(M, b, x_ref, tol=1e-8)
    for r in res:
        _registrar(r.metodo, [_fila_it(h[0], h[1], h[2], h[3], np.linalg.norm(x_ref)) for h in r.historial],
                   r.convergio, tolerancia=1e-8, max_iter=100000, referencia="solución exacta x* conocida")
    filas = [[r.metodo, r.iteraciones, r.convergio, r.residuo, r.historial[-1][3]] for r in res]
    info = {"spd": es_spd(M), "kappa2": float(np.linalg.cond(M)),
            "rho_jacobi": radio_espectral(M, "jacobi"), "rho_gs": radio_espectral(M, "gauss_seidel")}
    tablas = [_tabla("Sistema lineal de calibración 4x4 (tolerancia 1e-8)",
                     ["Método", "Iteraciones", "Convergió", "Residuo (norma inf.)", "Error (norma inf.)"], filas)]
    if escenario == "ESTRES":
        s = sensibilidad(M, A @ np.array(datos["normal"]["x_ref"], float), b - A @ np.array(datos["normal"]["x_ref"], float))
        info["sensibilidad"] = s
    if escenario == "MAL_CONDICIONADO":
        info["sensibilidad"] = sensibilidad(M, b, np.array(datos["mal_condicionado"]["delta_b"], float))
    return tablas, info


def modulo2(escenario, p=None):
    p = _param(2, escenario, p)
    tablas, graficos = [], []
    if escenario == "MAL_CONDICIONADO":
        Dm, be, tm, u, du = p["D_min"], p["beta"], p["t_min"], p["umbral"], p["delta_umbral"]
        D = lambda t: Dm + be * (t - tm) ** 2
        f = lambda t: D(t) - u
        df = lambda t: 2 * be * (t - tm)
        res = [raices.biseccion(f, 0.0, 2 * tm, x_ref=tm), raices.newton(f, df, 25.0, x_ref=tm),
               raices.newton(f, df, 25.0, x_ref=tm, m=2), raices.secante(f, 25.0, 24.0, x_ref=tm)]
        tablas.append(_tabla_raices(res, tm))
        # umbral levemente mayor: la raíz doble se separa en dos
        u2 = u + du
        f2 = lambda t: D(t) - u2
        r1 = tm - math.sqrt((u2 - Dm) / be); r2 = tm + math.sqrt((u2 - Dm) / be)
        b1 = raices.biseccion(f2, tm - 5, tm, x_ref=r1); b2 = raices.biseccion(f2, tm, tm + 5, x_ref=r2)
        tablas.append(_tabla("Sensibilidad: umbral 0.20 -> 0.2001 separa la raíz doble",
                             ["Raíz", "Valor", "Bisección (iteraciones)", "Desplazamiento respecto de t=20"],
                             [["t1", b1.raiz, b1.iteraciones, b1.raiz - tm], ["t2", b2.raiz, b2.iteraciones, b2.raiz - tm]]))
        ref = {"raiz_doble": tm, "raices_umbral_perturbado": [r1, r2], "desplazamiento": (r2 - r1) / 2,
               "amplificacion_dt_du": (r2 - tm) / du}
        tt = np.linspace(0, 40, 200)
        graficos.append({"titulo": "D(t) con umbral (raíz doble)", "x": [float(v) for v in tt], "xlabel": "t (meses)",
                         "series": {"D(t)": [float(v) for v in D(tt)], "umbral": [u] * len(tt)}})
    else:
        D0, al, be, u = p["D0"], p["alpha"], p["beta"], p["umbral"]
        D = lambda t: D0 + al * t + be * t ** 2
        f = lambda t: D(t) - u
        df = lambda t: al + 2 * be * t
        t_ref = _raiz_cuadratica(D0, al, be, u)
        res = [raices.biseccion(f, 0.0, 100.0, x_ref=t_ref), raices.newton(f, df, 40.0, x_ref=t_ref),
               raices.secante(f, 0.0, 10.0, x_ref=t_ref)]
        tablas.append(_tabla_raices(res, t_ref))
        sens = -t_ref / (al + 2 * be * t_ref)
        t_pert = _raiz_cuadratica(D0, al + 0.001, be, u)
        tablas.append(_tabla("Sensibilidad del tiempo al umbral respecto de alfa",
                             ["dt*/dalpha (analítica)", "Cambio de t* con alfa + 0.001", "Aproximación lineal"],
                             [[sens, t_pert - t_ref, 0.001 * sens]]))
        t_base = _raiz_cuadratica(*(PARAMETROS[2]["NORMAL"][k] for k in ("D0", "alpha", "beta", "umbral")))
        ref = {"t_umbral": t_ref, "t_umbral_normal": t_base, "adelanto_respecto_normal": t_base - t_ref, "dt_dalpha": sens}
        tt = np.linspace(0, 30, 200)
        graficos.append({"titulo": "Indicador de deterioro D(t) y umbral", "x": [float(v) for v in tt], "xlabel": "t (meses)",
                         "series": {"D(t)": [float(v) for v in D(tt)], "umbral": [u] * len(tt)}})
    graficos.append({"titulo": "Error de cada método vs iteración", "escala": "semilogy", "xlabel": "iteración",
                     "x": list(range(1, max(len(r.historial) for r in res) + 1)),
                     "series": {r.metodo: [(h[3] if h[3] and h[3] > 0 else 1e-17) for h in r.historial]
                                + [None] * (max(len(q.historial) for q in res) - len(r.historial)) for r in res}})
    lin, info = _lineales(escenario)
    tablas += lin
    ref["sistema_lineal"] = info
    return {"modulo": 2, "escenario": escenario, "parametros": p, "referencia": ref, "tablas": tablas, "graficos": graficos}


# ---------------------------------------------------------------- Módulo 3
def _oscilador(m, c, k, F):
    return lambda t, y: np.array([y[1], (F(t) - c * y[1] - k * y[0]) / m])


def _libre(m, c, k, x0, v0):
    w0 = math.sqrt(k / m); z = c / (2 * math.sqrt(k * m)); wd = w0 * math.sqrt(1 - z ** 2)
    C1 = x0; C2 = (v0 + z * w0 * x0) / wd
    return lambda t: np.exp(-z * w0 * np.asarray(t)) * (C1 * np.cos(wd * np.asarray(t)) + C2 * np.sin(wd * np.asarray(t))), \
        {"omega0": w0, "zeta": z, "omega_d": wd, "C1": C1, "C2": C2}


def _simpson_ref(fun, a, b, n=200000):
    return integ.simpson13(fun, a, b, n)


def modulo3(escenario, p=None):
    p = _param(3, escenario, p)
    if escenario == "NORMAL":
        return _m3_normal(p)
    if escenario == "ESTRES":
        return _m3_estres(p)
    return _m3_mal(p)


def _barrido(f, y0, T, x_ref_fun, hs):
    filas, errs = [], {"RK2": [], "RK4": []}
    for m in ("RK2", "RK4"):
        e = []
        for h in hs:
            n = round(T / h)
            t, Y = edo.integrar(m, f, 0.0, y0, T / n, n)
            _reg_edo(f"{m} (h = {h} s)", T / n, t, Y, ref=x_ref_fun(t))
            e.append(float(np.max(np.abs(Y[:, 0] - x_ref_fun(t)))))
        errs[m] = e
        filas += [[m, h, ee, o] for h, ee, o in zip(hs, e, [None] + edo.orden_observado(hs, e))]
    return filas, errs


def _m3_normal(p):
    m, c, k, x0, v0, T, h = (p[q] for q in ("m", "c", "k", "x0", "v0", "T", "h"))
    xr, par = _libre(m, c, k, x0, v0)
    f = _oscilador(m, c, k, lambda t: 0.0)
    hs = [0.4, 0.2, 0.1, 0.05, 0.025]
    filas, errs = _barrido(f, [x0, v0], T, xr, hs)
    tablas = [_tabla("Error máximo |x_RK - x_analítica| y orden observado",
                     ["Método", "h (s)", "Error máx. de x", "Orden p"], filas)]
    n = round(T / h)
    sol = {mm: edo.integrar(mm, f, 0.0, [x0, v0], T / n, n) for mm in ("RK2", "RK4")}
    t = sol["RK4"][0]
    I_ref = _simpson_ref(lambda s: xr(s) ** 2, 0.0, T)
    filas = [["Amplitud máxima |x|", float(np.max(np.abs(xr(t)))), float(np.max(np.abs(sol['RK2'][1][:, 0]))),
              float(np.max(np.abs(sol['RK4'][1][:, 0])))],
             ["Integral de x(t)^2 (Simpson)", I_ref, integ.simpson_datos(sol['RK2'][1][:, 0] ** 2, T / n),
              integ.simpson_datos(sol['RK4'][1][:, 0] ** 2, T / n)],
             ["Integral de x(t)^2 (trapecio)", I_ref, integ.trapecio_datos(sol['RK2'][1][:, 0] ** 2, T / n),
              integ.trapecio_datos(sol['RK4'][1][:, 0] ** 2, T / n)]]
    tablas.append(_tabla(f"Magnitudes con h = {h} s", ["Magnitud", "Analítica / referencia", "RK2", "RK4"], filas))
    val, R = integ.romberg(lambda s: xr(s) ** 2, 0.0, T, 8)
    _reg_romberg(R, I_ref)
    tablas.append(_tabla("Romberg sobre x(t)^2 analítica", ["Nivel i", "R[i][0] (trapecio)", "R[i][i]", "Error vs referencia"],
                         [[i, R[i, 0], R[i, i], abs(R[i, i] - I_ref)] for i in range(8)]))
    graficos = [{"titulo": "Oscilación libre subamortiguada", "x": _resumir(t, t)[0], "xlabel": "t (s)",
                 "series": {"analítica": _resumir(t, xr(t))[1], "RK2": _resumir(t, sol['RK2'][1][:, 0])[1],
                            "RK4": _resumir(t, sol['RK4'][1][:, 0])[1]}},
                {"titulo": "Error máximo vs paso", "x": hs, "escala": "loglog", "xlabel": "h (s)", "series": errs}]
    return {"modulo": 3, "escenario": "NORMAL", "parametros": p,
            "referencia": {**par, "integral_x2": I_ref}, "tablas": tablas, "graficos": graficos}


def _m3_estres(p):
    m, c, k, F0, w, T = (p[q] for q in ("m", "c", "k", "F0", "w", "T"))
    F = lambda t: F0 * math.sin(w * t)
    f = _oscilador(m, c, k, F)
    h_ref = 1e-3
    n_ref = round(T / h_ref)
    t_ref, Y_ref = edo.integrar("RK4", f, 0.0, [p["x0"], p["v0"]], T / n_ref, n_ref)
    _, Y_chk = edo.integrar("RK4", f, 0.0, [p["x0"], p["v0"]], T / (n_ref // 2), n_ref // 2)
    chequeo = float(np.max(np.abs(Y_chk[:, 0] - Y_ref[::2, 0])))
    A_est = F0 / (c * w)
    filas, tr, tr_graf = [], {}, None
    for h in p["pasos"]:
        n = round(T / h)
        paso = n_ref // n
        for mm in ("RK2", "RK4"):
            t, Y = edo.integrar(mm, f, 0.0, [p["x0"], p["v0"]], T / n, n)
            _reg_edo(f"{mm} forzado (h = {h} s)", T / n, t, Y, ref=Y_ref[::paso, 0])
            err = float(np.max(np.abs(Y[:, 0] - Y_ref[::paso, 0])))
            cola = Y[t > T - 10, 0]
            filas.append([mm, h, err, float(np.max(np.abs(Y[:, 0]))), float(np.max(np.abs(cola))),
                          integ.simpson_datos(Y[:, 0] ** 2, T / n)])
            tr[(mm, h)] = (t, Y)
    I_ref = integ.simpson_datos(Y_ref[:, 0] ** 2, T / n_ref)
    tablas = [_tabla(f"Respuesta forzada F(t) = {F0} sen({w} t): comparación RK2 / RK4 (referencia: RK4 con h = 0.001 s)",
                     ["Método", "h (s)", "Error máx. de x", "Amplitud máx.", "Amplitud en los últimos 10 s",
                      "Integral de x^2 (Simpson)"], filas),
              _tabla("Referencias", ["Cantidad", "Valor"],
                     [["Amplitud estacionaria teórica F0/(c w)", A_est], ["Integral de x^2 (referencia)", I_ref],
                      ["Chequeo de la referencia (h vs 2h, error máx.)", chequeo]])]
    h0 = p["pasos"][0]
    graficos = [{"titulo": "Oscilación forzada en resonancia", "x": _resumir(tr[("RK4", h0)][0], tr[("RK4", h0)][0])[0],
                 "xlabel": "t (s)",
                 "series": {"referencia": _resumir(t_ref, Y_ref[:, 0], 400)[1][:len(_resumir(tr[("RK4", h0)][0], tr[("RK4", h0)][0])[0])],
                            **{f"{mm} h={h0}": _resumir(tr[(mm, h0)][0], tr[(mm, h0)][1][:, 0])[1] for mm in ("RK2", "RK4")}}},
                {"titulo": "Error máximo por método y paso", "x": [str(h) for h in p["pasos"]], "xlabel": "h (s)",
                 "series": {mm: [r[2] for r in filas if r[0] == mm] for mm in ("RK2", "RK4")}}]
    return {"modulo": 3, "escenario": "ESTRES", "parametros": p,
            "referencia": {"amplitud_estacionaria": A_est, "integral_x2": I_ref, "chequeo_referencia": chequeo},
            "tablas": tablas, "graficos": graficos}


def _m3_mal(p):
    m, k, x0, v0, T, h = (p[q] for q in ("m", "k", "x0", "v0", "T", "h"))
    w0 = math.sqrt(k / m)
    filas, graficos, ref = [], [], {}
    n = round(T / h)
    for c in p["amortiguamientos"]:
        z = c / (2 * math.sqrt(k * m))
        f = _oscilador(m, c, k, lambda t: 0.0)
        t, Y = edo.integrar("RK4", f, 0.0, [x0, v0], T / n, n)
        if z < 1:
            xr, par = _libre(m, c, k, x0, v0)
            kappa = z ** 2 / (1 - z ** 2)
            err = float(np.max(np.abs(Y[:, 0] - xr(t))))
            _reg_edo(f"RK4 (c = {c})", T / n, t, Y, ref=xr(t))
            filas.append([c, z, par["omega_d"], par["C1"], par["C2"], kappa, err, "Fórmula subamortiguada aplicable"])
            graficos.append({"titulo": f"Oscilación casi crítica (c = {c})", "x": _resumir(t, t)[0], "xlabel": "t (s)",
                             "series": {"analítica": _resumir(t, xr(t))[1], "RK4": _resumir(t, Y[:, 0])[1]}})
            ref[f"c={c}"] = par
        else:
            crit = lambda s: np.exp(-w0 * s) * (x0 + (v0 + w0 * x0) * s)
            err = float(np.max(np.abs(Y[:, 0] - crit(t))))
            _reg_edo(f"RK4 (c = {c}, crítico)", T / n, t, Y, ref=crit(t))
            filas.append([c, z, 0.0, x0, None, float("inf"), err,
                          "wd = 0: la fórmula subamortiguada divide por cero; se usa x = (C1 + C2 t) e^(-w0 t)"])
            ref[f"c={c}"] = {"zeta": z, "omega_d": 0.0}
    zs = [0.5, 0.9, 0.99, 0.999, 0.9999]
    graficos.append({"titulo": "Constante C2 = (v0 + zeta w0 x0)/omega_d al acercarse al amortiguamiento crítico",
                     "x": zs, "xlabel": "zeta", "escala": "semilogy",
                     "series": {"C2": [(0.0 + z_ * w0 * x0) / (w0 * math.sqrt(1 - z_ ** 2)) for z_ in zs]}})
    tablas = [_tabla("Amortiguamiento casi crítico: sensibilidad de la fórmula analítica",
                     ["c (N s/m)", "zeta", "omega_d (rad/s)", "C1", "C2", "zeta^2/(1-zeta^2)", "Error máx. RK4", "Observación"], filas)]
    return {"modulo": 3, "escenario": "MAL_CONDICIONADO", "parametros": p, "referencia": ref,
            "tablas": tablas, "graficos": graficos}


# ---------------------------------------------------------------- Módulo 4
def _reg_interp(etiqueta, fun, ocultos):
    for nombre, fn in fun.items():
        pred = fn(ocultos)
        its = [_fila_it(i + 1, [o, v], None, abs(v - math.sin(o)), math.sin(o))
               for i, (o, v) in enumerate(zip(ocultos, pred))]
        _registrar(f"{nombre}{etiqueta}", its, referencia="valor real sen(t) en los puntos ocultos")


def _interpolantes(xn, yn):
    P = interp.lagrange(xn, yn)
    Q, coef, tabla = interp.newton_dd(xn, yn)
    S = interp.spline_natural(xn, yn)
    return {"Lagrange": P, "Newton": Q, "Spline cúbico": S}, coef, tabla


def _datos(n, sigma, semilla):
    xn = np.linspace(0.0, 2 * np.pi, n)
    yn = np.sin(xn)
    if sigma:
        yn = yn + np.random.default_rng(semilla).normal(0.0, sigma, n)
    return xn, yn


def modulo4(escenario, p=None):
    p = _param(4, escenario, p)
    ocultos = np.array(p["ocultos"], float)
    tt = np.linspace(0.0, 2 * np.pi, 300)
    tablas, graficos, ref = [], [], {}
    if escenario == "ESTRES":
        filas = []
        for n in p["n_nodos"]:
            for etiqueta, sig in (("sin ruido", 0.0), (f"ruido sigma={p['sigma']}", p["sigma"])):
                xn, yn = _datos(n, sig, p["semilla"])
                fun, _, _ = _interpolantes(xn, yn)
                _reg_interp(f" ({n} nodos, {etiqueta})", fun, ocultos)
                for nombre, fn in fun.items():
                    e = np.abs(fn(ocultos) - np.sin(ocultos))
                    filas.append([n, etiqueta, nombre, *[float(v) for v in e], float(e.max())])
        tablas.append(_tabla("Error en los puntos ocultos según número de nodos y ruido",
                             ["Nodos", "Datos", "Método"] + [f"t = {o}" for o in ocultos] + ["Máximo"], filas))
        xn, yn = _datos(9, p["sigma"], p["semilla"])
        fun, _, _ = _interpolantes(xn, yn)
        graficos.append({"titulo": "Reconstrucción con ruido (9 nodos)", "x": [float(v) for v in tt], "xlabel": "t",
                         "series": {"sen t": [float(v) for v in np.sin(tt)],
                                    **{n_: [float(v) for v in f_(tt)] for n_, f_ in fun.items()}},
                         "nodos": {"x": [float(v) for v in xn], "y": [float(v) for v in yn]}})
        graficos.append({"titulo": "Error máximo en puntos ocultos vs número de nodos (con ruido)", "escala": "semilogy",
                         "x": [str(n) for n in p["n_nodos"]], "xlabel": "nodos",
                         "series": {nm: [max(f_[6] for f_ in filas if f_[0] == n and f_[2] == nm and "ruido" in f_[1])
                                         for n in p["n_nodos"]] for nm in ("Lagrange", "Newton", "Spline cúbico")}})
        ref = {"funcion": "sin(t)", "semilla": p["semilla"]}
    else:
        xn, yn = _datos(p["n_nodos"], p["sigma"], p["semilla"])
        fun, coef, tabla = _interpolantes(xn, yn)
        _reg_interp("", fun, ocultos)
        errs = {n_: np.abs(f_(ocultos) - np.sin(ocultos)) for n_, f_ in fun.items()}
        tablas.append(_tabla("Error en los puntos ocultos (valor real = sen t)",
                             ["Método"] + [f"t = {o}" for o in ocultos] + ["Máximo"],
                             [[n_, *[float(v) for v in e], float(e.max())] for n_, e in errs.items()]))
        graficos.append({"titulo": "Curvas interpoladas y función real", "x": [float(v) for v in tt], "xlabel": "t",
                         "series": {"sen t": [float(v) for v in np.sin(tt)],
                                    **{n_: [float(v) for v in f_(tt)] for n_, f_ in fun.items()}},
                         "nodos": {"x": [float(v) for v in xn], "y": [float(v) for v in yn]}})
        graficos.append({"titulo": "Error de reconstrucción |S(t) - sen t|", "x": [float(v) for v in tt], "xlabel": "t",
                         "escala": "semilogy",
                         "series": {n_: [float(max(v, 1e-17)) for v in np.abs(f_(tt) - np.sin(tt))] for n_, f_ in fun.items()}})
        ref = {"funcion": "sin(t)", "n_nodos": p["n_nodos"], "sigma": p["sigma"]}
        if escenario == "NORMAL":
            u = 0.5
            g = {n_: raices.biseccion(lambda s, f_=f_: float(f_(s)) - u, 0.0, math.pi / 2, x_ref=math.asin(u)) for n_, f_ in fun.items()}
            tablas.append(_tabla("Cruce del umbral y = 0.5 por bisección (valor real = asin(0.5))",
                                 ["Curva", "t estimado", "Iteraciones", "Error abs."],
                                 [[n_, r.raiz, r.iteraciones, abs(r.raiz - math.asin(u))] for n_, r in g.items()]))
            tablas.append(_tabla("Diferencias divididas de Newton (coeficientes)", ["k", "f[x0..xk]"],
                                 [[i, float(c_)] for i, c_ in enumerate(coef)]))
        else:
            V = np.vander(xn)
            cheb = np.cos(np.pi * (2 * np.arange(p["n_nodos"]) + 1) / (2 * p["n_nodos"]))
            cheb = np.pi * (cheb[::-1] + 1)
            fc = interp.lagrange(cheb, np.sin(cheb))
            e_cheb = np.abs(fc(ocultos) - np.sin(ocultos))
            tablas.append(_tabla("Evidencia de mal condicionamiento", ["Cantidad", "Valor"], [
                ["kappa(Vandermonde) con 20 nodos equiespaciados", float(np.linalg.cond(V))],
                ["kappa(Vandermonde) con 9 nodos equiespaciados", float(np.linalg.cond(np.vander(np.linspace(0, 2 * np.pi, 9))))],
                ["Constante de Lebesgue, 20 nodos equiespaciados", interp.constante_lebesgue(xn)],
                ["Constante de Lebesgue, 20 nodos de Chebyshev", interp.constante_lebesgue(cheb)],
                ["Error máx. Lagrange con nodos de Chebyshev (sin ruido)", float(e_cheb.max())]]))
    return {"modulo": 4, "escenario": escenario, "parametros": p, "referencia": ref, "tablas": tablas, "graficos": graficos}


modulo1, modulo2, modulo3, modulo4 = (_con_registro(m) for m in (modulo1, modulo2, modulo3, modulo4))
MODULOS = {1: modulo1, 2: modulo2, 3: modulo3, 4: modulo4}


def ejecutar(modulo, escenario, parametros=None):
    """Punto de entrada único: ejecuta un módulo en un escenario con parámetros opcionales."""
    return MODULOS[modulo](escenario, parametros)


def serializable(obj):
    """Convierte el resultado en datos JSON estándar (NaN/inf -> None o texto, numpy -> Python)."""
    if isinstance(obj, dict):
        return {str(k): serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serializable(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        if math.isnan(v):
            return None
        return "inf" if v == math.inf else "-inf" if v == -math.inf else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj
