"""Módulo 2 — Deterioro mecánico y mantenimiento (raíces + sistemas lineales SPD)."""
import json
import math
import time
from pathlib import Path

import numpy as np

from .. import raices
from ..errores import sensibilidad
from ..sistemas_lineales import es_spd, gauss_seidel, gradiente_conjugado, jacobi, lu, radio_espectral
from .comun import ejecucion, err_rel, fila, fmt, grafico, log_seguro, serie, tabla
from .m1_detencion import _ej_raiz

NOMBRE = "Deterioro y mantenimiento"
PREGUNTA = "¿En qué momento un indicador hipotético de deterioro alcanzaría un umbral de inspección y qué tan fiable es su calibración?"
MODELO = ("D(t) = D₀ + α·t + β·t² (indicador adimensional, abstracto). Tiempo al umbral: f(t) = D(t) − D_umbral = 0. "
          "Calibración de 4 coeficientes por mínimos cuadrados: (MᵀM)c = Mᵀy, sistema 4×4 simétrico definido positivo, "
          "resuelto con Jacobi, Gauss-Seidel, LU y gradiente conjugado.")
METODOS = ["Bisección", "Newton-Raphson", "Secante", "Jacobi", "Gauss-Seidel", "LU", "Gradiente conjugado"]

RUTA = Path(__file__).resolve().parents[2] / "datos_ejemplo" / "sistemas_semana1.json"
ESPEC = {
    "D0": {"label": "Deterioro inicial D₀", "unidad": "adim.", "min": 0, "max": 0.9, "fuente": "Sintético"},
    "alfa": {"label": "Tasa lineal α", "unidad": "1/mes", "min": 0, "max": 0.2, "fuente": "Sintético"},
    "beta": {"label": "Aceleración β", "unidad": "1/mes²", "min": 0, "max": 0.01, "fuente": "Sintético"},
    "D_umbral": {"label": "Umbral de inspección", "unidad": "adim.", "min": 0.05, "max": 2, "fuente": "Supuesto didáctico"},
    "tol_raiz": {"label": "Tolerancia de raíces", "unidad": "—", "min": 1e-13, "max": 1e-3, "fuente": "Configuración numérica"},
    "tol_sis": {"label": "Tolerancia de sistemas lineales", "unidad": "—", "min": 1e-12, "max": 1e-3, "fuente": "Configuración numérica"},
    "pert_pct": {"label": "Perturbación alternada de b", "unidad": "%", "min": 0, "max": 50, "fuente": "Sintético"},
}
DEFAULTS = {
    "NORMAL": {"D0": 0.10, "alfa": 0.015, "beta": 0.0005, "D_umbral": 0.40, "tol_raiz": 1e-10, "tol_sis": 1e-8},
    "ESTRES": {"D0": 0.10, "alfa": 0.020, "beta": 0.001, "D_umbral": 0.40, "tol_raiz": 1e-10, "tol_sis": 1e-8, "pert_pct": 5.0},
    "MAL_CONDICIONADO": {"tol_sis": 1e-8, "pert_pct": 5.0},
}


def _ejecs_sistema(res, A, b, x_ref, tol, nota_mal=False):
    """Convierte los Resultado del motor de sistemas lineales a ejecuciones normalizadas."""
    rho = {"Jacobi": radio_espectral(A, "jacobi"), "Gauss-Seidel": radio_espectral(A, "gauss_seidel")}
    textos = {"Jacobi": "Converge si ρ(T_J) < 1.", "Gauss-Seidel": "Converge si A es SPD o diagonalmente dominante; ρ(T_GS) rige la velocidad.",
              "LU": "Directo: una factorización y dos sustituciones; el error es solo de redondeo.",
              "Gradiente conjugado": "Para SPD termina en ≤ n pasos en aritmética exacta."}
    out = []
    nx = np.linalg.norm(x_ref)
    for r in res:
        filas = [fila(k, [float(v) for v in x], rr, e, np.linalg.norm(x - x_ref) / nx if nx else None) for (k, x, rr, e) in r.historial]
        mt = {"iteraciones": r.iteraciones, "residuo": r.residuo, "error_max": r.historial[-1][3], "convergio": float(r.convergio)}
        if r.metodo in rho:
            mt["rho"] = rho[r.metodo]
        txt = textos[r.metodo]
        if not r.convergio and r.metodo in rho:
            txt = f"NO converge: ρ = {rho[r.metodo]:.4g} ≥ 1 (el residuo crece)."
        out.append(ejecucion(r.metodo, "Sistemas lineales", filas, tolerancia=tol, max_iter=100000 if r.metodo in rho else 1000,
                             convergio=r.convergio, referencia="Solución conocida x* (b = A·x*)", valor=[float(v) for v in r.x] if np.all(np.isfinite(r.x)) else None,
                             metricas=mt, interpretacion=txt))
    return out


