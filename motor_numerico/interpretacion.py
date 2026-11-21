"""Conclusiones automáticas de cada módulo y escenario: una numérica y otra del problema.

Se construyen con los números de la propia ejecución, de modo que cambian al modificar los parámetros.
"""


def _tabla(r, prefijo):
    return next(t for t in r["tablas"] if t["nombre"].startswith(prefijo))


def _g(x, d=3):
    return "—" if x is None else f"{x:.{d}g}"


def _orden(r, metodo):
    filas = [f for f in _tabla(r, "Ampliación")["filas"] if f[0] == metodo and f[3] is not None]
    return filas[-1][3] if filas else None


def interpretar(r):
    f = {(1, "NORMAL"): _m1n, (1, "ESTRES"): _m1e, (1, "MAL_CONDICIONADO"): _m1m,
         (2, "NORMAL"): _m2n, (2, "ESTRES"): _m2e, (2, "MAL_CONDICIONADO"): _m2m,
         (3, "NORMAL"): _m3n, (3, "ESTRES"): _m3e, (3, "MAL_CONDICIONADO"): _m3m,
         (4, "NORMAL"): _m4n, (4, "ESTRES"): _m4e, (4, "MAL_CONDICIONADO"): _m4m}[(r["modulo"], r["escenario"])]
    num, prob, no = f(r)
    return {"numerica": num, "problema": prob, "no_inferible": no}


def _lineal(r):
    t = _tabla(r, "Sistema lineal")
    d = {f[0]: f for f in t["filas"]}
    info = r["referencia"]["sistema_lineal"]
    return d, info


# ------------------------------------------------------------------ Módulo 1
def _m1n(r):
    p, ref = r["parametros"], r["referencia"]
    e = max(max(f[4], f[6]) for f in _tabla(r, "EDO")["filas"])
    num = (f"Con desaceleración constante RK2 y RK4 reproducen la solución analítica (error máximo {_g(e)}), porque la "
           f"solución es un polinomio de grado ≤ 2 que ambos integran exactamente; trapecio, Simpson y Romberg dan la "
           f"distancia de frenado {_g(ref['d_frenado'])} m sin error apreciable por el mismo motivo. Para ver la "
           f"diferencia entre métodos se usa la ampliación a(v) = a + k·v: el error disminuye con orden observado "
           f"≈ {_g(_orden(r, 'RK2'), 2)} en RK2 y ≈ {_g(_orden(r, 'RK4'), 2)} en RK4. Bisección, Newton y secante hallan "
           f"el instante v(t) = 0 en muy pocas iteraciones porque v(t) es lineal.")
    prob = (f"La cabina se detiene a los {_g(ref['t_det'])} s tras recorrer {_g(ref['d_frenado'])} m de frenado; con un "
            f"tiempo de reacción de {_g(p['tr'])} s la distancia total es {_g(ref['d_total'])} m, de la cual "
            f"{_g(p['v0'] * p['tr'])} m ({_g(100 * p['v0'] * p['tr'] / ref['d_total'], 3)} %) corresponden solo a la "
            f"reacción. La distancia crece con v0² y decrece con la desaceleración a: duplicar v0 la cuadruplica.")
    return num, prob, ("No permite afirmar que una cabina real frene con estos valores ni evaluar si la distancia "
                       "disponible en una estación es suficiente: los parámetros son supuestos y el modelo es de una sola dimensión.")


def _m1e(r):
    p, ref = r["parametros"], r["referencia"]
    filas = _tabla(r, "EDO")["filas"]
    e = max(max(f[4], f[6]) for f in filas)
    num = (f"Cambiar el paso de h = {_g(p['pasos'][0])} s a h = {_g(p['pasos'][-1])} s no modifica el resultado de forma apreciable "
           f"(error máximo {_g(e)}): con desaceleración constante RK2 y RK4 son exactos y el error observado es solo "
           f"redondeo. La mayor exigencia (v0 = {_g(p['v0'])} m/s, a = {_g(p['a'])} m/s²) aumenta la magnitud del "
           f"resultado, pero no empeora el condicionamiento ni la precisión del cálculo. En la ampliación a(v) el orden "
           f"observado sigue siendo ≈ {_g(_orden(r, 'RK2'), 2)} (RK2) y ≈ {_g(_orden(r, 'RK4'), 2)} (RK4).")
    prob = (f"El tiempo de detención sube a {_g(ref['t_det'])} s y la distancia total a {_g(ref['d_total'])} m "
            f"(frenado {_g(ref['d_frenado'])} m + reacción {_g(p['v0'] * p['tr'])} m). El riesgo modelado aumenta por la "
            f"mayor velocidad inicial y la menor desaceleración, no por dificultades numéricas.")
    return num, prob, ("Una situación físicamente exigente no es un problema mal condicionado. El resultado no dice si ese "
                       "frenado sería admisible en una instalación real.")


