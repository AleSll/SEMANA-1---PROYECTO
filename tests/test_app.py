import pytest

flask = pytest.importorskip("flask")

from backend.app import crear_app


@pytest.fixture
def cliente(tmp_path):
    return crear_app(str(tmp_path / "api.db")).test_client()


def test_api_flujo_completo(cliente):
    assert cliente.get("/api/salud").get_json()["ok"]
    r = cliente.post("/api/simular", json={"modulo": 4, "escenario": "NORMAL", "equipo": "pareja 1"})
    assert r.status_code == 200 and r.get_json()["id"] == 1
    assert cliente.post("/api/listar", json={"q": "Reconstrucción"}).get_json()["simulaciones"][0]["id"] == 1
    assert cliente.post("/api/abrir", json={"id": 1}).get_json()["interpretacion"]["problema"]
    assert cliente.post("/api/relanzar", json={"id": 1}).get_json()["coincide"]
    mal = cliente.post("/api/simular", json={"modulo": 1, "escenario": "NORMAL", "parametros": {"v0": -5}})
    assert mal.status_code == 400 and "v0" in mal.get_json()["error"]


def test_se_sirve_la_interfaz(cliente):
    assert cliente.get("/").status_code == 302
    r = cliente.get("/frontend/")
    assert r.status_code == 200 and b"SIMTELE-RISK" in r.data
    r.close()
