"""Experimento de la Semana 1: tres escenarios sobre sistemas lineales (Módulo 2).

Uso (desde la raíz del repositorio):  python -m motor_numerico.experimento_semana1
"""
import json
from pathlib import Path

import numpy as np

from .errores import sensibilidad
from .sistemas_lineales import es_spd, radio_espectral, resolver_todos

RUTA = Path(__file__).resolve().parents[1] / "datos_ejemplo" / "sistemas_semana1.json"


def tabla(resultados):
    print(f"{'Método':<22}{'Iter.':>7}{'Converge':>10}{'Residuo ∞':>14}{'Error ∞':>14}")
    for r in resultados:
        err = r.historial[-1][3]
        print(f"{r.metodo:<22}{r.iteraciones:>7}{str(r.convergio):>10}{r.residuo:>14.2e}{err:>14.2e}")


def main():
    datos = json.loads(RUTA.read_text(encoding="utf-8"))

    n = datos["normal"]
    A = np.array(n["A"], float); x_ref = np.array(n["x_ref"], float); b = A @ x_ref
    print("== NORMAL ==")
    print("SPD:", es_spd(A), "| cond2 =", round(np.linalg.cond(A), 2),
          "| rho(Jacobi) =", round(radio_espectral(A, "jacobi"), 4),
          "| rho(GS) =", round(radio_espectral(A, "gauss_seidel"), 4))
    tabla(resolver_todos(A, b, x_ref, tol=n["tolerancia"]))

    e = datos["estres"]
    b_e = np.array(e["b"], float); x_e = np.linalg.solve(A, b_e)
    print("\n== ESTRÉS (b perturbado ±5 %) ==")
    tabla(resolver_todos(A, b_e, x_e, tol=e["tolerancia"]))
    s = sensibilidad(A, b, b_e - b)
    print(f"Perturbación de b: {s['rel_b']:.2%} | cambio de x: {s['rel_x']:.2%} | cota: {s['cota']:.2%}")

    m = datos["mal_condicionado"]
    Am = np.array(m["A"], float); xm = np.array(m["x_ref"], float); bm = Am @ xm
    print("\n== MAL CONDICIONADO ==")
    print("SPD:", es_spd(Am), "| cond2 =", round(np.linalg.cond(Am), 1),
          "| rho(Jacobi) =", round(radio_espectral(Am, "jacobi"), 4),
          "| rho(GS) =", round(radio_espectral(Am, "gauss_seidel"), 4))
    tabla(resolver_todos(Am, bm, xm, tol=m["tolerancia"]))
    s = sensibilidad(Am, bm, np.array(m["delta_b"], float))
    print(f"Perturbación de b: {s['rel_b']:.2e} | cambio de x: {s['rel_x']:.2e} | "
          f"amplificación ≈ {s['amplificacion']:.0f}x | cota: {s['cota']:.2e}")


if __name__ == "__main__":
    main()