def _m1m(r):
    ref = r["referencia"]
    d = {f[0]: f for f in _tabla(r, "Raíces")["filas"]}
    nw, mod, bis = d["Newton-Raphson"], d["Newton modificado (m=2)"], d["Bisección"]
    num = (f"La raíz es doble (v(t) = 0.05 (t − {_g(r['parametros']['t_raiz'])})² no cambia de signo): Newton-Raphson pasa de "
           f"convergencia cuadrática a lineal (orden observado ≈ {_g(ref['orden_newton_observado'], 2)}, {nw[1]} iteraciones), "
           f"la bisección no puede acotar la raíz y el método de Newton modificado con m = 2 converge en {mod[1]} iteración. "
           f"Simpson y Romberg integran exactamente la cuadrática, mientras el trapecio solo mejora con orden 2 al refinar.")
    prob = (f"El instante en que la velocidad se anula es t = {_g(ref['raiz'])} s y la distancia recorrida hasta ahí es "
            f"{_g(ref['distancia'], 5)} m. La dificultad es de cálculo de la raíz, no un frenado más peligroso.")
    return num, prob, ("Este escenario es un subexperimento numérico: no representa una maniobra real ni permite concluir "
                       "nada sobre la seguridad del sistema.")


# ------------------------------------------------------------------ Módulo 2
def _m2n(r):
    ref = r["referencia"]
    d = {f[0]: f for f in _tabla(r, "Raíces")["filas"]}
    ld, info = _lineal(r)
    num = (f"Bisección necesita {d['Bisección'][1]} iteraciones, mientras Newton-Raphson y secante convergen en "
           f"{d['Newton-Raphson'][1]} y {d['Secante'][1]} con error cercano a la precisión de máquina. En el sistema lineal de calibración "
           f"(κ₂ = {_g(info['kappa2'], 3)}) Jacobi usa {ld['Jacobi'][1]} iteraciones, Gauss-Seidel {ld['Gauss-Seidel'][1]}, el gradiente "
           f"conjugado {ld['Gradiente conjugado'][1]} y LU resuelve de forma directa; ρ(Jacobi) = {_g(info['rho_jacobi'], 4)} y "
           f"ρ(GS) = {_g(info['rho_gs'], 4)} explican la diferencia.")
    prob = (f"El indicador hipotético alcanzaría el umbral de inspección a los {_g(ref['t_umbral'], 4)} meses. La derivada "
            f"dt*/dα ≈ {_g(ref['dt_dalpha'], 4)} meses por unidad indica que un deterioro inicial más rápido adelanta la inspección "
            f"de forma notable. Los coeficientes de calibración son confiables porque el sistema está bien condicionado.")
    return num, prob, "El tiempo calculado describe el modelo sintético; no es una predicción sobre un componente real."


def _m2e(r):
    ref = r["referencia"]
    d = {f[0]: f for f in _tabla(r, "Raíces")["filas"]}
    ld, info = _lineal(r)
    s = info["sensibilidad"]
    num = (f"Los tres métodos siguen convergiendo (bisección {d['Bisección'][1]} iteraciones, Newton {d['Newton-Raphson'][1]}, "
           f"secante {d['Secante'][1]}), de modo que la exigencia del escenario no degrada el cálculo. Al perturbar el vector "
           f"de observaciones un {_g(100 * s['rel_b'], 3)} % la solución cambia {_g(100 * s['rel_x'], 3)} %, por debajo de la "
           f"cota κ·‖δb‖/‖b‖ = {_g(100 * s['cota'], 3)} %.")
    prob = (f"Con mantenimiento retrasado (α y β mayores) el umbral se alcanza a los {_g(ref['t_umbral'], 4)} meses, "
            f"{_g(ref['adelanto_respecto_normal'], 3)} meses antes que en el caso NORMAL ({_g(ref['t_umbral_normal'], 4)}). "
            f"El retraso del mantenimiento reduce el margen de inspección.")
    return num, prob, "No indica cuándo ni con qué frecuencia debe inspeccionarse un componente real."


