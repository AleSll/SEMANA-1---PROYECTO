# backend/

API Flask de SIMTELE-RISK (`app.py`) y acceso a SQLite (`db.py`, usa `db/schema.sql`).

| Ruta | Descripción |
|---|---|
| `GET /` | Interfaz web (`frontend/index.html`) |
| `GET /api/modulos` | Catálogo: módulos, métodos, escenarios, parámetros con rangos y unidades |
| `POST /api/simular` | `{modulo, escenario, parametros}` → valida, ejecuta el motor, **guarda** y devuelve el resultado (400 si hay parámetros inválidos) |
| `GET /api/historial?q=&modulo=&escenario=` | Busca simulaciones guardadas |
| `GET /api/simulaciones/<id>` | Reconstruye una simulación **solo desde las tablas** (parámetros, iteraciones, gráficos) |
| `POST /api/simulaciones/<id>/relanzar` | Repite el cálculo con los parámetros guardados y compara con la original (tolerancia 1e-9) |
| `DELETE /api/simulaciones/<id>` | Elimina una simulación |
| `GET /api/comparacion` | Resumen de los 12 experimentos |

Variable de entorno `SIMTELE_DB`: ruta del archivo SQLite (por defecto `data/simtele.db`).
