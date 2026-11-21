# frontend/

`index.html`: aplicación de una sola página (HTML + CSS + JavaScript, **sin dependencias externas**; los gráficos son SVG generados en el navegador).
Pantallas: Inicio (4 tarjetas) · Módulo (modelo, parámetros validados, selector NORMAL/ESTRÉS/MAL CONDICIONADO, resultados, gráficos, tablas de iteraciones, conclusiones separadas) · Comparación (12 experimentos) · Historial (buscar, abrir, relanzar, eliminar).

Debe servirse desde el backend (`python -m backend.app`), porque consume `/api/...`.
