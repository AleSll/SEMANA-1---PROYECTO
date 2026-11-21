import json

import pytest

from motor_numerico.casos import ESCENARIOS, ejecutar, serializable

COMBINACIONES = [(m, e) for m in (1, 2, 3, 4) for e in ESCENARIOS]


@pytest.mark.parametrize("modulo,escenario", COMBINACIONES)
def test_los_doce_casos_se_ejecutan_y_son_serializables(modulo, escenario):
    r = ejecutar(modulo, escenario)
    assert r["modulo"] == modulo and r["escenario"] == escenario
    assert r["tablas"] and len(r["graficos"]) >= 2
    json.dumps(serializable(r), allow_nan=False)


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        ejecutar(1, "INEXISTENTE")


def test_modulo1_referencias_y_ordenes():
    r = ejecutar(1, "NORMAL")
    assert r["referencia"]["t_det"] == 10.0 and r["referencia"]["d_total"] == pytest.approx(32.5)
    ampl = [f for f in r["tablas"][3]["filas"] if f[0] == "RK4" and f[3]]
    assert ampl[-1][3] == pytest.approx(4.0, abs=0.15)


def test_modulo1_mal_condicionado_distingue_raiz_doble():
    r = ejecutar(1, "MAL_CONDICIONADO")
    filas = {f[0]: f for f in r["tablas"][0]["filas"]}
    assert filas["Bisección"][2] is False and filas["Newton modificado (m=2)"][1] == 1
    assert filas["Newton-Raphson"][1] > 25
    simpson_ok = [f[5] for f in r["tablas"][1]["filas"] if isinstance(f[0], int)]
    assert max(simpson_ok) < 1e-12                         # Simpson es exacto en una cuadrática


def test_modulo2_tiempos_y_sensibilidad():
    n = ejecutar(2, "NORMAL"); e = ejecutar(2, "ESTRES"); m = ejecutar(2, "MAL_CONDICIONADO")
    assert n["referencia"]["t_umbral"] == pytest.approx(13.72, abs=5e-3)
    assert e["referencia"]["t_umbral"] == pytest.approx(9.26, abs=5e-3)
    assert m["referencia"]["amplificacion_dt_du"] == pytest.approx(4472, rel=1e-3)
    assert m["referencia"]["sistema_lineal"]["kappa2"] == pytest.approx(1e4, rel=1e-3)


def test_modulo3_resonancia_y_critico():
    e = ejecutar(3, "ESTRES")
    assert e["referencia"]["amplitud_estacionaria"] == pytest.approx(0.25)
    rk4 = [f for f in e["tablas"][0]["filas"] if f[0] == "RK4" and f[1] == 0.1][0]
    assert rk4[4] == pytest.approx(0.25, rel=1e-2) and e["referencia"]["chequeo_referencia"] < 1e-9
    m = ejecutar(3, "MAL_CONDICIONADO")["tablas"][0]["filas"]
    assert m[0][4] == pytest.approx(0.706, abs=1e-3) and m[1][2] == 0.0


def test_modulo4_errores_y_mal_condicionamiento():
    n = ejecutar(4, "NORMAL")["tablas"][0]["filas"]
    assert n[0][4] == pytest.approx(2.05e-4, rel=1e-2) and n[2][4] == pytest.approx(8.95e-4, rel=1e-2)
    mal = ejecutar(4, "MAL_CONDICIONADO")
    err = {f[0]: f[4] for f in mal["tablas"][0]["filas"]}
    assert err["Lagrange"] > 100 * err["Spline cúbico"]
    assert mal["tablas"][1]["filas"][0][1] > 1e20
