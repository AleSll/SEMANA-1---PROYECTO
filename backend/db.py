"""Persistencia SQLite de SIMTELE-RISK. Todo el historial se lee de la base de datos (nada depende de memoria)."""
import json
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


def conectar(ruta):
    con = sqlite3.connect(str(ruta))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def inicializar(ruta):
    """Crea las tablas si no existen (idempotente). Se puede llamar en cada arranque."""
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = conectar(ruta)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.commit()
    con.close()


def _j(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def guardar_simulacion(con, res, observaciones=None):
    """Guarda una ejecución completa: escenario, simulación, métodos, iteraciones y resúmenes. Devuelve el id."""
    params = _j(res["parametros"])
    fila = con.execute("SELECT id FROM escenario WHERE caso_id=? AND tipo=? AND parametros_json=?", (res["modulo"], res["escenario"], params)).fetchone()
    esc_id = fila["id"] if fila else con.execute("INSERT INTO escenario (caso_id, tipo, parametros_json) VALUES (?,?,?)", (res["modulo"], res["escenario"], params)).lastrowid
    ligero = dict(res)
    ligero["metodos"] = [{**{k: v for k, v in m.items() if k != "iteraciones"}, "n_iteraciones": len(m["iteraciones"])} for m in res["metodos"]]
    cur = con.execute("INSERT INTO simulacion (escenario_id, estado, observaciones, modelo_version, resultado_json) VALUES (?,?,?,?,?)",
                      (esc_id, "COMPLETADA", observaciones, res["modelo_version"], _j(ligero)))
    sim_id = cur.lastrowid
    for m in res["metodos"]:
        eid = con.execute("INSERT INTO ejecucion_metodo (simulacion_id, metodo, familia, tolerancia, paso, max_iter, convergio, tiempo_ms, mensaje) VALUES (?,?,?,?,?,?,?,?,?)",
                          (sim_id, m["metodo"], m["familia"], m["tolerancia"], m["paso"], m["max_iter"], int(m["convergio"]), m["tiempo_ms"], m.get("mensaje"))).lastrowid
        con.executemany("INSERT INTO iteracion_resultado (ejecucion_id, numero, aproximacion_json, residual, error_abs, error_rel) VALUES (?,?,?,?,?,?)",
                        [(eid, it["numero"], _j(it["aprox"]), it["residual"], it["error_abs"], it["error_rel"]) for it in m["iteraciones"]])
        rs = m["resumen"]
        con.execute("INSERT INTO resultado_resumen (ejecucion_id, referencia, valor_json, metrica_error_json, interpretacion) VALUES (?,?,?,?,?)",
                    (eid, rs["referencia"], _j(rs["valor"]), _j(rs["metricas"]), rs["interpretacion"]))
    con.commit()
    return sim_id


def recuperar_simulacion(con, sim_id):
    """Reconstruye el resultado completo (con todas las iteraciones) únicamente a partir de las tablas."""
    s = con.execute("SELECT s.*, e.tipo, e.caso_id, e.parametros_json FROM simulacion s JOIN escenario e ON e.id=s.escenario_id WHERE s.id=?", (sim_id,)).fetchone()
    if s is None:
        return None
    res = json.loads(s["resultado_json"])
    metodos = []
    for e in con.execute("SELECT * FROM ejecucion_metodo WHERE simulacion_id=? ORDER BY id", (sim_id,)).fetchall():
        its = [{"numero": r["numero"], "aprox": json.loads(r["aproximacion_json"]), "residual": r["residual"], "error_abs": r["error_abs"], "error_rel": r["error_rel"]}
               for r in con.execute("SELECT * FROM iteracion_resultado WHERE ejecucion_id=? ORDER BY numero", (e["id"],))]
        rr = con.execute("SELECT * FROM resultado_resumen WHERE ejecucion_id=?", (e["id"],)).fetchone()
        metodos.append({"metodo": e["metodo"], "familia": e["familia"], "tolerancia": e["tolerancia"], "paso": e["paso"], "max_iter": e["max_iter"],
                        "convergio": bool(e["convergio"]), "tiempo_ms": e["tiempo_ms"], "mensaje": e["mensaje"], "iteraciones": its,
                        "resumen": {"referencia": rr["referencia"], "valor": json.loads(rr["valor_json"]), "metricas": json.loads(rr["metrica_error_json"]), "interpretacion": rr["interpretacion"]}})
    res["metodos"] = metodos
    res["parametros"] = json.loads(s["parametros_json"])
    res["id"], res["fecha"], res["estado"], res["observaciones"] = s["id"], s["fecha"], s["estado"], s["observaciones"]
    return res


def historial(con, q=None, modulo=None, escenario=None, limite=200):
    sql = ("SELECT s.id, s.fecha, s.estado, s.observaciones, s.modelo_version, e.tipo AS escenario, e.caso_id AS modulo, c.nombre AS nombre_modulo, e.parametros_json, "
           "(SELECT COUNT(*) FROM ejecucion_metodo m WHERE m.simulacion_id=s.id) AS n_metodos "
           "FROM simulacion s JOIN escenario e ON e.id=s.escenario_id JOIN caso_estudio c ON c.id=e.caso_id WHERE 1=1")
    args = []
    if modulo:
        sql += " AND e.caso_id=?"; args.append(int(modulo))
    if escenario:
        sql += " AND e.tipo=?"; args.append(escenario)
    if q:
        sql += " AND (c.nombre LIKE ? OR e.tipo LIKE ? OR s.observaciones LIKE ? OR e.parametros_json LIKE ? OR CAST(s.id AS TEXT)=?)"
        like = f"%{q}%"; args += [like, like, like, like, q.strip()]
    sql += " ORDER BY s.id DESC LIMIT ?"; args.append(limite)
    return [dict(r) for r in con.execute(sql, args).fetchall()]


def eliminar(con, sim_id):
    cur = con.execute("DELETE FROM simulacion WHERE id=?", (sim_id,))
    con.commit()
    return cur.rowcount > 0
