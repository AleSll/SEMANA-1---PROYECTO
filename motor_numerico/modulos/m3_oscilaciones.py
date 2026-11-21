"""Módulo 3 — Oscilaciones por viento (EDO RK2/RK4 + integración de x²)."""
import math
import time

import numpy as np
from scipy.integrate import quad, solve_ivp

from .. import edo, integracion
from .comun import ejecucion, err_rel, fila, fmt, grafico, lista, log_seguro, serie, tabla

NOMBRE = "Oscilaciones por viento"
PREGUNTA = "¿Cómo se modifica la oscilación ante cambios de la fuerza externa, el amortiguamiento y los parámetros del modelo?"
MODELO = ("Oscilador amortiguado de un grado de libertad: x' = v ; v' = [F(t) − c·v − k·x]/m, con F(t) = F₀·sin(Ωt). "
          "Referencia analítica subamortiguada (ζ<1): x(t) = e^(−ζω₀t)[C₁cos(ω_d t) + C₂sin(ω_d t)] + x_p(t), con x_p la respuesta estacionaria. "
          "Magnitud acumulada: ∫₀ᵀ x(t)² dt.")
METODOS = ["RK2 (Heun)", "RK4", "Trapecio", "Simpson 1/3", "Romberg"]
ESPEC = {
    "m": {"label": "Masa equivalente m", "unidad": "kg", "min": 1, "max": 1e5, "fuente": "Sintético"},
    "c": {"label": "Amortiguamiento c", "unidad": "N·s/m", "min": 0.1, "max": 1e5, "fuente": "Sintético"},
    "k": {"label": "Rigidez k", "unidad": "N/m", "min": 1, "max": 1e6, "fuente": "Sintético"},
    "x0": {"label": "Posición inicial x₀", "unidad": "m", "min": -5, "max": 5, "fuente": "Sintético"},
    "v0": {"label": "Velocidad inicial v₀", "unidad": "m/s", "min": -10, "max": 10, "fuente": "Sintético"},
    "F0": {"label": "Amplitud de fuerza F₀", "unidad": "N", "min": 0, "max": 1e4, "fuente": "Sintético"},
    "Omega": {"label": "Frecuencia de la fuerza Ω", "unidad": "rad/s", "min": 0, "max": 50, "fuente": "Sintético"},
    "T": {"label": "Tiempo de simulación T", "unidad": "s", "min": 1, "max": 200, "fuente": "Configuración"},
    "h": {"label": "Paso RK (h)", "unidad": "s", "min": 0.001, "max": 5, "fuente": "Configuración numérica"},
}
DEFAULTS = {
    "NORMAL": {"m": 100.0, "c": 40.0, "k": 400.0, "x0": 0.05, "v0": 0.0, "F0": 0.0, "Omega": 0.0, "T": 25.0, "h": 0.05},
    "ESTRES": {"m": 100.0, "c": 40.0, "k": 400.0, "x0": 0.05, "v0": 0.0, "F0": 20.0, "Omega": 1.9, "T": 40.0, "h": 0.05},
    "MAL_CONDICIONADO": {"m": 100.0, "c": 399.6, "k": 400.0, "x0": 0.05, "v0": 0.0, "F0": 0.0, "Omega": 0.0, "T": 25.0, "h": 1.2},
}


def solucion_analitica(m, c, k, x0, v0, F0=0.0, Om=0.0):
    """Solución exacta del oscilador subamortiguado (ζ<1) con fuerza armónica. Devuelve x(t), v(t), ω₀, ζ, ω_d."""
    w0 = math.sqrt(k / m); z = c / (2 * math.sqrt(k * m))
    if z >= 1:
        raise ValueError("La referencia analítica implementada requiere régimen subamortiguado (ζ < 1).")
    wd = w0 * math.sqrt(1 - z * z)
    A = B = 0.0
    if F0:
        D = k - m * Om ** 2; det = D * D + (c * Om) ** 2
        A = F0 * D / det; B = -F0 * c * Om / det
    C1 = x0 - B; C2 = (v0 + z * w0 * C1 - Om * A) / wd

    def x(t):
        t = np.asarray(t, float)
        return np.exp(-z * w0 * t) * (C1 * np.cos(wd * t) + C2 * np.sin(wd * t)) + A * np.sin(Om * t) + B * np.cos(Om * t)

    def v(t):
        t = np.asarray(t, float); e = np.exp(-z * w0 * t)
        return e * (-z * w0 * (C1 * np.cos(wd * t) + C2 * np.sin(wd * t)) + wd * (-C1 * np.sin(wd * t) + C2 * np.cos(wd * t))) + Om * (A * np.cos(Om * t) - B * np.sin(Om * t))
    return x, v, w0, z, wd, C1, C2