def _graf_sistemas(res, logx=False):
    gs_r, gs_e = [], []
    for r in res:
        k = [h[0] for h in r.historial]
        gs_r.append(serie(f"{r.metodo} ({r.iteraciones} it.)", k, [log_seguro(h[2]) for h in r.historial], tipo="linea" if len(k) > 1 else "puntos"))
        gs_e.append(serie(r.metodo, k, [log_seguro(h[3]) for h in r.historial], tipo="linea" if len(k) > 1 else "puntos"))
    return [grafico("res", "Residuo ‖b − A·x‖∞ por iteración (log)", "iteración k", "residuo", gs_r, logx=logx, logy=True),
            grafico("err", "Error ‖x − x*‖∞ por iteración (log)", "iteración k", "error", gs_e, logx=logx, logy=True)]


def _ejecutar_raices(p):
    D0, al, be, Du, tol = p["D0"], p["alfa"], p["beta"], p["D_umbral"], p["tol_raiz"]
    D = lambda t: D0 + al * t + be * t * t
    f = lambda t: D(t) - Du
    df = lambda t: al + 2 * be * t
    disc = al * al + 4 * be * (Du - D0)
    t_ref = (-al + math.sqrt(disc)) / (2 * be) if be > 0 else (Du - D0) / al
    ts = 3 * t_ref + 5
    ej = []
    t_ = time.perf_counter(); rb = raices.biseccion(f, 0, ts, tol, raiz_ref=t_ref); tb = (time.perf_counter() - t_) * 1e3
    t_ = time.perf_counter(); rn = raices.newton(f, df, 1.5 * t_ref, tol, raiz_ref=t_ref); tn = (time.perf_counter() - t_) * 1e3
    t_ = time.perf_counter(); rs = raices.secante(f, 0, ts, tol, raiz_ref=t_ref); tsec = (time.perf_counter() - t_) * 1e3
    ej.append(_ej_raiz(rb, tol, t_ref, "Intervalo [0, %.1f]: |e| ≤ (b−a)/2^k, ≈ 1 bit por iteración." % ts, tb))
    ej.append(_ej_raiz(rn, tol, t_ref, "Convergencia cuadrática (raíz simple): el número de cifras correctas se duplica.", tn))
    ej.append(_ej_raiz(rs, tol, t_ref, "Orden ≈ 1.618 sin derivada.", tsec))
    # sensibilidad ±10 %
    def raiz(D0_=D0, al_=al, be_=be, Du_=Du):
        d = al_ ** 2 + 4 * be_ * (Du_ - D0_)
        return (-al_ + math.sqrt(d)) / (2 * be_) if be_ > 0 else (Du_ - D0_) / al_
    filas_s = []
    for nombre, clave in (("α (tasa lineal)", "al_"), ("β (aceleración)", "be_"), ("D_umbral", "Du_")):
        vals = []
        for fct in (0.9, 1.0, 1.1):
            kw = {clave: {"al_": al, "be_": be, "Du_": Du}[clave] * fct}
            vals.append(raiz(**kw))
        filas_s.append([nombre, vals[0], vals[1], vals[2], max(abs(vals[0] - vals[1]), abs(vals[2] - vals[1])),
                        100 * max(abs(vals[0] - vals[1]), abs(vals[2] - vals[1])) / vals[1]])
    tab_s = tabla("Sensibilidad del tiempo al umbral a ±10 % de cada parámetro (meses)", ["Parámetro", "−10 %", "Nominal", "+10 %", "Efecto máx. (meses)", "Efecto máx. (%)"], filas_s,
                  "Cálculo con la fórmula cuadrática exacta, variando un parámetro a la vez.")
    # mantenimiento retrasado
    filas_m = []
    for dl in (0, 1, 2, 3, 6):
        d = D(t_ref + dl)
        filas_m.append([dl, t_ref + dl, d, d - Du, 100 * (d - Du) / Du])
    tab_m = tabla("Efecto de un mantenimiento hipotéticamente retrasado Δ meses sobre el indicador", ["Retraso Δ (meses)", "Instante (meses)", "D(t*+Δ)", "Exceso sobre umbral", "Exceso (%)"], filas_m,
                  "Modelo: el indicador sigue creciendo mientras no hay intervención. Es un efecto dentro del modelo sintético, no una predicción.")
    tt = np.linspace(0, max(25, 1.8 * t_ref), 300)
    g = [grafico("D", "Indicador sintético D(t) y umbral", "t (meses)", "D (adim.)",
                 [serie("D(t)", tt, D(tt)), serie("Umbral", [0, tt[-1]], [Du, Du]), serie("Raíz t*", [t_ref], [Du], tipo="puntos")]),
         grafico("raices", "Convergencia de raíces para D(t) = D_umbral (log)", "iteración k", "|t_k − t*| (meses)",
                 [serie(r["metodo"], [h["k"] for h in r["historial"]], [log_seguro(h["err"]) for h in r["historial"]]) for r in (rb, rn, rs)], logy=True)]
    info = {"t_ref": t_ref, "rb": rb, "rn": rn, "rs": rs, "al": al, "be": be, "Du": Du, "D0": D0, "tab": [tab_s, tab_m], "g": g}
    return ej, info


