"""Módulo 1 — Detención de emergencia de cabinas (EDO + integración + raíces)."""
import math
import time

import numpy as np

from .. import edo, integracion, raices
from .comun import (ejecucion, err_rel, fila, fmt, grafico, lista, log_seguro, serie, tabla)

NOMBRE = "Detención de emergencia"
PREGUNTA = "¿Cómo varían el tiempo y la distancia de detención al cambiar velocidad, tiempo de reacción y desaceleración?"
MODELO = ("dx/dt = v ; dv/dt = −(a₀ + c·v).  Con c = 0: desaceleración constante, v(t) = v₀ − a₀t y d_f = v₀²/(2a₀). "
          "Con c > 0 (desaceleración variable, ampliación de la consigna): v(t) = (v₀ + a₀/c)e^(−ct) − a₀/c. "
          "d_total = v₀·t_r + d_f (distancia recorrida durante el tiempo de reacción más la de frenado).")
METODOS = ["Bisección", "Newton-Raphson", "Secante", "RK2 (Heun)", "RK4", "Trapecio", "Simpson 1/3", "Romberg"]

ESPEC = {
    "v0": {"label": "Velocidad inicial v₀", "unidad": "m/s", "min": 0.5, "max": 30, "fuente": "Sintético"},
    "a0": {"label": "Desaceleración base a₀", "unidad": "m/s²", "min": 0.05, "max": 5, "fuente": "Sintético"},
    "c": {"label": "Coef. dependiente de la velocidad c", "unidad": "1/s", "min": 0, "max": 1, "fuente": "Sintético (ampliación)"},
    "t_r": {"label": "Tiempo de reacción t_r", "unidad": "s", "min": 0, "max": 10, "fuente": "Supuesto didáctico"},
    "d_disp": {"label": "Distancia disponible", "unidad": "m", "min": 5, "max": 500, "fuente": "Supuesto didáctico"},
    "h": {"label": "Paso RK (h)", "unidad": "s", "min": 0.01, "max": 5, "fuente": "Configuración numérica"},
    "tol": {"label": "Tolerancia de raíces", "unidad": "—", "min": 1e-13, "max": 1e-3, "fuente": "Configuración numérica"},
    "t_raiz": {"label": "Raíz doble t*", "unidad": "s", "min": 1, "max": 100, "fuente": "Sintético"},
    "t0": {"label": "Semilla inicial t₀", "unidad": "s", "min": 0, "max": 200, "fuente": "Configuración numérica"},
    "eps": {"label": "Perturbación ε de f", "unidad": "—", "min": 1e-14, "max": 1e-3, "fuente": "Sintético"},
}
DEFAULTS = {
    "NORMAL": {"v0": 5.0, "a0": 0.5, "c": 0.0, "t_r": 1.5, "d_disp": 60.0, "h": 0.5, "tol": 1e-10},
    "ESTRES": {"v0": 8.0, "a0": 0.4, "c": 0.05, "t_r": 1.5, "d_disp": 60.0, "h": 1.0, "tol": 1e-10},
    "MAL_CONDICIONADO": {"t_raiz": 10.0, "t0": 5.0, "eps": 1e-10, "tol": 1e-10},
}


def _filas_raiz(r, ref):
    fl = []
    for h in r["historial"]:
        ap = {k: h[k] for k in ("a", "b", "x", "fx", "paso") if k in h}
        fl.append(fila(h["k"], ap, abs(h["fx"]), h["err"], None if ref == 0 else (h["err"] or 0) / abs(ref)))
    return fl


def _ej_raiz(r, tol, ref, texto, t_ms):
    return ejecucion(r["metodo"], "Raíces", _filas_raiz(r, ref), tolerancia=tol, max_iter=len(r["historial"]),
                     convergio=r["convergio"], tiempo_ms=t_ms, referencia=f"t_det analítico = {ref:.10g} s",
                     valor=r["raiz"], metricas={"raiz": r["raiz"], "error_abs": abs(r["raiz"] - ref),
                                                "residuo": r["residuo"], "iteraciones": r["iteraciones"]},
                     interpretacion=texto, mensaje=r.get("mensaje"))


