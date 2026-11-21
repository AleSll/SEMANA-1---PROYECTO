"""Servicio de SIMTELE-RISK: ejecuta simulaciones y las guarda/recupera en SQLite.

La misma lógica se usa desde Flask (backend/app.py) y desde el navegador con Pyodide
(frontend/transporte.js), de modo que el cálculo y el guardado son idénticos en ambos casos.
"""
import json
import math
import sqlite3
import threading
from pathlib import Path

from motor_numerico.casos import ESCENARIOS, PARAMETROS, ejecutar, serializable
from motor_numerico.interpretacion import interpretar

from .validacion import validar

RAIZ = Path(__file__).resolve().parents[1]
RUTA_SCHEMA = RAIZ / "db" / "schema.sql"
NOMBRES = {1: "Detención de emergencia", 2: "Deterioro y mantenimiento",
           3: "Oscilaciones por viento", 4: "Reconstrucción de sensores"}
MODULO_DE = {v: k for k, v in NOMBRES.items()}
RESUMEN_METODO = "Resultado completo del módulo"     # fila de ejecucion_metodo que guarda el resultado completo


def conectar(ruta=":memory:"):
    con = sqlite3.connect(ruta, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    existe = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='caso_estudio'").fetchone()
    if not existe:
        con.executescript(RUTA_SCHEMA.read_text(encoding="utf-8"))
        con.commit()
    return con


def _db(x):
    """Valores finitos para columnas REAL; None si no es un número finito."""
    return float(x) if isinstance(x, (int, float)) and math.isfinite(x) else None


def _comparar(a, b, tol, acumulado):
    """Compara dos estructuras JSON; acumula el número de valores numéricos y la mayor diferencia relativa."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            acumulado["estructura"] = False
            return
        for k in a:
            _comparar(a[k], b[k], tol, acumulado)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            acumulado["estructura"] = False
            return
        for x, y in zip(a, b):
            _comparar(x, y, tol, acumulado)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        acumulado["n"] += 1
        d = abs(a - b) / max(1.0, abs(a), abs(b))
        acumulado["max"] = max(acumulado["max"], d)
    elif a != b:
        acumulado["estructura"] = False


class Servicio:
    def __init__(self, con):
        self.con = con
        self.lock = threading.RLock()

    # ------------------------------------------------------------ información
    def parametros(self):
        return {"nombres": {str(k): v for k, v in NOMBRES.items()},
                "parametros": {str(m): {e: p for e, p in d.items()} for m, d in PARAMETROS.items()}}

    def estado(self):
        n = self.con.execute("SELECT COUNT(*) FROM simulacion").fetchone()[0]
        return {"ok": True, "simulaciones": n}

    # ------------------------------------------------------------ simular
    def simular(self, modulo, escenario, parametros=None, guardar=True, equipo=None):
        errores = validar(modulo, escenario, parametros)
        if errores:
            raise ValueError("; ".join(errores))
        res = ejecutar(modulo, escenario, parametros)
        res["interpretacion"] = interpretar(res)
        if guardar:
            res["id"] = self._guardar(res, equipo)
        return serializable(res)

    def _guardar(self, res, equipo=None):
        with self.lock:
            con = self.con
            try:
                caso_id = con.execute("SELECT id FROM caso_estudio WHERE nombre = ?",
                                      (NOMBRES[res["modulo"]],)).fetchone()[0]
                pj = json.dumps(res["parametros"], sort_keys=True, ensure_ascii=False)
                fila = con.execute("SELECT id FROM escenario WHERE caso_id = ? AND tipo = ? AND parametros_json = ?",
                                   (caso_id, res["escenario"], pj)).fetchone()
                esc_id = fila[0] if fila else con.execute(
                    "INSERT INTO escenario (caso_id, tipo, parametros_json, fuente_datos) VALUES (?,?,?,'sintetico')",
                    (caso_id, res["escenario"], pj)).lastrowid
                sim_id = con.execute(
                    "INSERT INTO simulacion (escenario_id, estado, observaciones) VALUES (?, 'COMPLETADA', ?)",
                    (esc_id, f"equipo: {equipo}" if equipo else None)).lastrowid
                for e in res["ejecuciones"]:
                    ej_id = con.execute(
                        "INSERT INTO ejecucion_metodo (simulacion_id, metodo, tolerancia, paso, max_iter, convergio, tiempo_ms)"
                        " VALUES (?,?,?,?,?,?,?)",
                        (sim_id, e["metodo"], _db(e["tolerancia"]), _db(e["paso"]), e["max_iter"],
                         1 if e["convergio"] else 0, _db(e["tiempo_ms"]))).lastrowid
                    con.executemany(
                        "INSERT INTO iteracion_resultado (ejecucion_id, numero, aproximacion_json, residual, error_abs, error_rel)"
                        " VALUES (?,?,?,?,?,?)",
                        [(ej_id, it["numero"], json.dumps(serializable(it["aproximacion"])), _db(it["residual"]),
                          _db(it["error_abs"]), _db(it["error_rel"])) for it in e["iteraciones"]])
                    ultima = e["iteraciones"][-1] if e["iteraciones"] else None
                    con.execute(
                        "INSERT INTO resultado_resumen (ejecucion_id, referencia, valor_json, metrica_error_json, interpretacion)"
                        " VALUES (?,?,?,?,?)",
                        (ej_id, e["referencia"],
                         json.dumps(serializable(ultima["aproximacion"])) if ultima else None,
                         json.dumps(serializable({"error_abs": ultima["error_abs"], "residual": ultima["residual"],
                                                  "error_rel": ultima["error_rel"]})) if ultima else None,
                         f"{e['metodo']}: {'convergió' if e['convergio'] else 'no convergió'} "
                         f"en {len(e['iteraciones'])} registros"))
                completo = {k: res[k] for k in ("parametros", "referencia", "tablas", "graficos", "interpretacion")}
                ej_id = con.execute(
                    "INSERT INTO ejecucion_metodo (simulacion_id, metodo, convergio) VALUES (?,?,1)",
                    (sim_id, RESUMEN_METODO)).lastrowid
                con.execute(
                    "INSERT INTO resultado_resumen (ejecucion_id, referencia, valor_json, interpretacion) VALUES (?,?,?,?)",
                    (ej_id, "resultado completo (tablas, gráficos y referencias)",
                     json.dumps(serializable(completo), ensure_ascii=False), res["interpretacion"]["numerica"]))
                con.commit()
                return sim_id
            except Exception:
                con.rollback()
                raise

    # ------------------------------------------------------------ historial
    def listar(self, q=None, modulo=None, escenario=None, limite=200):
        sql = ("SELECT s.id, s.fecha, s.estado, s.observaciones, e.tipo AS escenario, e.parametros_json, c.nombre AS caso,"
               " (SELECT COUNT(*) FROM ejecucion_metodo m WHERE m.simulacion_id = s.id AND m.metodo <> ?) AS metodos"
               " FROM simulacion s JOIN escenario e ON e.id = s.escenario_id JOIN caso_estudio c ON c.id = e.caso_id")
        cond, args = [], [RESUMEN_METODO]
        if modulo:
            cond.append("c.nombre = ?"); args.append(NOMBRES[int(modulo)])
        if escenario:
            cond.append("e.tipo = ?"); args.append(escenario)
        if q:
            like = f"%{q}%"
            cond.append("(c.nombre LIKE ? OR e.tipo LIKE ? OR s.fecha LIKE ? OR IFNULL(s.observaciones,'') LIKE ?"
                        " OR CAST(s.id AS TEXT) = ? OR e.parametros_json LIKE ?)")
            args += [like, like, like, like, str(q).lstrip("#"), like]
        if cond:
            sql += " WHERE " + " AND ".join(cond)
        sql += " ORDER BY s.id DESC LIMIT ?"
        args.append(int(limite))
        with self.lock:
            filas = self.con.execute(sql, args).fetchall()
        return {"simulaciones": [{"id": f["id"], "fecha": f["fecha"], "estado": f["estado"], "caso": f["caso"],
                                  "modulo": MODULO_DE[f["caso"]], "escenario": f["escenario"],
                                  "metodos": f["metodos"], "observaciones": f["observaciones"]} for f in filas]}

    def abrir(self, id):
        with self.lock:
            cab = self.con.execute(
                "SELECT s.id, s.fecha, s.estado, s.observaciones, e.tipo, e.parametros_json, c.nombre"
                " FROM simulacion s JOIN escenario e ON e.id = s.escenario_id JOIN caso_estudio c ON c.id = e.caso_id"
                " WHERE s.id = ?", (int(id),)).fetchone()
            if cab is None:
                raise KeyError(f"No existe la simulación #{id}")
            completo = self.con.execute(
                "SELECT r.valor_json FROM resultado_resumen r JOIN ejecucion_metodo m ON m.id = r.ejecucion_id"
                " WHERE m.simulacion_id = ? AND m.metodo = ?", (int(id), RESUMEN_METODO)).fetchone()
            metodos = self.con.execute(
                "SELECT m.id, m.metodo, m.tolerancia, m.paso, m.max_iter, m.convergio,"
                " (SELECT COUNT(*) FROM iteracion_resultado i WHERE i.ejecucion_id = m.id) AS iteraciones,"
                " r.referencia, r.metrica_error_json FROM ejecucion_metodo m"
                " LEFT JOIN resultado_resumen r ON r.ejecucion_id = m.id"
                " WHERE m.simulacion_id = ? AND m.metodo <> ? ORDER BY m.id", (int(id), RESUMEN_METODO)).fetchall()
        res = json.loads(completo[0]) if completo else {}
        res.update({"id": cab["id"], "fecha": cab["fecha"], "estado": cab["estado"], "modulo": MODULO_DE[cab["nombre"]],
                    "escenario": cab["tipo"], "parametros": json.loads(cab["parametros_json"]),
                    "observaciones": cab["observaciones"],
                    "metodos": [{"id": m["id"], "metodo": m["metodo"], "tolerancia": m["tolerancia"], "paso": m["paso"],
                                 "max_iter": m["max_iter"], "convergio": bool(m["convergio"]),
                                 "iteraciones": m["iteraciones"], "referencia": m["referencia"],
                                 "metrica_error": json.loads(m["metrica_error_json"]) if m["metrica_error_json"] else None}
                                for m in metodos]})
        return res

    def iteraciones(self, ejecucion_id, limite=500):
        with self.lock:
            filas = self.con.execute(
                "SELECT numero, aproximacion_json, residual, error_abs, error_rel FROM iteracion_resultado"
                " WHERE ejecucion_id = ? ORDER BY numero LIMIT ?", (int(ejecucion_id), int(limite))).fetchall()
            total = self.con.execute("SELECT COUNT(*) FROM iteracion_resultado WHERE ejecucion_id = ?",
                                     (int(ejecucion_id),)).fetchone()[0]
        return {"total": total, "iteraciones": [{"numero": f["numero"], "aproximacion": json.loads(f["aproximacion_json"]),
                                                 "residual": f["residual"], "error_abs": f["error_abs"],
                                                 "error_rel": f["error_rel"]} for f in filas]}

    def relanzar(self, id, tolerancia=1e-9, guardar=True):
        """Recupera una simulación guardada, repite el cálculo con sus parámetros y compara los resultados."""
        guardada = self.abrir(id)
        nueva = self.simular(guardada["modulo"], guardada["escenario"], guardada["parametros"], guardar=guardar)
        acum = {"n": 0, "max": 0.0, "estructura": True}
        _comparar(guardada["tablas"], nueva["tablas"], tolerancia, acum)
        _comparar(guardada["referencia"], nueva["referencia"], tolerancia, acum)
        coincide = acum["estructura"] and acum["max"] <= tolerancia
        return {"origen": int(id), "nueva_id": nueva.get("id"), "coincide": bool(coincide),
                "valores_comparados": acum["n"], "max_dif_relativa": acum["max"], "tolerancia": tolerancia,
                "estructura_igual": acum["estructura"], "resultado": nueva}

    def eliminar(self, id):
        with self.lock:
            n = self.con.execute("DELETE FROM simulacion WHERE id = ?", (int(id),)).rowcount
            self.con.commit()
        if not n:
            raise KeyError(f"No existe la simulación #{id}")
        return {"eliminada": int(id)}

    # ------------------------------------------------------------ despacho único (Flask y Pyodide)
    def llamar(self, accion, datos=None):
        datos = datos or {}
        try:
            if accion == "parametros":
                return self.parametros()
            if accion == "estado":
                return self.estado()
            if accion == "simular":
                return self.simular(int(datos["modulo"]), datos["escenario"], datos.get("parametros"),
                                    bool(datos.get("guardar", True)), datos.get("equipo"))
            if accion == "listar":
                return self.listar(datos.get("q"), datos.get("modulo"), datos.get("escenario"))
            if accion == "abrir":
                return serializable(self.abrir(datos["id"]))
            if accion == "iteraciones":
                return serializable(self.iteraciones(datos["ejecucion_id"]))
            if accion == "relanzar":
                return serializable(self.relanzar(datos["id"], datos.get("tolerancia", 1e-9), bool(datos.get("guardar", True))))
            if accion == "eliminar":
                return self.eliminar(datos["id"])
            return {"error": f"Acción desconocida: {accion}"}
        except (ValueError, KeyError, TypeError) as e:
            return {"error": str(e).strip("'\"")}

    def llamar_json(self, accion, texto="{}"):
        return json.dumps(self.llamar(accion, json.loads(texto or "{}")), ensure_ascii=False, allow_nan=False)
