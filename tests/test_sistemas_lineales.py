import json
from pathlib import Path

import numpy as np
import pytest

from motor_numerico import errores
from motor_numerico.sistemas_lineales import (es_spd, gauss_seidel, gradiente_conjugado, jacobi, lu,
                                            radio_espectral)

DATOS = json.loads((Path(__file__).resolve().parents[1] / "datos_ejemplo" / "sistemas_semana1.json")
                   .read_text(encoding="utf-8"))
A = np.array(DATOS["normal"]["A"], float)
X = np.array(DATOS["normal"]["x_ref"], float)
B = A @ X
AM = np.array(DATOS["mal_condicionado"]["A"], float)
XM = np.array(DATOS["mal_condicionado"]["x_ref"], float)
BM = AM @ XM


def test_b_construido():
    assert np.allclose(B, [2, 6, 1, 2])


def test_matriz_spd():
    assert es_spd(A) and es_spd(AM)


@pytest.mark.parametrize("metodo,iters", [(jacobi, 24), (gauss_seidel, 13), (gradiente_conjugado, 4)])
def test_normal_converge_y_coincide_con_referencia(metodo, iters):
    r = metodo(A, B, x_ref=X)
    assert r.convergio and r.iteraciones == iters
    assert np.allclose(r.x, X, atol=1e-7)


def test_lu_directo():
    r = lu(A, B, x_ref=X)
    assert np.allclose(r.x, X, atol=1e-12)


def test_radios_espectrales_normal():
    assert radio_espectral(A, "jacobi") == pytest.approx(0.4234, abs=1e-4)
    assert radio_espectral(A, "gauss_seidel") == pytest.approx(0.1793, abs=1e-4)


def test_mal_condicionado_jacobi_diverge_gs_lento_cg_converge():
    assert np.linalg.cond(AM) == pytest.approx(1e4, rel=1e-3)
    assert radio_espectral(AM, "jacobi") > 1
    assert not jacobi(AM, BM, x_ref=XM).convergio
    gs = gauss_seidel(AM, BM, x_ref=XM)
    assert gs.convergio and gs.iteraciones == 3230
    cg = gradiente_conjugado(AM, BM, x_ref=XM)
    assert cg.convergio and cg.iteraciones == 5


def test_sensibilidad_mal_condicionado():
    s = errores.sensibilidad(AM, BM, DATOS["mal_condicionado"]["delta_b"])
    assert s["rel_b"] == pytest.approx(4.77e-6, rel=1e-2)
    assert s["rel_x"] == pytest.approx(4.20e-3, rel=1e-2)
    assert s["rel_x"] <= s["cota"]


def test_error_relativo_sin_division_por_cero():
    assert errores.error_relativo([0, 0], [1, 1]) is None
    assert errores.error_absoluto([0, 0], [1, 1]) == 1.0