def ejecutar(escenario, p):
    return _ejecutar_normal_estres(escenario, p) if escenario in ("NORMAL", "ESTRES") else _ejecutar_mal(p)


def _ejecutar_normal_estres(escenario, p):
    v0, a0, c, t_r, d_disp, h, tol = (p[k] for k in ("v0", "a0", "c", "t_r", "d_disp", "h", "tol"))
    if c == 0:
        v_an = lambda t: v0 - a0 * np.asarray(t, float)
        x_an = lambda t: v0 * np.asarray(t, float) - a0 * np.asarray(t, float) ** 2 / 2
        T_ref = v0 / a0
        dv = lambda t: -a0
    else:
        K = v0 + a0 / c
        v_an = lambda t: K * np.exp(-c * np.asarray(t, float)) - a0 / c
        x_an = lambda t: K * (1 - np.exp(-c * np.asarray(t, float))) / c - a0 * np.asarray(t, float) / c
        T_ref = math.log(1 + c * v0 / a0) / c
        dv = lambda t: -c * K * math.exp(-c * t)
    d_f_ref = float(x_an(T_ref))
    d_tot_ref = v0 * t_r + d_f_ref

    # ---- Raíces: instante en que v(t) = 0 ----------------------------------------------------------------
    f = lambda t: float(v_an(t))
    t0 = time.perf_counter(); rb = raices.biseccion(f, 0, 3 * v0 / a0, tol, raiz_ref=T_ref); tb = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter(); rn = raices.newton(f, dv, v0 / (2 * a0), tol, raiz_ref=T_ref); tn = (time.perf_counter() - t0) * 1e3
    t0 = time.perf_counter(); rs = raices.secante(f, 0, v0 / (2 * a0), tol, raiz_ref=T_ref); ts = (time.perf_counter() - t0) * 1e3
    ej = [_ej_raiz(rb, tol, T_ref, "Reduce el intervalo a la mitad en cada paso: orden 1, siempre converge con cambio de signo.", tb),
          _ej_raiz(rn, tol, T_ref, "Orden 2 en raíz simple; con v(t) lineal converge en un solo paso.", tn),
          _ej_raiz(rs, tol, T_ref, "Orden ≈ 1.618 sin necesitar derivada.", ts)]
    T = rn["raiz"]

    # ---- EDO: RK2 y RK4 sobre [x, v] en [0, T] -----------------------------------------------------------------
    n = max(1, math.ceil(T / h)); h_ef = T / n
    fode = lambda t, y: np.array([y[1], -(a0 + c * y[1])])
    graf_t, tabs_edo = {}, {}
    for nombre, fun, kw in (("RK2 (Heun)", edo.rk2, {"variante": "heun"}), ("RK4", edo.rk4, {})):
        t0 = time.perf_counter(); tt, yy = fun(fode, 0.0, [0.0, v0], h_ef, n, **kw); tm = (time.perf_counter() - t0) * 1e3
        ex, ev = np.abs(yy[:, 0] - x_an(tt)), np.abs(yy[:, 1] - v_an(tt))
        graf_t[nombre] = (tt, yy, ex)
        filas = [fila(i, {"t": float(tt[i]), "x": float(yy[i, 0]), "v": float(yy[i, 1]), "x_ref": float(x_an(tt[i])),
                          "v_ref": float(v_an(tt[i]))}, None, ex[i], err_rel(x_an(tt[i]), yy[i, 0])) for i in range(len(tt))]
        ej.append(ejecucion(nombre, "EDO", filas, paso=h_ef, max_iter=n, tiempo_ms=tm,
                            referencia="Solución analítica x(t), v(t)", valor={"x_T": float(yy[-1, 0]), "v_T": float(yy[-1, 1])},
                            metricas={"x_T": yy[-1, 0], "v_T": yy[-1, 1], "d_f_ref": d_f_ref, "err_x_max": ex.max(),
                                      "err_v_max": ev.max(), "err_dist_frenado": abs(yy[-1, 0] - d_f_ref),
                                      "d_total": v0 * t_r + yy[-1, 0], "h": h_ef},
                            interpretacion=("Orden global 2 (variante de Heun)." if "RK2" in nombre else "Orden global 4.")))
    # estudio de orden: h, h/2, h/4, h/8
    hs, e2, e4 = [], [], []
    for k in range(4):
        nk = n * 2 ** k; hk = T / nk
        hs.append(hk)
        _, y2 = edo.rk2(fode, 0.0, [0.0, v0], hk, nk); _, y4 = edo.rk4(fode, 0.0, [0.0, v0], hk, nk)
        e2.append(abs(y2[-1, 0] - d_f_ref)); e4.append(abs(y4[-1, 0] - d_f_ref))
    p2, p4 = edo.orden_empirico(e2, hs), edo.orden_empirico(e4, hs)
    tab_orden = tabla("Estudio de refinamiento del paso (error en x(T) frente a d_f analítico)",
                      ["h (s)", "Error RK2", "Orden RK2", "Error RK4", "Orden RK4"],
                      [[hs[i], e2[i], None if i == 0 else p2[i - 1], e4[i], None if i == 0 else p4[i - 1]] for i in range(4)],
                      "Orden ≈ log₂(e(h)/e(h/2)). Si el error es del orden del redondeo (≈10⁻¹⁵) el orden no es informativo: "
                      "con a constante la solución es un polinomio de grado ≤ 2 y RK2/RK4 la integran exactamente." )

    # ---- Integración de v(t) en [0, T] --------------------------------------------------------------------------
    refin = integracion.tabla_refinamiento(lambda t: v_an(t), 0.0, T, d_f_ref, niveles=(1, 2, 3, 4, 5, 6, 7, 8))
    for nombre, kv, ke in (("Trapecio", "trapecio", "e_trap"), ("Simpson 1/3", "simpson", "e_simp"), ("Romberg", "romberg", "e_romb")):
        filas = [fila(i + 1, {"n": r["n"], "h": r["h"], "integral": r[kv]}, None, r[ke], err_rel(d_f_ref, r[kv])) for i, r in enumerate(refin)]
        ej.append(ejecucion(nombre, "Integración", filas, paso=refin[-1]["h"], max_iter=refin[-1]["n"],
                            referencia=f"d_f analítico = {d_f_ref:.10g} m", valor=refin[-1][kv],
                            metricas={"integral": refin[-1][kv], "error_abs": refin[-1][ke], "n": refin[-1]["n"]},
                            interpretacion={"Trapecio": "Error O(h²): se divide ≈ 4 al duplicar n.",
                                            "Simpson 1/3": "Error O(h⁴): se divide ≈ 16 al duplicar n.",
                                            "Romberg": "Extrapolación de Richardson sobre el trapecio."}[nombre]))
    tab_refin = tabla("Refinamiento de la integral de v(t): distancia de frenado",
                      ["n", "h (s)", "Trapecio", "Error", "Simpson 1/3", "Error", "Romberg", "Error"],
                      [[r["n"], r["h"], r["trapecio"], r["e_trap"], r["simpson"], r["e_simp"], r["romberg"], r["e_romb"]] for r in refin],
                      f"Referencia analítica d_f = {d_f_ref:.8g} m.")

    # ---- Resultados físicos --------------------------------------------------------------------------------------
    d_total = v0 * t_r + float(graf_t["RK4"][1][-1, 0])
    margen = d_disp - d_total
    tab_fis = tabla("Resultados físicos del modelo", ["Magnitud", "Analítico", "Numérico (RK4)", "Unidad"],
                    [["Tiempo de detención t_det", T_ref, T, "s"], ["Distancia de frenado d_f", d_f_ref, float(graf_t["RK4"][1][-1, 0]), "m"],
                     ["Distancia durante reacción v₀·t_r", v0 * t_r, v0 * t_r, "m"], ["Distancia total d_total", d_tot_ref, d_total, "m"],
                     ["Distancia disponible (supuesto)", d_disp, d_disp, "m"], ["Margen = disponible − total", d_disp - d_tot_ref, margen, "m"]])
    g = [
        grafico("v", "Velocidad v(t)", "t (s)", "v (m/s)",
                [serie("Analítica", np.linspace(0, T, 300), v_an(np.linspace(0, T, 300))),
                 serie("RK4", graf_t["RK4"][0], graf_t["RK4"][1][:, 1]), serie("RK2 (Heun)", graf_t["RK2 (Heun)"][0], graf_t["RK2 (Heun)"][1][:, 1])]),
        grafico("x", "Posición x(t) durante el frenado", "t (s)", "x (m)",
                [serie("Analítica", np.linspace(0, T, 300), x_an(np.linspace(0, T, 300))),
                 serie("RK4", graf_t["RK4"][0], graf_t["RK4"][1][:, 0]), serie("RK2 (Heun)", graf_t["RK2 (Heun)"][0], graf_t["RK2 (Heun)"][1][:, 0])]),
        grafico("err_t", "Error global |x_RK − x_ref| (log)", "t (s)", "error (m)",
                [serie(k, v[0], [log_seguro(e) for e in v[2]]) for k, v in graf_t.items()], logy=True),
        grafico("refin", "Error de integración vs n (log-log)", "n subintervalos", "error en d_f (m)",
                [serie("Trapecio", [r["n"] for r in refin], [log_seguro(r["e_trap"]) for r in refin]),
                 serie("Simpson 1/3", [r["n"] for r in refin], [log_seguro(r["e_simp"]) for r in refin]),
                 serie("Romberg", [r["n"] for r in refin], [log_seguro(r["e_romb"]) for r in refin])], logx=True, logy=True),
        grafico("raices", "Convergencia de raíces para v(t)=0 (log)", "iteración k", "|t_k − t_det| (s)",
                [serie(r["metodo"], [h_["k"] for h_ in r["historial"]], [log_seguro(h_["err"]) for h_ in r["historial"]])
                 for r in (rb, rn, rs)], logy=True),
    ]
    e4m = ej[4]["resumen"]["metricas"]; e2m = ej[3]["resumen"]["metricas"]
    claves = [{"etiqueta": "t_det (s)", "valor": T}, {"etiqueta": "d_total (m)", "valor": d_total},
              {"etiqueta": "Margen vs distancia disponible (m)", "valor": margen},
              {"etiqueta": "Error máx. x RK2 (m)", "valor": e2m["err_x_max"]}, {"etiqueta": "Error máx. x RK4 (m)", "valor": e4m["err_x_max"]}]
    exacto = c == 0
    num_txt = (f"Bisección necesitó {rb['iteraciones']} iteraciones, Newton {rn['iteraciones']} y la secante {rs['iteraciones']} para hallar el instante de detención "
               f"(t_det = {T:.6g} s; analítico {T_ref:.6g} s). ")
    if exacto:
        num_txt += (f"Con desaceleración constante la solución es un polinomio de grado ≤ 2, así que RK2 y RK4 la reproducen sin error de truncamiento "
                    f"(error máx. de x: {fmt(e2m['err_x_max'])} y {fmt(e4m['err_x_max'])} m, solo redondeo) y trapecio, Simpson y Romberg integran v(t) exactamente. "
                    "Este escenario valida el código pero no distingue la calidad de los métodos: eso ocurre en ESTRÉS.")
    else:
        num_txt += (f"Con desaceleración variable RK2 comete un error máx. de {fmt(e2m['err_x_max'])} m y RK4 {fmt(e4m['err_x_max'])} m (h = {h_ef:.4g} s); "
                    f"los órdenes observados al reducir h son ≈ {fmt(p2[-1], 3)} (RK2) y ≈ {fmt(p4[-1], 3)} (RK4), coherentes con 2 y 4. "
                    f"En la integración de v(t), Simpson (error {fmt(refin[-1]['e_simp'])}) supera al trapecio ({fmt(refin[-1]['e_trap'])}) y Romberg ({fmt(refin[-1]['e_romb'])}) mejora a ambos.")
    prob_txt = (f"Con v₀ = {v0:g} m/s, a₀ = {a0:g} m/s²{'' if c == 0 else f' y c = {c:g} 1/s'} el modelo da t_det ≈ {T:.2f} s, d_f ≈ {d_f_ref:.2f} m y d_total ≈ {d_tot_ref:.2f} m "
                f"(incluye {v0 * t_r:.2f} m recorridos durante el tiempo de reacción). ")
    prob_txt += (f"Frente a la distancia disponible supuesta de {d_disp:g} m hay un margen de {margen:.2f} m. " if margen >= 0 else
                 f"Esto EXCEDE en {-margen:.2f} m la distancia disponible supuesta de {d_disp:g} m: dentro del modelo, la maniobra no cabe. ")
    prob_txt += ("La distancia de frenado crece con v₀² y con 1/a, mientras que la de reacción crece solo linealmente con v₀·t_r. "
                 "No puede inferirse nada sobre una cabina real: el modelo es 1-D, sin masa, pendiente, viento ni sistemas de freno reales; los parámetros son supuestos didácticos.")
    return {"descripcion": f"Escenario {escenario.replace('_', ' ')}: v₀={v0:g} m/s, a₀={a0:g} m/s², c={c:g} 1/s, t_r={t_r:g} s, h={h:g} s.",
            "metodos": ej, "tablas": [tab_fis, tab_orden, tab_refin], "graficos": g, "claves": claves,
            "conclusion_numerica": num_txt, "conclusion_problema": prob_txt, "avisos": []}


