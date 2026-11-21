"""PRUEBA OBLIGATORIA: ejecutar → guardar → cerrar/reiniciar → recuperar → repetir → comparar dentro de la tolerancia."""
import os

import pytest

os.environ["SIMTELE_AUTOCREAR"] = "0"
from backend import db                      # noqa: E402
from backend.app import comparar, crear_app  # noqa: E402
from motor_numerico import modulos           # noqa: E402


@pytest.mark.parametrize("modulo,escenario", [(1, "ESTRES"), (2, "MAL_CONDICIONADO"), (3, "NORMAL"), (4, "ESTRES")])
def test_guardar_reiniciar_recuperar_repetir(tmp_path, modulo, escenario):
    ruta = tmp_path / "simtele.db"
    db.inicializar(ruta)
    res = modulos.ejecutar(modulo, escenario)
    con = db.conectar(ruta)
    sim_id = db.guardar_simulacion(con, res, "prueba")
    con.close()                                           # «cerrar la aplicación»

    db.inicializar(ruta)                                  # «reiniciar»: idempotente, no borra nada
    con = db.conectar(ruta)
    rec = db.recuperar_simulacion(con, sim_id)
    con.close()
    assert rec["parametros"] == res["parametros"]
    assert [m["metodo"] for m in rec["metodos"]] == [m["metodo"] for m in res["metodos"]]
    assert all(len(a["iteraciones"]) == len(b["iteraciones"]) for a, b in zip(rec["metodos"], res["metodos"]))
    assert len(rec["graficos"]) == len(res["graficos"]) >= 2          # los gráficos también se recuperan
    nueva = modulos.ejecutar(rec["modulo"], rec["escenario"], rec["parametros"])      # «repetir el cálculo»
    c = comparar(rec, nueva)
    assert c["coincide"] and c["max_dif_relativa"] <= 1e-9


def test_api_historial_relanzar_y_eliminar(tmp_path):
    cli = crear_app(str(tmp_path / "api.db")).test_client()
    r = cli.post("/api/simular", json={"modulo": 2, "escenario": "ESTRES", "parametros": {"pert_pct": 7}})
    assert r.status_code == 200
    sid = r.json["id"]
    assert cli.get("/api/historial?q=ESTRES").json[0]["id"] == sid
    assert cli.get("/api/historial?modulo=1").json == []
    otra = crear_app(str(tmp_path / "api.db")).test_client()            # segunda instancia = reinicio de la app
    abierta = otra.get(f"/api/simulaciones/{sid}").json
    assert abierta["parametros"]["pert_pct"] == 7
    rl = otra.post(f"/api/simulaciones/{sid}/relanzar").json
    assert rl["comparacion"]["coincide"]
    assert otra.delete(f"/api/simulaciones/{sid}").status_code == 200
    assert otra.get(f"/api/simulaciones/{sid}").status_code == 404
    assert cli.post("/api/simular", json={"modulo": 3, "escenario": "NORMAL", "parametros": {"m": -5}}).status_code == 400