def _ejecutar_sistema(escenario, p, datos):
    tol = p["tol_sis"]
    if escenario == "MAL_CONDICIONADO":
        A = np.array(datos["mal_condicionado"]["A"], float); x_ref = np.array(datos["mal_condicionado"]["x_ref"], float)
    else:
        A = np.array(datos["normal"]["A"], float); x_ref = np.array(datos["normal"]["x_ref"], float)
    b = A @ x_ref
    tabs, avisos = [], []
    x_obj = x_ref
    if escenario == "ESTRES":
        signo = np.array([1, -1, 1, -1.0])
        b_e = b * (1 + signo * p["pert_pct"] / 100)
        x_obj = np.linalg.solve(A, b_e)
        sens = sensibilidad(A, b, b_e - b)
        filas_c = [[f"x{i + 1}", x_ref[i], x_obj[i], x_obj[i] - x_ref[i], 100 * (x_obj[i] - x_ref[i]) / x_ref[i]] for i in range(4)]
        tabs.append(tabla(f"Efecto de la perturbación alternada ±{p['pert_pct']:g} % de b sobre la solución", ["Incógnita", "NORMAL", "ESTRÉS", "Cambio abs.", "Cambio rel. (%)"], filas_c))
        b = b_e
    res = [jacobi(A, b, tol=tol, x_ref=x_obj), gauss_seidel(A, b, tol=tol, x_ref=x_obj), lu(A, b, x_ref=x_obj), gradiente_conjugado(A, b, tol=tol, x_ref=x_obj)]
    ej = _ejecs_sistema(res, A, b, x_obj, tol)
    spd = es_spd(A); kappa = float(np.linalg.cond(A, 2)); rj, rg = radio_espectral(A, "jacobi"), radio_espectral(A, "gauss_seidel")
    tabs.append(tabla("Propiedades de A y condiciones de aplicación", ["Propiedad", "Valor", "Consecuencia"],
                      [["¿A simétrica definida positiva?", "Sí" if spd else "No", "Gradiente conjugado estándar aplicable" if spd else "NO usar CG estándar"],
                       ["κ₂(A)", kappa, "Amplificación máxima de perturbaciones en b"],
                       ["ρ(T_Jacobi)", rj, "< 1: Jacobi converge" if rj < 1 else "≥ 1: Jacobi DIVERGE"],
                       ["ρ(T_Gauss-Seidel)", rg, "< 1: Gauss-Seidel converge" if rg < 1 else "≥ 1: diverge"]]))
    if not spd:
        avisos.append("La matriz no es SPD: el gradiente conjugado estándar no tiene garantía de convergencia.")
    claves = [{"etiqueta": "κ₂(A)", "valor": kappa}, {"etiqueta": "Iter. Jacobi", "valor": res[0].iteraciones if res[0].convergio else "diverge"},
              {"etiqueta": "Iter. Gauss-Seidel", "valor": res[1].iteraciones}, {"etiqueta": "Iter. Grad. conjugado", "valor": res[3].iteraciones}]
    sens_info = None
    if escenario == "ESTRES":
        sens_info = sens
        claves.append({"etiqueta": "Amplificación observada ×", "valor": sens["amplificacion"]})
    elif escenario == "MAL_CONDICIONADO":
        db = np.array(datos["mal_condicionado"]["delta_b"], float)
        s1 = sensibilidad(A, b, db)
        signo = np.array([1, -1, 1, -1.0]); s5 = sensibilidad(A, b, b * signo * p["pert_pct"] / 100)
        sens_info = s1
        tabs.append(tabla("Evidencia cuantitativa del mal condicionamiento (δb diminuta vs la perturbación del ESTRÉS)",
                          ["Magnitud", "δb diminuta [±0.01]", f"Mismo ±{p['pert_pct']:g} % del ESTRÉS"],
                          [["‖δb‖₂/‖b‖₂", s1["rel_b"], s5["rel_b"]], ["‖δx‖₂/‖x*‖₂", s1["rel_x"], s5["rel_x"]],
                           ["Amplificación observada", s1["amplificacion"], s5["amplificacion"]], ["Cota κ·‖δb‖/‖b‖", s1["cota"], s5["cota"]]],
                          "La solución puede cambiar más de 1000 % con un ±5 % en los datos: coeficientes sin sentido."))
        claves += [{"etiqueta": "Amplificación observada ×", "valor": s1["amplificacion"]}, {"etiqueta": "Cambio rel. de x (±5 %)", "valor": s5["rel_x"]}]
        # un residuo pequeño no basta: GS en iteración 1000
        gs = res[1]
        if len(gs.historial) >= 1000:
            k1000 = gs.historial[999]
            tabs.append(tabla("Un residuo pequeño no basta (Gauss-Seidel en la iteración 1000)", ["Iteración", "Residuo ‖r‖∞", "Error ‖x−x*‖∞", "Error / residuo"],
                              [[1000, k1000[2], k1000[3], k1000[3] / k1000[2]]]))
    return ej, tabs, avisos, claves, res, kappa, rj, rg, sens_info


