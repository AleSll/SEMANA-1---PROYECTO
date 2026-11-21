"""Módulo 4 — Reconstrucción de señales de sensores (interpolación + raíz de cruce de umbral)."""
import math
import time

import numpy as np

from .. import raices
from ..interpolacion import constante_lebesgue, diferencias_divididas, lagrange, newton_dd, spline_natural
from .comun import ejecucion, err_rel, fila, fmt, grafico, log_seguro, serie, tabla

NOMBRE = "Reconstrucción de sensores"
PREGUNTA = "¿Qué tan bien se reconstruyen registros faltantes y cómo afectan el espaciamiento de nodos y el ruido?"
MODELO = ("Señal sintética y(t) = sin(t) en [0, 2π]. Se entregan n nodos equiespaciados (con ruido gaussiano σ opcional) y se OCULTAN los puntos intermedios; "
          "se reconstruye con Lagrange, Newton (diferencias divididas) y spline cúbico natural y se mide el error real |sin(t) − P(t)| en los puntos ocultos. "
          "Cruce de umbral: raíz de P(t) − y_umbral con bisección y secante.")
METODOS = ["Lagrange", "Newton (dif. divididas)", "Spline cúbico natural", "Bisección", "Secante"]
ESPEC = {
    "n_nodos": {"label": "Número de nodos entregados", "unidad": "—", "min": 4, "max": 30, "entero": True, "fuente": "Configuración"},
    "sigma": {"label": "Desviación del ruido σ", "unidad": "adim.", "min": 0, "max": 0.5, "fuente": "Sintético"},
    "semilla": {"label": "Semilla del generador", "unidad": "—", "min": 0, "max": 1e6, "entero": True, "fuente": "Reproducibilidad"},
    "n_mc": {"label": "Repeticiones Monte Carlo", "unidad": "—", "min": 1, "max": 400, "entero": True, "fuente": "Configuración"},
    "umbral": {"label": "Umbral de cruce y_umbral", "unidad": "adim.", "min": -0.95, "max": 0.95, "fuente": "Supuesto didáctico"},
}
DEFAULTS = {
    "NORMAL": {"n_nodos": 9, "sigma": 0.0, "semilla": 42, "n_mc": 100, "umbral": 0.5},
    "ESTRES": {"n_nodos": 9, "sigma": 0.02, "semilla": 42, "n_mc": 200, "umbral": 0.5},
    "MAL_CONDICIONADO": {"n_nodos": 21, "sigma": 0.001, "semilla": 42, "n_mc": 100, "umbral": 0.5},
}
B = 2 * math.pi


def _ev(metodo, xn, yn):
    if metodo == "Lagrange":
        return lambda x: lagrange(xn, yn, x)
    if metodo == "Newton (dif. divididas)":
        return lambda x: newton_dd(xn, yn, x)
    S, _ = spline_natural(xn, yn)
    return S


