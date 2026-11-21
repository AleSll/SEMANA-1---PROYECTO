# frontend/

Interfaz web de SIMTELE-RISK (inicio, módulo, resultados, interpretación e historial).

- `index.html`, `app.js`: interfaz.
- `transporte.js`: usa el servidor Flask si existe; si no (GitHub Pages) ejecuta el mismo código Python
  en el navegador con Pyodide y guarda la base SQLite en IndexedDB.
- `prototipo_semana1.html`: prototipo estático de la Semana 1.
