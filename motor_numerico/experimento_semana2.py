"""Ejecuta los módulos y escenarios de la Semana 2 y muestra sus tablas.

Uso (desde la raíz del repositorio):
    python -m motor_numerico.experimento_semana2            # los 12 casos
    python -m motor_numerico.experimento_semana2 3 ESTRES   # un módulo y escenario
"""
import sys

from .casos import ESCENARIOS, ejecutar


def _fmt(x):
    if isinstance(x, float):
        return f"{x:.4g}"
    return "" if x is None else str(x)


def mostrar(resultado):
    print(f"\n=== Módulo {resultado['modulo']} · {resultado['escenario']} ===")
    for t in resultado["tablas"]:
        print(f"\n{t['nombre']}")
        print(" | ".join(t["columnas"]))
        for fila in t["filas"]:
            print(" | ".join(_fmt(v) for v in fila))


def main(argv):
    if len(argv) >= 2:
        mostrar(ejecutar(int(argv[0]), argv[1].upper()))
        return
    for m in (1, 2, 3, 4):
        for e in ESCENARIOS:
            mostrar(ejecutar(m, e))


if __name__ == "__main__":
    main(sys.argv[1:])