def _m2m(r):
    ref = r["referencia"]
    d = {f[0]: f for f in _tabla(r, "Raíces")["filas"]}
    ld, info = _lineal(r)
    s = info["sensibilidad"]
    num = (f"Raíz doble: Newton-Raphson ({d['Newton-Raphson'][1]} iter.) y secante ({d['Secante'][1]} iter.) pierden velocidad, la bisección no "
           f"aplica y Newton modificado converge en {d['Newton modificado (m=2)'][1]} {'iteración' if d['Newton modificado (m=2)'][1] == 1 else 'iteraciones'}. Subir el umbral {_g(r['parametros']['delta_umbral'])} "
           f"desplaza la raíz ±{_g(ref['desplazamiento'], 3)} meses (amplificación {_g(ref['amplificacion_dt_du'], 4)} meses por unidad). En "
           f"el sistema lineal κ₂ = {_g(info['kappa2'], 5)}: Jacobi {'converge' if ld['Jacobi'][2] else 'diverge'} "
           f"(ρ = {_g(info['rho_jacobi'], 4)}), Gauss-Seidel necesita {ld['Gauss-Seidel'][1]} iteraciones (ρ = {_g(info['rho_gs'], 4)}) y "
           f"el gradiente conjugado {ld['Gradiente conjugado'][1]}. Una perturbación de {_g(s['rel_b'], 3)} en b se amplifica "
           f"×{_g(s['amplificacion'], 3)}.")
    prob = ("Si el umbral coincide con el mínimo de la curva de deterioro, un cambio mínimo del umbral o de los datos mueve "
            "mucho el instante estimado de inspección; calibrar con datos que den un sistema mal condicionado hace poco "
            "confiables los coeficientes.")
    return num, prob, "Es un subexperimento numérico: no representa un componente real ni una política de mantenimiento."


# ------------------------------------------------------------------ Módulo 3
def _m3n(r):
    ref = r["referencia"]
    filas = _tabla(r, "Error máximo")["filas"]
    e2 = next(f for f in filas if f[0] == "RK2" and f[1] == 0.05)[2]; e4 = next(f for f in filas if f[0] == "RK4" and f[1] == 0.05)[2]
    o2 = [f for f in filas if f[0] == "RK2" and f[3]][-1][3]; o4 = [f for f in filas if f[0] == "RK4" and f[3]][-1][3]
    num = (f"Con h = 0.05 s el error máximo es {_g(e2)} m en RK2 y {_g(e4)} m en RK4; el orden observado ≈ {_g(o2, 2)} y "
           f"≈ {_g(o4, 2)} confirma los órdenes 2 y 4. La integral de x(t)² (referencia {_g(ref['integral_x2'], 5)}) se aproxima "
           f"mejor con RK4; Romberg converge al refinar las extrapolaciones de Richardson.")
    prob = (f"La vibración libre subamortiguada (ζ = {_g(ref['zeta'])}, ω_d = {_g(ref['omega_d'], 4)} rad/s) decae sin superar la "
            f"amplitud inicial de {_g(r['parametros']['x0'])} m; la magnitud acumulada ∫x² dt mide la energía de oscilación "
            f"disipada por el amortiguamiento.")
    return num, prob, "Un oscilador de un grado de libertad no reproduce la dinámica completa de una cabina ni del cable."


def _m3e(r):
    ref = r["referencia"]
    filas = _tabla(r, "Respuesta forzada")["filas"]
    g = {(f[0], f[1]): f for f in filas}
    hs = sorted({f[1] for f in filas})
    a, b = hs[0], hs[-1]
    num = (f"Con h = {a} s RK4 comete un error máximo de {_g(g[('RK4', a)][2])} m frente a {_g(g[('RK2', a)][2])} m de RK2; "
           f"con h = {b} s el error de RK2 sube a {_g(g[('RK2', b)][2])} m y el de RK4 a {_g(g[('RK4', b)][2])} m. "
           f"El paso grande distorsiona la amplitud y la magnitud integrada. La referencia (RK4 con h = 0.001 s) se verificó "
           f"con h/2 (diferencia {_g(ref['chequeo_referencia'])} m).")
    prob = (f"En resonancia la amplitud estacionaria teórica es {_g(ref['amplitud_estacionaria'])} m (RK4 con h = {a} s da "
            f"{_g(g[('RK4', a)][4])} m), mucho mayor que la oscilación libre; el amortiguamiento limita pero no elimina la "
            f"respuesta cuando la frecuencia de la fuerza coincide con la natural.")
    return num, prob, "No permite afirmar que el viento real excite una frecuencia así ni calcular esfuerzos sobre una estructura real."