def ejecutar(escenario, p):
    datos = json.loads(RUTA.read_text(encoding="utf-8"))
    ej, tabs, graf, claves, avisos = [], [], [], [], []
    info = None
    if escenario in ("NORMAL", "ESTRES"):
        if p["D0"] >= p["D_umbral"]:
            raise ValueError("D₀ debe ser menor que el umbral.")
        if p["alfa"] == 0 and p["beta"] == 0:
            raise ValueError("α y β no pueden ser ambos cero (el indicador nunca llegaría al umbral).")
        ej, info = _ejecutar_raices(p)
        tabs += info["tab"]; graf += info["g"]
        claves += [{"etiqueta": "t* (meses)", "valor": info["t_ref"]}]
    ej_s, tabs_s, avisos, cl_s, res, kappa, rj, rg, sens = _ejecutar_sistema(escenario, p, datos)
    ej += ej_s; tabs += tabs_s; claves += cl_s
    graf += _graf_sistemas(res, logx=(escenario == "MAL_CONDICIONADO"))
    r = {m.metodo: m for m in res}
    it = lambda m: (f"{m.iteraciones}" if m.convergio else "no converge")
    num_sis = (f"Sobre el sistema 4×4 (κ₂ = {kappa:.4g}, ρ(T_J) = {rj:.4g}, ρ(T_GS) = {rg:.4g}): Jacobi {it(r['Jacobi'])}, Gauss-Seidel {it(r['Gauss-Seidel'])}, "
               f"gradiente conjugado {it(r['Gradiente conjugado'])} iteraciones; LU directo con error {fmt(r['LU'].historial[-1][3])}. ")
    if escenario == "NORMAL":
        num_sis += "La matriz es SPD y diagonalmente dominante, por lo que los cuatro métodos tienen garantía de convergencia y la comparación es justa."
    elif escenario == "ESTRES":
        num_sis += (f"Perturbar b en ±{p['pert_pct']:g} % no cambia la velocidad de los iterativos (dependen de A) sino la solución: cambio relativo de x = {sens['rel_x']:.2%} "
                    f"(amplificación observada ×{sens['amplificacion']:.2f}, por debajo de la cota teórica κ·‖δb‖/‖b‖ = {sens['cota']:.2%}).")
    else:
        num_sis += (f"A es SPD pero NO diagonalmente dominante: Jacobi {'diverge' if not r['Jacobi'].convergio else 'converge'} (ρ = {rj:.4g}), Gauss-Seidel converge muy lento (ρ = {rg:.4f}) "
                    f"y CG/LU resuelven con error ≈ {fmt(r['Gradiente conjugado'].historial[-1][3])}. El mal condicionamiento (κ₂ = {kappa:.0f}) se manifiesta en la sensibilidad: una perturbación relativa de {sens['rel_b']:.2e} en b "
                    f"produce un cambio relativo de {sens['rel_x']:.2e} en x (×{sens['amplificacion']:.0f}). Que Jacobi falle se debe a ρ > 1 (propiedad del método sobre esta matriz); la sensibilidad a los datos es del problema: son fenómenos distintos.")
    num_raiz = ""
    if info:
        rb, rn, rs = info["rb"], info["rn"], info["rs"]
        num_raiz = (f"Raíces: bisección {rb['iteraciones']}, Newton {rn['iteraciones']} y secante {rs['iteraciones']} iteraciones hasta t* = {info['t_ref']:.6f} meses (fórmula cuadrática); "
                    "Newton converge cuadráticamente, la secante con orden ≈ 1.6 y la bisección ganando ≈ 1 bit por iteración. ")
    if escenario == "MAL_CONDICIONADO":
        prob = ("El sistema representa la calibración de 4 coeficientes abstractos del modelo de deterioro. Con una matriz de κ₂ = 10⁴ los coeficientes estimados serían extremadamente sensibles al error de medición: "
                "un ±5 % en las observaciones destruiría la estimación. Variables influyentes: la precisión de los datos y el diseño del ajuste (κ). No puede inferirse ninguna condición de componentes reales; "
                "una matriz mal condicionada no es «peligrosa», es un problema matemático sensible que exigiría datos precisos o regularización.")
    else:
        t_ref = info["t_ref"]; rt = info["tab"][1]["filas"]
        sev = info["tab"][0]["filas"]
        prob = (f"Dentro del modelo sintético el indicador alcanza el umbral a los t* ≈ {t_ref:.2f} meses. Es más sensible al umbral (±{sev[2][5]:.1f} %) y a la tasa α (±{sev[0][5]:.1f} %) que a β (±{sev[1][5]:.1f} %) para variaciones de ±10 %. "
                f"Un mantenimiento retrasado 3 meses dejaría el indicador {rt[3][4]:.1f} % por encima del umbral. "
                + ("En ESTRÉS (α y β mayores) el umbral se alcanza antes y la calibración con datos ±{:g} % cambia los coeficientes en distinta proporción. ".format(p["pert_pct"]) if escenario == "ESTRES" else "")
                + "No puede inferirse el estado de ningún componente real: D(t) es un indicador abstracto y los parámetros son supuestos.")
    return {"descripcion": f"Escenario {escenario.replace('_', ' ')} del Módulo 2.", "metodos": ej, "tablas": tabs, "graficos": graf, "claves": claves,
            "conclusion_numerica": num_raiz + num_sis, "conclusion_problema": prob, "avisos": avisos}