def ejecutar(escenario, p):
    n, sig, seed, n_mc, umbral = int(p["n_nodos"]), p["sigma"], int(p["semilla"]), int(p["n_mc"]), p["umbral"]
    rng = np.random.default_rng(seed)
    xn = np.linspace(0, B, n)
    y_limpio = np.sin(xn)
    yn = y_limpio + (rng.normal(0, sig, n) if sig > 0 else 0.0)
    xo = 0.5 * (xn[:-1] + xn[1:])                      # puntos OCULTOS: puntos medios (no se entregan)
    yo = np.sin(xo)
    xs = np.linspace(0, B, 800); ys = np.sin(xs)
    nombres = ["Lagrange", "Newton (dif. divididas)", "Spline cúbico natural"]
    ej, curvas, errs = [], {}, {}
    for nm in nombres:
        t_ = time.perf_counter(); f = _ev(nm, xn, yn); po = f(xo); tm = (time.perf_counter() - t_) * 1e3
        eo = np.abs(po - yo); ed = np.abs(f(xs) - ys)
        curvas[nm] = f(xs); errs[nm] = ed
        filas = [fila(i + 1, {"t": float(xo[i]), "y_aprox": float(po[i]), "y_ref": float(yo[i])}, None, eo[i], err_rel(yo[i], po[i])) for i in range(len(xo))]
        ej.append(ejecucion(nm, "Interpolación", filas, max_iter=len(xo), tiempo_ms=tm, referencia="sin(t) exacto en puntos ocultos (puntos medios)",
                            valor={"y_aprox": [float(v) for v in po]},
                            metricas={"err_oculto_max": eo.max(), "err_oculto_rms": float(np.sqrt(np.mean(eo ** 2))), "err_denso_max": ed.max(), "n_nodos": n},
                            interpretacion={"Lagrange": "Polinomio único de grado n−1; error ∝ f⁽ⁿ⁾(ξ)/n!·Π(x−xᵢ); sensible al ruido por la constante de Lebesgue.",
                                            "Newton (dif. divididas)": "Mismo polinomio que Lagrange (unicidad) calculado por diferencias divididas; difieren solo por redondeo.",
                                            "Spline cúbico natural": "Polinomios cúbicos a trozos con C²; sistema tridiagonal; amplifica poco el ruido."}[nm]))
    dif_ln = float(np.max(np.abs(curvas["Lagrange"] - curvas["Newton (dif. divididas)"])))
    lam = constante_lebesgue(xn)
    # ---- Cruce de umbral con la curva interpolada (spline y polinomio) -------------------------------------------------
    t_ref = math.asin(umbral)
    fS = _ev("Spline cúbico natural", xn, yn); fP = _ev("Newton (dif. divididas)", xn, yn)
    h_ = lambda f: (lambda t: float(f(t)[0]) - umbral)
    a, b = 0.0, math.pi / 2
    if umbral < 0 or h_(fS)(a) * h_(fS)(b) > 0:
        a, b = (0.0, math.pi) if umbral >= 0 else (math.pi, 1.5 * math.pi)
    avisos = []
    tabs = []
    try:
        rb = raices.biseccion(h_(fS), a, b, 1e-12, raiz_ref=t_ref); rs = raices.secante(h_(fS), a, b, 1e-12, raiz_ref=t_ref)
        for r, nm in ((rb, "Bisección"), (rs, "Secante")):
            filas = [fila(h["k"], {k: h[k] for k in ("a", "b", "x", "fx") if k in h}, abs(h["fx"]), h["err"], (h["err"] or 0) / abs(t_ref) if t_ref else None) for h in r["historial"]]
            ej.append(ejecucion(nm, "Raíces", filas, tolerancia=1e-12, max_iter=len(filas), convergio=r["convergio"],
                                referencia=f"arcsin({umbral:g}) = {t_ref:.10f} (cruce del umbral por la señal real)", valor=r["raiz"],
                                metricas={"raiz": r["raiz"], "error_abs": abs(r["raiz"] - t_ref), "iteraciones": r["iteraciones"], "residuo": r["residuo"]},
                                interpretacion=f"Instante en que el spline reconstruido cruza y = {umbral:g}."))
        rp = raices.biseccion(h_(fP), a, b, 1e-12, raiz_ref=t_ref)
        tabs.append(tabla("Cruce del umbral según la curva reconstruida", ["Curva", "Instante (rad)", "Error vs arcsin(umbral)"],
                          [["Spline cúbico natural", rb["raiz"], abs(rb["raiz"] - t_ref)], ["Polinomio (Lagrange/Newton)", rp["raiz"], abs(rp["raiz"] - t_ref)], ["Referencia", t_ref, 0.0]]))
        err_cruce = abs(rb["raiz"] - t_ref)
    except ValueError as e:
        avisos.append(f"No se pudo hallar el cruce del umbral: {e}")
        err_cruce = None
    # ---- Monte Carlo y barrido de nodos ------------------------------------------------------------------------------------
    ns = [5, 9, 13, 17, 21, 25]
    filas_b = []
    xd = np.linspace(0, B, 600)
    for nn in ns:
        xnn = np.linspace(0, B, nn); lam_n = constante_lebesgue(xnn, 1500)
        ep, es = [], []
        mc = max(1, min(n_mc, 100))
        r2 = np.random.default_rng(seed + nn)
        for _ in range(mc if sig > 0 else 1):
            yy = np.sin(xnn) + (r2.normal(0, sig, nn) if sig > 0 else 0)
            ep.append(np.max(np.abs(newton_dd(xnn, yy, xd) - np.sin(xd)))); S, _ = spline_natural(xnn, yy); es.append(np.max(np.abs(S(xd) - np.sin(xd))))
        filas_b.append([nn, lam_n, float(np.mean(ep)), float(np.mean(es))])
    tabs.append(tabla(f"Efecto del número de nodos (equiespaciados) con ruido σ = {sig:g}: constante de Lebesgue y error máximo medio",
                      ["n nodos", "Constante de Lebesgue Λ", "Error máx. polinomio", "Error máx. spline"], filas_b,
                      "Λ = máx Σ|Lᵢ(x)| es el factor con que la interpolación polinomial puede amplificar el error de los datos; crece exponencialmente con n en nodos equiespaciados."))
    # Monte Carlo sobre la configuración elegida
    mp, ms, = [], []
    r3 = np.random.default_rng(seed + 1000)
    for _ in range(n_mc if sig > 0 else 1):
        yy = y_limpio + (r3.normal(0, sig, n) if sig > 0 else 0)
        mp.append(np.max(np.abs(newton_dd(xn, yy, xs) - ys))); S, _ = spline_natural(xn, yy); ms.append(np.max(np.abs(S(xs) - ys)))
    amp_p = float(np.mean(mp) / sig) if sig > 0 else None; amp_s = float(np.mean(ms) / sig) if sig > 0 else None
    tabs.append(tabla(f"Monte Carlo ({n_mc if sig > 0 else 1} repetición/es) con n = {n} nodos y σ = {sig:g}", ["Método", "Error máx. medio", "Error máx. / σ (amplificación)"],
                      [["Polinomio (Lagrange/Newton)", float(np.mean(mp)), amp_p], ["Spline cúbico natural", float(np.mean(ms)), amp_s]],
                      "Si el cociente ≫ 1 el método amplifica el ruido; ≈ 1–3 indica un comportamiento estable."))
    if n <= 10:
        T = diferencias_divididas(xn, yn)
        tabs.append(tabla("Tabla de diferencias divididas de Newton (primera fila = coeficientes)", ["k", "f[x₀,…,x_k]"], [[k, float(T[0, k])] for k in range(n)]))
    # ---- gráficos -------------------------------------------------------------------------------------------------------------
    g = [grafico("curvas", "Reconstrucción con los nodos entregados", "t", "y",
                 [serie("sin(t) exacta", xs, ys), serie("Lagrange / Newton", xs, np.clip(curvas["Lagrange"], -10, 10)), serie("Spline cúbico natural", xs, curvas["Spline cúbico natural"]),
                  serie("Nodos entregados", xn, yn, tipo="puntos"), serie("Puntos ocultos", xo, yo, tipo="puntos")]),
         grafico("err", "Error de reconstrucción |sin(t) − P(t)| (log)", "t", "error",
                 [serie("Polinomio", xs, [log_seguro(e) for e in errs["Lagrange"]]), serie("Spline", xs, [log_seguro(e) for e in errs["Spline cúbico natural"]])], logy=True),
         grafico("nodos", f"Error máx. vs número de nodos (σ = {sig:g}, log)", "n nodos", "error máx.",
                 [serie("Polinomio", [r[0] for r in filas_b], [log_seguro(r[2]) for r in filas_b]), serie("Spline", [r[0] for r in filas_b], [log_seguro(r[3]) for r in filas_b])], logy=True)]
    em = {nm: e["resumen"]["metricas"] for nm, e in zip(nombres, ej[:3])}
    claves = [{"etiqueta": "Nodos", "valor": n}, {"etiqueta": "σ", "valor": sig}, {"etiqueta": "Error oculto máx. polinomio", "valor": em["Lagrange"]["err_oculto_max"]},
              {"etiqueta": "Error oculto máx. spline", "valor": em["Spline cúbico natural"]["err_oculto_max"]}, {"etiqueta": "Constante de Lebesgue Λ", "valor": lam}]
    num = (f"Con {n} nodos equiespaciados y σ = {sig:g}, el error máximo en puntos ocultos es {fmt(em['Lagrange']['err_oculto_max'])} para el polinomio (Lagrange y Newton coinciden: diferencia máx. {fmt(dif_ln)}, solo redondeo) "
           f"y {fmt(em['Spline cúbico natural']['err_oculto_max'])} para el spline. Constante de Lebesgue Λ = {lam:.4g}. ")
    if sig > 0:
        num += f"Monte Carlo: el polinomio amplifica el ruido ×{amp_p:.1f} y el spline ×{amp_s:.1f} (error máx. medio / σ). "
    if escenario == "NORMAL":
        num += "Sin ruido, el polinomio de grado n−1 es ligeramente mejor o similar al spline para esta función analítica; la ventaja del spline aparece al añadir ruido o aumentar n."
    elif escenario == "ESTRES":
        num += "El ruido degrada ambos métodos, pero el polinomio de grado 8 lo amplifica más que el spline."
    else:
        num += ("Este es un subexperimento de mal condicionamiento de la INTERPOLACIÓN POLINOMIAL: con 21 nodos equiespaciados Λ ≈ 10⁴, de modo que un ruido de solo σ = 0.001 se convierte en errores de orden 1 o mayor, "
                "mientras que el spline permanece en el orden de σ. La reconstrucción polinomial no diverge por el método (la interpolación es exacta en los nodos): el problema es sensible.")
    prob = (f"La señal reconstruida permite estimar valores faltantes con un error de ≈ {fmt(em['Spline cúbico natural']['err_oculto_max'])} (spline) en los instantes ocultos"
            + (f"; el instante en que la señal cruza y = {umbral:g} se recupera con error de {fmt(err_cruce)} rad. " if err_cruce is not None else ". "))
    prob += ("Variables influyentes: densidad de muestras, nivel de ruido y tipo de interpolante. " +
             ("Con ruido, rellenar datos faltantes con un polinomio de grado alto sobre muchos nodos equiespaciados es poco fiable; un spline o menos nodos es más robusto. " if sig > 0 else "") +
             "No puede inferirse el comportamiento de un sensor real: la señal es sin(t) y el ruido gaussiano es un supuesto; en datos reales habría deriva, ruido no gaussiano y datos atípicos. "
             "La fiabilidad solo se mide fuera de los nodos (puntos ocultos), nunca con el ajuste en los nodos.")
    return {"descripcion": f"Escenario {escenario.replace('_', ' ')}: n={n} nodos en [0, 2π], σ={sig:g}, semilla={seed}.", "metodos": ej, "tablas": tabs, "graficos": g, "claves": claves,
            "conclusion_numerica": num, "conclusion_problema": prob, "avisos": avisos}