def referencia_independiente(m, c, k, x0, v0, F0, Om, T):
    """Integrador de alta precisión (DOP853, rtol=1e-12) usado para contrastar la solución analítica."""
    f = lambda t, y: [y[1], (F0 * math.sin(Om * t) - c * y[1] - k * y[0]) / m]
    return solve_ivp(f, [0, T], [x0, v0], method="DOP853", rtol=1e-12, atol=1e-14, dense_output=True)


def ejecutar(escenario, p):
    m, c, k, x0, v0, F0, Om, T, h = (p[q] for q in ("m", "c", "k", "x0", "v0", "F0", "Omega", "T", "h"))
    x_an, v_an, w0, zeta, wd, C1, C2 = solucion_analitica(m, c, k, x0, v0, F0, Om)
    n = max(1, math.ceil(T / h)); h_ef = T / n
    fode = lambda t, y: np.array([y[1], (F0 * math.sin(Om * t) - c * y[1] - k * y[0]) / m])
    ej, trayect = [], {}
    tf = np.linspace(0, T, 4001)
    amp_ref = float(np.max(np.abs(x_an(tf))))
    sol = referencia_independiente(m, c, k, x0, v0, F0, Om, T)
    dif_ref = float(np.max(np.abs(sol.sol(tf)[0] - x_an(tf))))
    for nombre, fun, kw in (("RK2 (Heun)", edo.rk2, {"variante": "heun"}), ("RK4", edo.rk4, {})):
        t_ = time.perf_counter(); tt, yy = fun(fode, 0.0, [x0, v0], h_ef, n, **kw); tm = (time.perf_counter() - t_) * 1e3
        xr, vr = x_an(tt), v_an(tt)
        ex = np.abs(yy[:, 0] - xr); ev = np.abs(yy[:, 1] - vr)
        finite = np.all(np.isfinite(yy))
        trayect[nombre] = (tt, yy, ex)
        filas = [fila(i, {"t": float(tt[i]), "x": float(yy[i, 0]), "v": float(yy[i, 1]), "x_ref": float(xr[i])}, None, ex[i], err_rel(xr[i], yy[i, 0])) for i in range(len(tt))]
        crece = bool(np.max(np.abs(yy[:, 0])) > 10 * max(amp_ref, abs(x0), 1e-12))
        ej.append(ejecucion(nombre, "EDO", filas, paso=h_ef, max_iter=n, convergio=bool(finite and not crece), tiempo_ms=tm,
                            referencia="Solución analítica x(t) (contrastada con DOP853 rtol=1e-12)", valor={"x_T": float(yy[-1, 0]), "v_T": float(yy[-1, 1])},
                            metricas={"err_x_max": float(np.nanmax(ex)), "err_v_max": float(np.nanmax(ev)), "amp_max": float(np.max(np.abs(yy[:, 0]))), "amp_ref": amp_ref,
                                      "x_T": yy[-1, 0], "h": h_ef},
                            interpretacion=("Orden 2; su región de estabilidad es pequeña: con h grande puede crecer aunque la solución real decaiga." if "RK2" in nombre
                                            else "Orden 4; región de estabilidad mayor (|hλ| ≲ 2.78 sobre el eje real negativo).")))
    dif24 = float(np.max(np.abs(trayect["RK2 (Heun)"][1][:, 0] - trayect["RK4"][1][:, 0])))
    # ---- magnitud acumulada ∫ x² dt ----------------------------------------------------------------------------------
    I_ref = quad(lambda t: float(x_an(t)) ** 2, 0, T, limit=2000, epsabs=1e-14, epsrel=1e-13)[0]
    refin = integracion.tabla_refinamiento(lambda t: x_an(t) ** 2, 0.0, T, I_ref, niveles=(3, 4, 5, 6, 7, 8, 9))
    for nombre, kv, ke in (("Trapecio", "trapecio", "e_trap"), ("Simpson 1/3", "simpson", "e_simp"), ("Romberg", "romberg", "e_romb")):
        filas = [fila(i + 1, {"n": r["n"], "h": r["h"], "integral": r[kv]}, None, r[ke], err_rel(I_ref, r[kv])) for i, r in enumerate(refin)]
        ej.append(ejecucion(nombre, "Integración", filas, paso=refin[-1]["h"], max_iter=refin[-1]["n"], referencia=f"∫₀ᵀx² dt (scipy.quad, tol 1e-13) = {I_ref:.10e} m²·s",
                            valor=refin[-1][kv], metricas={"integral": refin[-1][kv], "error_abs": refin[-1][ke], "n": refin[-1]["n"]},
                            interpretacion={"Trapecio": "O(h²)", "Simpson 1/3": "O(h⁴)", "Romberg": "Richardson sobre trapecio"}[nombre]))
    tab_refin = tabla("Refinamiento de ∫₀ᵀ x(t)² dt", ["n", "h (s)", "Trapecio", "Error", "Simpson 1/3", "Error", "Romberg", "Error"],
                      [[r["n"], r["h"], r["trapecio"], r["e_trap"], r["simpson"], r["e_simp"], r["romberg"], r["e_romb"]] for r in refin],
                      f"Referencia: {I_ref:.8e} m²·s. Si f'(a) y f'(b) son ≈ 0 (aquí (x²)'(0) = 0 con v₀ = 0) los términos de borde de Euler-Maclaurin se anulan y el trapecio puede superar a Simpson; no es un error. Con pocas muestras por oscilación (h·ω_d grande) todos los métodos fallan; la convergencia solo es visible cuando h resuelve el periodo T_d = {2 * math.pi / wd:.3f} s.")
    # ---- tablas de parámetros derivados ---------------------------------------------------------------------------------
    tab_par = tabla("Parámetros derivados del modelo", ["Magnitud", "Valor", "Unidad"],
                    [["ω₀ = √(k/m)", w0, "rad/s"], ["ζ = c/(2√(km))", zeta, "—"], ["ω_d = ω₀√(1−ζ²)", wd, "rad/s"], ["Periodo amortiguado T_d", 2 * math.pi / wd, "s"],
                     ["C₁", C1, "m"], ["C₂", C2, "m"], ["Amplitud máx. analítica |x|", amp_ref, "m"], ["Diferencia analítica vs DOP853", dif_ref, "m"],
                     ["Diferencia máx. RK2 − RK4", dif24, "m"]])
    tabs = [tab_par, tab_refin]
    # ---- estudio de refinamiento de h (solo para escenarios con h razonable) ----------------------------------------
    hs, e2, e4 = [], [], []
    for kk in range(4):
        nk = n * 2 ** kk; hk = T / nk; hs.append(hk)
        _, y2 = edo.rk2(fode, 0.0, [x0, v0], hk, nk); _, y4 = edo.rk4(fode, 0.0, [x0, v0], hk, nk)
        tk = hk * np.arange(nk + 1)
        e2.append(float(np.max(np.abs(y2[:, 0] - x_an(tk))))); e4.append(float(np.max(np.abs(y4[:, 0] - x_an(tk)))))
    p2, p4 = edo.orden_empirico(e2, hs), edo.orden_empirico(e4, hs)
    tabs.append(tabla("Refinamiento del paso: error máximo de x(t) al reducir h a la mitad", ["h (s)", "Error RK2", "Orden RK2", "Error RK4", "Orden RK4"],
                      [[hs[i], e2[i], None if i == 0 else p2[i - 1], e4[i], None if i == 0 else p4[i - 1]] for i in range(4)],
                      "El orden empírico solo se acerca a 2 y 4 cuando h está dentro de la región de estabilidad y es suficientemente pequeño."))
    avisos = []
    # ---- gráficos ----------------------------------------------------------------------------------------------------------
    tt4 = trayect["RK4"][0]
    lim = lambda a: a  # sin recortes: si RK2 diverge, la gráfica debe mostrarlo tal cual
    g = [grafico("x", "Respuesta x(t)", "t (s)", "x (m)",
                 [serie("Analítica", tf, x_an(tf)), serie("RK4", tt4, lim(trayect["RK4"][1][:, 0])), serie("RK2 (Heun)", trayect["RK2 (Heun)"][0], lim(trayect["RK2 (Heun)"][1][:, 0]))]),
         grafico("err", "Error global |x_RK − x_ref| (log)", "t (s)", "error (m)",
                 [serie(q, v[0], [log_seguro(e) for e in v[2]]) for q, v in trayect.items()], logy=True),
         grafico("refin", "Error de ∫x²dt vs n (log-log)", "n subintervalos", "error (m²·s)",
                 [serie("Trapecio", [r["n"] for r in refin], [log_seguro(r["e_trap"]) for r in refin]),
                  serie("Simpson 1/3", [r["n"] for r in refin], [log_seguro(r["e_simp"]) for r in refin]),
                  serie("Romberg", [r["n"] for r in refin], [log_seguro(r["e_romb"]) for r in refin])], logx=True, logy=True)]
    lam = complex(-zeta * w0, wd)
    inestable_rk2 = abs(edo.factor_amplificacion("rk2", h_ef * lam)) > 1
    inestable_rk4 = abs(edo.factor_amplificacion("rk4", h_ef * lam)) > 1
    filas_est = [[hh, abs(edo.factor_amplificacion("rk2", hh * lam)), abs(edo.factor_amplificacion("rk4", hh * lam)), abs(np.exp(hh * lam))] for hh in (0.1, 0.5, 1.0, 1.2, 1.5, 2.0)]
    tabs.append(tabla("Estabilidad del esquema: factor de amplificación por paso |R(hλ)| para λ = −ζω₀ + iω_d", ["h (s)", "|R| RK2", "|R| RK4", "|e^(hλ)| exacto"], filas_est,
                      "|R| > 1 significa que el esquema numérico crece en cada paso aunque la solución real decaiga (|e^(hλ)| < 1). Es un fenómeno de ESTABILIDAD DEL ESQUEMA, distinto del mal condicionamiento del problema."))
    # tabla de coeficientes cerca de ζ → 1 (solo informativa en MAL)
    if escenario == "MAL_CONDICIONADO":
        filas_z = []
        for zz in (0.1, 0.5, 0.9, 0.99, 0.999, 0.99999, 1 - 1e-9):
            cc = 2 * zz * math.sqrt(k * m)
            try:
                xa, _, w0_, z_, wd_, c1_, c2_ = solucion_analitica(m, cc, k, x0, v0)
                tt_ = 1.0
                ref_ = solve_ivp(lambda t, y: [y[1], (-cc * y[1] - k * y[0]) / m], [0, tt_], [x0, v0], method="DOP853", rtol=1e-13, atol=1e-16).y[0, -1]
                filas_z.append([zz, wd_, abs(c2_) / abs(c1_) if c1_ else None, float(xa(tt_)), float(ref_), abs(float(xa(tt_)) - ref_) / abs(ref_)])
            except Exception as e:  # pragma: no cover
                filas_z.append([zz, None, None, None, None, None])
        tabs.append(tabla("Fórmula subamortiguada cerca del régimen crítico (ζ → 1): coeficientes y valor de x(1 s)", ["ζ", "ω_d (rad/s)", "|C₂/C₁|", "x(1) fórmula", "x(1) DOP853", "Dif. relativa"], filas_z,
                          "Cuando ζ → 1, ω_d → 0 y C₂ ∝ 1/ω_d crece sin límite, pero C₂·sin(ω_d t) ≈ (v₀+ζω₀x₀)·t se mantiene acotado: la fórmula NO pierde precisión de forma apreciable hasta que ω_d es del orden del redondeo; "
                          "solo es indefinida exactamente en ζ = 1 (división entre ω_d = 0)."))
        g.append(grafico("estab", "Factor de amplificación por paso vs h (log-y)", "h (s)", "|R(hλ)|",
                         [serie("RK2 (Heun)", [f_[0] for f_ in filas_est], [f_[1] for f_ in filas_est]), serie("RK4", [f_[0] for f_ in filas_est], [f_[2] for f_ in filas_est]),
                          serie("Exacto e^(hλ)", [f_[0] for f_ in filas_est], [f_[3] for f_ in filas_est]), serie("Límite |R| = 1", [0.1, 2.0], [1, 1])], logy=True))
        if inestable_rk2:
            avisos.append(f"RK2 con h = {h_ef:.3g} s es INESTABLE (|R| = {abs(edo.factor_amplificacion('rk2', h_ef * lam)):.3f} > 1): la solución numérica crece mientras la real decae. No es «viento fuerte»: es el esquema.")
    ex2 = ej[0]["resumen"]["metricas"]; ex4 = ej[1]["resumen"]["metricas"]
    claves = [{"etiqueta": "ζ", "valor": zeta}, {"etiqueta": "ω_d (rad/s)", "valor": wd}, {"etiqueta": "Amplitud máx. |x| (m)", "valor": amp_ref},
              {"etiqueta": "Error máx. RK2 (m)", "valor": ex2["err_x_max"]}, {"etiqueta": "Error máx. RK4 (m)", "valor": ex4["err_x_max"]},
              {"etiqueta": "∫x²dt (m²·s)", "valor": I_ref}]
    num = (f"RK4 (error máx. {fmt(ex4['err_x_max'])} m) frente a RK2 (error máx. {fmt(ex2['err_x_max'])} m) con h = {h_ef:.4g} s: la diferencia entre ambos llega a {fmt(dif24)} m. "
           f"Órdenes observados al refinar h: ≈ {fmt(p2[-1], 3)} (RK2) y ≈ {fmt(p4[-1], 3)} (RK4). "
           f"Para ∫x²dt (ref. {I_ref:.5e} m²·s), con n = {refin[-1]['n']}: trapecio {fmt(refin[-1]['e_trap'])}, Simpson {fmt(refin[-1]['e_simp'])}, Romberg {fmt(refin[-1]['e_romb'])}. ")
    if escenario == "MAL_CONDICIONADO":
        num += (f"Con ζ = {zeta:.4f} (casi crítico) y h = {h_ef:.3g} s, |R_RK2| = {abs(edo.factor_amplificacion('rk2', h_ef * lam)):.3f} {'> 1 → RK2 diverge' if inestable_rk2 else '< 1'} "
                f"y |R_RK4| = {abs(edo.factor_amplificacion('rk4', h_ef * lam)):.3f} {'> 1' if inestable_rk4 else '< 1 → RK4 permanece estable'}; el valor exacto por paso es {abs(np.exp(h_ef * lam)):.3f}. "
                f"Ojo: RK4 es estable pero con h tan grande su error ({fmt(ex4['err_x_max'])} m) es comparable a la amplitud real ({amp_ref:g} m): estable ≠ preciso. La fórmula analítica aparece con C₂ = {C2:.3f} m ≫ x₀ = {x0:g} m, pero sigue siendo precisa (ver tabla ζ → 1). Es inestabilidad del esquema y sensibilidad de la representación, no una dificultad del problema físico.")
    if escenario == "ESTRES":
        num += "La fuerza armónica cercana a ω_d (casi resonancia) aumenta la amplitud y, al haber más oscilación acumulada, el error global de RK2 crece más que en NORMAL."
    prob = (f"Con ζ = {zeta:.3f} y ω_d = {wd:.4f} rad/s (T_d = {2 * math.pi / wd:.2f} s), la amplitud máxima del desplazamiento es {amp_ref:.4f} m (inicial {abs(x0):g} m) y la magnitud acumulada ∫x²dt vale {I_ref:.4e} m²·s. ")
    if escenario == "ESTRES":
        prob += (f"La excitación F₀ = {F0:g} N a Ω = {Om:g} rad/s (cerca de ω_d) amplifica el movimiento ×{amp_ref / abs(x0):.1f} respecto de la posición inicial: más fuerza y cercanía a la resonancia aumentan el desplazamiento y la energía acumulada. ")
    elif escenario == "MAL_CONDICIONADO":
        prob += "Con amortiguamiento casi crítico la cabina equivalente volvería a su posición sin oscilar apenas; el escenario no habla de «más viento» sino de la sensibilidad numérica cerca de ζ = 1. "
    else:
        prob += "Sin fuerza externa la oscilación se extingue con decremento logarítmico δ = 2πζ/√(1−ζ²). "
    prob += "Variables influyentes: ζ (decaimiento), ω₀ (frecuencia) y, en forzado, la cercanía Ω/ω_d. No puede inferirse comportamiento aerodinámico real, acoplamiento entre cabinas ni cargas de viento: es un oscilador lineal de 1 GDL con parámetros sintéticos."
    return {"descripcion": f"Escenario {escenario.replace('_', ' ')}: m={m:g} kg, c={c:g} N·s/m, k={k:g} N/m, F₀={F0:g} N, Ω={Om:g} rad/s, T={T:g} s, h={h:g} s.",
            "metodos": ej, "tablas": tabs, "graficos": g, "claves": claves, "conclusion_numerica": num, "conclusion_problema": prob, "avisos": avisos}