def _ejecutar_mal(p):
    ts, t0, eps, tol = p["t_raiz"], p["t0"], p["eps"], p["tol"]
    f = lambda t: (t - ts) ** 2
    df = lambda t: 2 * (t - ts)
    ej, avisos = [], []
    t_ = time.perf_counter(); rn = raices.newton(f, df, t0, tol, 200, ts); tn = (time.perf_counter() - t_) * 1e3
    t_ = time.perf_counter(); rm = raices.newton(f, df, t0, tol, 200, ts, m=2); tm = (time.perf_counter() - t_) * 1e3
    t_ = time.perf_counter(); rs = raices.secante(f, t0, t0 + 3, tol, 400, ts); tsec = (time.perf_counter() - t_) * 1e3
    razones = [h["err"] / (rn["historial"][i - 1]["err"] if i else abs(t0 - ts)) for i, h in enumerate(rn["historial"])]
    ej.append(_ej_raiz(rn, tol, ts, f"Convergencia solo LINEAL (razón e_k/e_(k−1) ≈ {np.mean(razones[:10]):.3f}) porque f'(t*) = 0.", tn))
    ej.append(_ej_raiz(rm, tol, ts, "Conociendo la multiplicidad m = 2 se recupera la convergencia rápida (un paso en este ejemplo).", tm))
    ej.append(_ej_raiz(rs, tol, ts, "Pierde el orden 1.618: en raíz doble la secante también es lineal.", tsec))
    try:
        raices.biseccion(f, 0, 2 * ts, tol)
    except ValueError as e:
        ej.append(ejecucion("Bisección", "Raíces", [], tolerancia=tol, convergio=False, referencia=f"t* = {ts:g} s", valor=None,
                            metricas={"aplicable": 0}, interpretacion="No aplicable: f(t) = (t − t*)² ≥ 0 nunca cambia de signo.", mensaje=str(e)))
        avisos.append("La bisección NO es aplicable (no hay cambio de signo): es una limitación del método, no del cálculo.")
    # criterio de parada engañoso |f| < tol
    k_f = next(h["k"] for h in rn["historial"] if abs(h["fx"]) < tol)
    err_f = next(h["err"] for h in rn["historial"] if abs(h["fx"]) < tol)
    # sensibilidad de la raíz a una perturbación de f
    filas_s = []
    for e in (1e-12, 1e-10, 1e-8, 1e-6, 1e-4):
        d_dob = math.sqrt(e)
        filas_s.append([e, d_dob, d_dob / e, e, 1.0])
    tab_s = tabla("Sensibilidad de la raíz: f(t) = (t − t*)² − ε  frente a una raíz simple  g(t) = (t − t*) − ε",
                  ["ε", "Desplazamiento raíz doble √ε", "Amplificación √ε/ε", "Desplazamiento raíz simple (ε)", "Amplificación simple"], filas_s,
                  "Una perturbación ε de f mueve la raíz doble √ε; la amplificación 1/√ε es enorme (condicionamiento de la raíz múltiple ≈ ∞ cuando ε → 0).")
    tab_p = tabla("Criterio de parada: residuo vs error real (Newton clásico)", ["Criterio", "Iteración en que se cumple", "Error real |t − t*|"],
                  [["|f(t_k)| < tol", k_f, err_f], ["|t_k − t_(k−1)| < tol (usado)", rn["iteraciones"], rn["historial"][-1]["err"]]],
                  "Un residuo pequeño NO garantiza una raíz precisa cuando f' ≈ 0: parar por |f| < tol dejaría un error de ≈ √tol.")
    tt = np.linspace(ts - 6, ts + 6, 300)
    g = [
        grafico("curva", "f(t) = (t − t*)² e iteraciones de Newton", "t (s)", "f(t)",
                [serie("f(t)", tt, f(tt)), serie("Iterados de Newton", [h["x"] for h in rn["historial"][:12]],
                                                  [h["fx"] for h in rn["historial"][:12]], tipo="puntos")]),
        grafico("raices", "Error vs iteración (log)", "iteración k", "|t_k − t*|",
                [serie("Newton clásico", [h["k"] for h in rn["historial"]], [log_seguro(h["err"]) for h in rn["historial"]]),
                 serie("Newton modificado (m=2)", [h["k"] for h in rm["historial"]], [log_seguro(h["err"]) for h in rm["historial"]], tipo="puntos"),
                 serie("Secante", [h["k"] for h in rs["historial"]], [log_seguro(h["err"]) for h in rs["historial"]])], logy=True),
        grafico("sens", "Desplazamiento de la raíz vs ε (log-log)", "ε", "desplazamiento de la raíz",
                [serie("Raíz doble (√ε)", [r[0] for r in filas_s], [r[1] for r in filas_s]),
                 serie("Raíz simple (ε)", [r[0] for r in filas_s], [r[3] for r in filas_s])], logx=True, logy=True),
    ]
    claves = [{"etiqueta": "Iteraciones Newton clásico", "valor": rn["iteraciones"]}, {"etiqueta": "Iteraciones Newton modificado", "valor": rm["iteraciones"]},
              {"etiqueta": "Razón de error lineal", "valor": float(np.mean(razones[:10]))},
              {"etiqueta": "Amplificación ε=1e-10", "valor": math.sqrt(1e-10) / 1e-10}]
    return {"descripcion": f"Escenario MAL CONDICIONADO (subexperimento de raíz múltiple): f(t) = (t − {ts:g})², t₀ = {t0:g}, ε = {eps:g}.",
            "metodos": ej, "tablas": [tab_s, tab_p], "graficos": g, "claves": claves, "avisos": avisos,
            "conclusion_numerica": (f"Newton clásico tarda {rn['iteraciones']} iteraciones y su error se divide por ≈ {np.mean(razones[:10]):.2f} en cada paso (convergencia lineal, no cuadrática); "
                                    f"Newton modificado con m = 2 converge en {rm['iteraciones']} paso(s) y la secante en {rs['iteraciones']}. La bisección es inaplicable. "
                                    f"Si se parara con |f| < {tol:g}, el algoritmo terminaría en la iteración {k_f} con un error real de {fmt(err_f)} (≈ √tol), no de {tol:g}. "
                                    f"Una perturbación ε = {eps:g} en f desplaza la raíz √ε = {math.sqrt(eps):.1e}, es decir, amplifica ×{math.sqrt(eps) / eps:.1e}. "
                                    "Esto es mal condicionamiento de la raíz (derivada nula), distinto de un fallo de convergencia: los métodos sí convergen, pero lento y con sensibilidad extrema."),
            "conclusion_problema": ("Este escenario NO representa una frenada más peligrosa: es un subexperimento matemático ligado al módulo. Ilustra que, si el instante de detención "
                                    "se definiera mediante una función que solo toca el cero sin cruzarlo (por ejemplo una velocidad que se anula tangencialmente), una pequeña incertidumbre en el modelo "
                                    "(ε) se traduciría en una incertidumbre mucho mayor en el instante calculado (√ε). En el modelo físico estándar (v(t) con pendiente distinta de cero en t_det) la raíz es simple y el problema está bien condicionado. "
                                    "No puede inferirse nada sobre equipos reales.")}
