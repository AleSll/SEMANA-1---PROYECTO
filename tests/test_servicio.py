import json

import pytest

from backend.servicio import RESUMEN_METODO, Servicio, conectar
from backend.validacion import validar
from motor_numerico.casos import ESCENARIOS


@pytest.fixture
def srv(tmp_path):
    return Servicio(conectar(str(tmp_path / "prueba.db")))


def test_guardar_y_recuperar_tras_reiniciar(tmp_path):
    ruta = str(tmp_path / "persistente.db")
    s1 = Servicio(conectar(ruta))
    original = s1.simular(2, "ESTRES", {"alpha": 0.03}, guardar=True)
    sim_id = original["id"]
    s1.con.close()                                        # "cerrar la aplicación"
    s2 = Servicio(conectar(ruta))                         # "reiniciar"
    guardada = s2.abrir(sim_id)
    assert guardada["parametros"]["alpha"] == 0.03 and guardada["modulo"] == 2
    assert guardada["tablas"] == original["tablas"] and len(guardada["graficos"]) >= 2
    assert guardada["interpretacion"]["numerica"] and guardada["interpretacion"]["problema"]
    assert all(m["iteraciones"] > 0 for m in guardada["metodos"] if m["metodo"] != RESUMEN_METODO)
    comp = s2.relanzar(sim_id)
    assert comp["coincide"] and comp["valores_comparados"] > 30 and comp["max_dif_relativa"] <= 1e-9


def test_tablas_de_la_base_de_datos_se_llenan(srv):
    r = srv.simular(1, "NORMAL")
    c = srv.con
    assert c.execute("SELECT COUNT(*) FROM simulacion").fetchone()[0] == 1
    n_it = c.execute("SELECT COUNT(*) FROM iteracion_resultado").fetchone()[0]
    n_res = c.execute("SELECT COUNT(*) FROM resultado_resumen").fetchone()[0]
    assert n_it > 100 and n_res == c.execute("SELECT COUNT(*) FROM ejecucion_metodo").fetchone()[0]
    assert c.execute("SELECT estado FROM simulacion").fetchone()[0] == "COMPLETADA"
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []


def test_escenario_se_reutiliza_con_los_mismos_parametros(srv):
    srv.simular(4, "NORMAL"); srv.simular(4, "NORMAL"); srv.simular(4, "NORMAL", {"n_nodos": 11})
    assert srv.con.execute("SELECT COUNT(*) FROM escenario").fetchone()[0] == 2
    assert srv.con.execute("SELECT COUNT(*) FROM simulacion").fetchone()[0] == 3


def test_listar_buscar_y_eliminar(srv):
    a = srv.simular(1, "NORMAL")["id"]; b = srv.simular(3, "ESTRES")["id"]
    assert [s["id"] for s in srv.listar()["simulaciones"]] == [b, a]
    assert [s["id"] for s in srv.listar(q="Oscilaciones")["simulaciones"]] == [b]
    assert [s["id"] for s in srv.listar(escenario="NORMAL")["simulaciones"]] == [a]
    assert [s["id"] for s in srv.listar(q=f"#{a}")["simulaciones"]] == [a]
    assert srv.eliminar(a) == {"eliminada": a}
    assert srv.con.execute("SELECT COUNT(*) FROM iteracion_resultado WHERE ejecucion_id NOT IN (SELECT id FROM ejecucion_metodo)").fetchone()[0] == 0
    assert "error" in srv.llamar("abrir", {"id": a})


def test_no_guardar_no_escribe(srv):
    r = srv.simular(2, "NORMAL", guardar=False)
    assert "id" not in r and srv.estado()["simulaciones"] == 0


def test_relanzar_con_parametros_modificados_detecta_diferencia(srv):
    sim = srv.simular(2, "NORMAL")["id"]
    srv.con.execute("UPDATE escenario SET parametros_json = ?", (json.dumps({"D0": 0.1, "alpha": 0.02, "beta": 0.0005, "umbral": 0.4}),))
    srv.con.commit()
    assert srv.relanzar(sim)["coincide"] is False


def test_llamar_json_y_errores(srv):
    out = json.loads(srv.llamar_json("simular", json.dumps({"modulo": 3, "escenario": "NORMAL", "parametros": {"c": 5000}})))
    assert "subamortiguado" in out["error"]
    assert "error" in srv.llamar("accion_inexistente")
    assert json.loads(srv.llamar_json("parametros"))["nombres"]["4"] == "Reconstrucción de sensores"


def test_validacion():
    assert validar(1, "NORMAL", {"v0": -1}) and validar(1, "NORMAL", {"xx": 1}) and validar(9, "NORMAL", {})
    assert validar(2, "NORMAL", {"umbral": 0.05}) and validar(4, "NORMAL", {"n_nodos": 2.5})
    assert validar(3, "ESTRES", {"pasos": [0.7]}) and not validar(3, "ESTRES", {"pasos": [0.2, 0.25]})
    assert validar(4, "ESTRES", {"n_nodos": []}) and validar(1, "NORMAL", {"pasos": "x"})
    for m in (1, 2, 3, 4):
        for e in ESCENARIOS:
            assert validar(m, e, None) == []
