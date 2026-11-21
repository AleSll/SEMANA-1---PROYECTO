"""API web de SIMTELE-RISK (Flask). Valida entradas, coordina el motor numérico y persiste en SQLite.

Ejecución local:   python -m backend.app        (abre http://127.0.0.1:5000)
Producción:        gunicorn wsgi:app
Variable de entorno SIMTELE_DB: ruta del archivo SQLite (por defecto data/simtele.db).
"""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from motor_numerico import modulos
from motor_numerico.modulos.comun import ErrorValidacion, aplanar_valores

from . import db

RAIZ = Path(__file__).resolve().parents[1]
TOL_COMPARACION = 1e-9


def crear_app(ruta_db=None):
    app = Flask(__name__, static_folder=None)
    ruta = ruta_db or os.environ.get("SIMTELE_DB") or str(RAIZ / "data" / "simtele.db")
    db.inicializar(ruta)
    app.config["RUTA_DB"] = ruta
    cache_comparacion = {}

    def con():
        return db.conectar(app.config["RUTA_DB"])

    @app.errorhandler(ErrorValidacion)
    def _validacion(e):
        return jsonify({"error": "Parámetros inválidos", "detalles": e.mensajes}), 400

    @app.get("/")
    def inicio():
        return send_from_directory(RAIZ / "frontend", "index.html")

    @app.get("/api/modulos")
    def api_modulos():
        return jsonify({"modulos": modulos.catalogo(), "escenarios": modulos.NOMBRE_ESCENARIO, "modelo_version": modulos.MODELO_VERSION})

    @app.post("/api/simular")
    def api_simular():
        d = request.get_json(silent=True) or {}
        res = modulos.ejecutar(d.get("modulo"), d.get("escenario"), d.get("parametros"))
        if d.get("guardar", True):
            c = con()
            try:
                res["id"] = db.guardar_simulacion(c, res, d.get("observaciones"))
            finally:
                c.close()
        return jsonify(res)

    @app.get("/api/historial")
    def api_historial():
        c = con()
        try:
            return jsonify(db.historial(c, request.args.get("q"), request.args.get("modulo"), request.args.get("escenario")))
        finally:
            c.close()

    @app.get("/api/simulaciones/<int:sim_id>")
    def api_abrir(sim_id):
        c = con()
        try:
            res = db.recuperar_simulacion(c, sim_id)
        finally:
            c.close()
        if res is None:
            return jsonify({"error": "Simulación no encontrada"}), 404
        return jsonify(res)

    @app.post("/api/simulaciones/<int:sim_id>/relanzar")
    def api_relanzar(sim_id):
        c = con()
        try:
            guardada = db.recuperar_simulacion(c, sim_id)
            if guardada is None:
                return jsonify({"error": "Simulación no encontrada"}), 404
            nueva = modulos.ejecutar(guardada["modulo"], guardada["escenario"], guardada["parametros"])
            cmp_ = comparar(guardada, nueva)
            nueva["id"] = db.guardar_simulacion(c, nueva, f"Relanzada desde la simulación #{sim_id}")
        finally:
            c.close()
        return jsonify({"resultado": nueva, "comparacion": cmp_, "original_id": sim_id})

    @app.delete("/api/simulaciones/<int:sim_id>")
    def api_eliminar(sim_id):
        c = con()
        try:
            ok = db.eliminar(c, sim_id)
        finally:
            c.close()
        return jsonify({"eliminada": ok}), (200 if ok else 404)

    @app.get("/api/comparacion")
    def api_comparacion():
        if not cache_comparacion:
            for i in modulos.MODULOS:
                for e in modulos.ESCENARIOS:
                    r = modulos.ejecutar(i, e)
                    cache_comparacion[f"{i}|{e}"] = {"modulo": i, "nombre": r["nombre_modulo"], "escenario": e, "claves": r["claves"], "avisos": r["avisos"],
                                                     "metodos": [{"metodo": m["metodo"], "familia": m["familia"], "convergio": m["convergio"], "n": len(m["iteraciones"])} for m in r["metodos"]]}
        return jsonify(list(cache_comparacion.values()))

    @app.get("/api/salud")
    def salud():
        return jsonify({"ok": True, "modelo_version": modulos.MODELO_VERSION})

    return app


def comparar(guardada, nueva, tol=TOL_COMPARACION):
    """Compara una simulación guardada con su relanzamiento: máxima diferencia absoluta/relativa de todas las métricas."""
    a, b = aplanar_valores(guardada), aplanar_valores(nueva)
    claves = sorted(set(a) | set(b))
    peor, detalle, faltan = 0.0, [], []
    for k in claves:
        if k not in a or k not in b:
            faltan.append(k)
            continue
        dif = abs(a[k] - b[k]) / max(1.0, abs(a[k]))
        if dif > peor:
            peor = dif
        if dif > tol:
            detalle.append({"magnitud": k, "guardado": a[k], "nuevo": b[k], "dif_relativa": dif})
    return {"coincide": peor <= tol and not faltan, "max_dif_relativa": peor, "tolerancia": tol, "magnitudes_comparadas": len(claves) - len(faltan), "fuera_de_tolerancia": detalle, "faltantes": faltan}


app = crear_app() if os.environ.get("SIMTELE_AUTOCREAR", "1") == "1" else None

if __name__ == "__main__":
    (app or crear_app()).run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)
