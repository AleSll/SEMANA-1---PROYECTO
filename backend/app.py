"""API Flask de SIMTELE-RISK (uso local o en un servidor).

    python -m backend.app            # http://127.0.0.1:5000/
La base de datos es un archivo SQLite (por defecto simtele.db; cambiar con la variable SIMTELE_DB).
"""
import os
import sys
from pathlib import Path

if __package__ in (None, ""):                      # ejecutado como «python backend/app.py»
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from backend.servicio import RAIZ, Servicio, conectar
else:
    from .servicio import RAIZ, Servicio, conectar

from flask import Flask, jsonify, redirect, request, send_from_directory


def crear_app(ruta_bd=None):
    app = Flask(__name__, static_folder=None)
    servicio = Servicio(conectar(ruta_bd or os.environ.get("SIMTELE_DB", "simtele.db")))

    @app.get("/api/salud")
    def salud():
        return jsonify({"ok": True, "modo": "flask"})

    @app.post("/api/<accion>")
    def api(accion):
        resultado = servicio.llamar(accion, request.get_json(silent=True) or {})
        return jsonify(resultado), (400 if "error" in resultado else 200)

    @app.get("/")
    def inicio():
        return redirect("/frontend/")

    @app.get("/frontend/")
    def indice():
        return send_from_directory(RAIZ / "frontend", "index.html")

    @app.get("/frontend/<path:ruta>")
    def estatico(ruta):
        return send_from_directory(RAIZ / "frontend", ruta)

    app.servicio = servicio
    return app


if __name__ == "__main__":
    crear_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
