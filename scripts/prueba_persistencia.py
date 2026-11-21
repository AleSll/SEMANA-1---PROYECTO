"""Demostración de la prueba obligatoria: ejecutar → guardar → cerrar/reiniciar → recuperar → repetir → comparar.

Uso:  python -m scripts.prueba_persistencia
"""
import os
import tempfile

os.environ["SIMTELE_AUTOCREAR"] = "0"
from backend import db                       # noqa: E402
from backend.app import comparar             # noqa: E402
from motor_numerico import modulos           # noqa: E402


def main():
    ruta = os.path.join(tempfile.mkdtemp(), "simtele_demo.db")
    print(f"Base de datos: {ruta}\n")
    print("1) EJECUTAR  Módulo 2, MAL CONDICIONADO")
    res = modulos.ejecutar(2, "MAL_CONDICIONADO")
    print("   Resultado en memoria:", {k["etiqueta"]: round(k["valor"], 4) if isinstance(k["valor"], float) else k["valor"] for k in res["claves"]})
    db.inicializar(ruta)
    con = db.conectar(ruta)
    print("2) GUARDAR")
    sim_id = db.guardar_simulacion(con, res, "prueba de persistencia")
    n_it = con.execute("SELECT COUNT(*) FROM iteracion_resultado").fetchone()[0]
    print(f"   simulación #{sim_id} guardada · {len(res['metodos'])} ejecuciones de método · {n_it} filas en iteracion_resultado")
    con.close(); del res
    print("3) CERRAR / REINICIAR  (se descarta todo lo que estaba en memoria y se reabre el archivo)")
    db.inicializar(ruta)
    con = db.conectar(ruta)
    print("4) RECUPERAR  desde las tablas")
    rec = db.recuperar_simulacion(con, sim_id)
    con.close()
    print("   parámetros:", rec["parametros"])
    print("   métodos   :", [(m["metodo"], len(m["iteraciones"])) for m in rec["metodos"]])
    print("   gráficos  :", [g["titulo"] for g in rec["graficos"]])
    print("5) REPETIR el cálculo con los parámetros recuperados")
    nueva = modulos.ejecutar(rec["modulo"], rec["escenario"], rec["parametros"])
    print("6) COMPARAR")
    c = comparar(rec, nueva)
    print(f"   magnitudes comparadas: {c['magnitudes_comparadas']} · diferencia relativa máxima: {c['max_dif_relativa']:.2e} · tolerancia: {c['tolerancia']:.0e}")
    print("   RESULTADO:", "COINCIDE ✔" if c["coincide"] else "NO COINCIDE ✘")


if __name__ == "__main__":
    main()