def _m3m(r):
    filas = _tabla(r, "Amortiguamiento")["filas"]
    a = filas[0]
    crit = next((f for f in filas if f[1] >= 1), None)
    num = (f"Para c = {_g(a[0])} (ζ = {_g(a[1], 5)}) la constante C₂ = {_g(a[4], 4)} es {_g(a[4] / abs(a[3]) if a[3] else 0, 3)} veces mayor "
           f"que C₁ y el indicador ζ²/(1−ζ²) = {_g(a[5], 4)} muestra la amplificación de la fórmula al acercarse a ω_d → 0. "
           + (f"En c = {_g(crit[0])} la fórmula subamortiguada divide por cero y se usa la solución crítica; RK4 funciona en ambos casos "
              f"(error {_g(a[6])})." if crit else "RK4 funciona sin dificultad."))
    prob = ("Cerca del amortiguamiento crítico la respuesta deja de oscilar y vuelve al reposo sin cruzar el equilibrio; el "
            "problema es la fórmula analítica, no el comportamiento físico, que cambia de forma continua.")
    return num, prob, "Es un subexperimento numérico sobre la sensibilidad de una fórmula, no una condición de operación."


# ------------------------------------------------------------------ Módulo 4
def _err4(r):
    t = r["tablas"][0]
    return {f[0]: f[-1] for f in t["filas"]}


def _m4n(r):
    e = _err4(r)
    cruce = _tabla(r, "Cruce")["filas"]
    num = (f"Con {r['parametros']['n_nodos']} nodos sin ruido, Lagrange y Newton producen el mismo polinomio (error máximo "
           f"{_g(e['Lagrange'])}) y el spline cúbico tiene error {_g(e['Spline cúbico'])} en los puntos ocultos. La bisección sobre la curva "
           f"interpolada estima el cruce de y = 0.5 en t = {_g(cruce[2][1], 5)} (spline) frente a 0.5236 real.")
    prob = ("Con muestras regulares y limpias es posible reconstruir los registros faltantes con error del orden de "
            f"{_g(max(e.values()), 2)}, lo que da confianza dentro del rango de los nodos.")
    return num, prob, "La confiabilidad vale para una señal suave y sintética; no se puede extrapolar fuera del rango ni a datos reales con fallas."


def _m4e(r):
    filas = _tabla(r, "Error en los puntos ocultos")["filas"]
    ns = sorted({f[0] for f in filas})

    def mx(n, limpio, met):
        return next(f[-1] for f in filas if f[0] == n and f[2] == met and f[1].startswith("sin") == limpio)
    n0, n1 = ns[0], ns[-1]
    sig = r["parametros"]["sigma"]
    num = (f"Sin ruido, más nodos reducen mucho el error de Lagrange ({_g(mx(n0, True, 'Lagrange'))} con {n0} nodos y "
           f"{_g(mx(n1, True, 'Lagrange'))} con {n1}). Con ruido σ = {sig}, en cambio, el error con {n1} nodos es "
           f"{_g(mx(n1, False, 'Lagrange'))} (Lagrange) y {_g(mx(n1, False, 'Spline cúbico'))} (spline), mucho mayor que sin ruido: "
           f"el ruido de los datos domina sobre el error de interpolación y los nodos adicionales no garantizan mejora.")
    prob = ("Para registros con ruido, agregar más nodos no asegura una mejor reconstrucción: el error queda fijado por el "
            "nivel del ruido, por lo que conviene suavizar o ajustar en lugar de interpolar exactamente.")
    return num, prob, "Con una sola realización del ruido (semilla fija) no se puede inferir el comportamiento promedio."


def _m4m(r):
    e = _err4(r)
    ev = {f[0]: f[1] for f in r["tablas"][1]["filas"]}
    k = [v for kk, v in ev.items() if "kappa(Vandermonde) con 20" in kk][0]
    leb = [v for kk, v in ev.items() if "Lebesgue, 20 nodos equi" in kk][0]
    lebc = [v for kk, v in ev.items() if "Chebyshev" in kk and "Lebesgue" in kk][0]
    num = (f"Con {r['parametros']['n_nodos']} nodos equiespaciados y ruido {r['parametros']['sigma']}, Lagrange/Newton cometen un error "
           f"máximo de {_g(e['Lagrange'])} en los extremos frente a {_g(e['Spline cúbico'])} del spline. κ(Vandermonde) = {_g(k, 3)}, "
           f"constante de Lebesgue {_g(leb, 4)} (equiespaciados) frente a {_g(lebc, 3)} (Chebyshev): el polinomio de grado alto "
           f"amplifica el ruido; no es un fallo de convergencia.")
    prob = ("Un polinomio de alto grado no sirve para reconstruir registros con ruido: oscila en los extremos del intervalo. "
            "El spline cúbico es más estable y confiable en esta situación.")
    return num, prob, "No permite decidir cuántos nodos usaría un sensor real; solo muestra la inestabilidad de la interpolación polinómica."
