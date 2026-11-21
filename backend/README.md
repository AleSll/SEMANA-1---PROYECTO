# backend/

- `servicio.py`: ejecuta los módulos, valida parámetros y guarda/recupera simulaciones en SQLite
  (`db/schema.sql`). Es la misma lógica que usa Flask y el navegador (Pyodide).
- `validacion.py`: validación de los parámetros de cada módulo y escenario.
- `app.py`: API Flask + servidor de la interfaz.

```bash
python -m backend.app          # http://127.0.0.1:5000/  (base de datos: simtele.db)
```
