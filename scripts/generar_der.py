"""Genera db/DER_SIMTELE_RISK.png (v2.0) con matplotlib."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

E = {
 "caso_estudio": (0.02, 0.58, ["PK id", "nombre (UNIQUE)", "descripcion", "modelo_version"]),
 "escenario": (0.35, 0.58, ["PK id", "FK caso_id", "tipo (NORMAL/ESTRES/MAL_COND.)", "parametros_json", "fuente_datos"]),
 "simulacion": (0.68, 0.58, ["PK id", "FK escenario_id", "fecha", "estado", "observaciones", "modelo_version", "resultado_json"]),
 "resultado_resumen": (0.02, 0.06, ["PK id", "FK ejecucion_id (UNIQUE)", "referencia", "valor_json", "metrica_error_json", "interpretacion"]),
 "iteracion_resultado": (0.35, 0.06, ["PK id", "FK ejecucion_id", "numero", "aproximacion_json", "residual, error_abs, error_rel"]),
 "ejecucion_metodo": (0.68, 0.06, ["PK id", "FK simulacion_id", "metodo, familia", "tolerancia, paso, max_iter", "convergio, tiempo_ms", "mensaje"]),
}
fig, ax = plt.subplots(figsize=(13, 6.6)); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
W, H = 0.29, 0.34
for n, (x, y, at) in E.items():
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.003", fc="#f4f7fb", ec="#163a5f", lw=1.5))
    ax.add_patch(FancyBboxPatch((x, y + H - 0.06), W, 0.06, boxstyle="round,pad=0.003", fc="#163a5f", ec="#163a5f"))
    ax.text(x + W / 2, y + H - 0.03, n, color="white", ha="center", va="center", fontsize=10, weight="bold")
    for i, a in enumerate(at):
        ax.text(x + 0.012, y + H - 0.09 - i * 0.036, a, fontsize=8.5, va="center")
def flecha(p, q, t):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=1.4))
    ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.015, t, color="#c0392b", fontsize=9, ha="center", weight="bold")
flecha((0.31, 0.76), (0.35, 0.76), "1:N"); flecha((0.64, 0.76), (0.68, 0.76), "1:N")
flecha((0.825, 0.58), (0.825, 0.40), "1:N"); flecha((0.68, 0.23), (0.64, 0.23), "1:N")
ax.annotate("", xy=(0.31, 0.14), xytext=(0.68, 0.10), arrowprops=dict(arrowstyle="-|>", color="#c0392b", lw=1.4, connectionstyle="arc3,rad=-0.15"))
ax.text(0.5, 0.03, "1:1", color="#c0392b", fontsize=9, ha="center", weight="bold")
ax.set_title("SIMTELE-RISK — Diagrama entidad-relación v2.0 (PK: clave primaria; FK: clave foránea)", fontsize=12, weight="bold", color="#163a5f")
fig.savefig("db/DER_SIMTELE_RISK.png", dpi=130, bbox_inches="tight")
