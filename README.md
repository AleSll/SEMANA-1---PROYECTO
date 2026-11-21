# SIMTELE-RISK

Proyecto integrador final de **Métodos Numéricos (INF-373)** · Carrera de Informática · Universidad Mayor de San Andrés (UMSA), La Paz, Bolivia.
Docente: Lic. Brigida Alexandra Carvajal Blanco.

Aplicación web educativa que resuelve, compara y verifica con métodos numéricos cuatro casos de estudio inspirados en un sistema de transporte por cable como Mi Teleférico. **Todos los datos son sintéticos y los parámetros son supuestos**: no hay conexión con equipos reales ni se atribuyen fallas a ninguna empresa.

## Integrantes

- Huaricona Laurel Najib Brayan
- Salgado Llusco Carlos Alejandro (mención: Desarrollo de Software e Innovación Tecnológica)

## Aplicación en línea

- **Aplicación:** `https://TU-USUARIO.github.io/simtele-risk/` (GitHub Pages; el cálculo se hace en el navegador con Python/Pyodide)
- Repositorio: `https://github.com/TU-USUARIO/simtele-risk`

## Cómo iniciar la aplicación

**Opción A — en su computadora (recomendada para la defensa):**

1. Instale Python 3.9 o superior (en Windows marque «Add Python to PATH»).
2. En la carpeta del proyecto: `pip install -r requirements.txt` (en Windows también `py -m pip install -r requirements.txt`).
3. Ejecute `python iniciar.py` (o doble clic en `iniciar.bat` en Windows). Se abre `http://127.0.0.1:5000/`.

**Opción B — en línea (GitHub Pages):** abra el enlace de la aplicación y espere unos segundos a que cargue Python.

> No abra `frontend/index.html` con doble clic: los navegadores bloquean la carga del motor de cálculo desde archivos locales (`file://`). Use la opción A o B.

## Casos de estudio y escenarios

1. Detención de emergencia de cabinas
2. Deterioro mecánico y mantenimiento
3. Oscilaciones por viento
4. Reconstrucción de señales de sensores

Cada módulo se ejecuta en tres escenarios: NORMAL, ESTRÉS y MAL CONDICIONADO, con tablas de iteraciones y errores, al menos dos gráficos, y dos conclusiones separadas (numérica y del problema).

## Estado del proyecto

| Componente | Estado |
|---|---|
| Teoría de errores y sistemas lineales (Jacobi, Gauss-Seidel, LU, gradiente conjugado) | Implementado y con pruebas |
| Raíces (bisección, Newton-Raphson, secante), interpolación (Lagrange, Newton, spline cúbico), integración (trapecio, Simpson 1/3, Romberg), EDO (RK2 de Heun, RK4) | Implementado y con pruebas |
| 4 módulos × 3 escenarios con tablas, errores, gráficos e interpretación | Implementado (`motor_numerico/casos.py`) |
| Aplicación web: inicio, módulo, resultados, interpretación, historial | Implementada (`frontend/`) |
| Base de datos SQLite: guardar, buscar, abrir y relanzar simulaciones | Implementada (`backend/servicio.py`, `db/schema.sql`) |
| Prueba de persistencia (ejecutar → guardar → reiniciar → recuperar → repetir) | Automatizada (`tests/test_servicio.py`) |
| Informe final, video y conclusiones integradoras | Pendiente (Semana 3) |

## Estructura del repositorio

```
simtele-risk/
├── iniciar.py / iniciar.bat   inicia la aplicación en su computadora
├── index.html           redirige a la aplicación (GitHub Pages)
├── backend/             servicio.py (guardar/recuperar), validacion.py, app.py (Flask)
├── motor_numerico/      algoritmos puros e independientes de la interfaz
│   ├── errores.py  sistemas_lineales.py  raices.py  interpolacion.py  integracion.py  edo.py
│   ├── casos.py              los 4 módulos y sus 3 escenarios
│   ├── interpretacion.py     conclusiones numérica y del problema
│   └── experimento_semana1.py / experimento_semana2.py
├── frontend/            interfaz web (index.html, app.js, transporte.js)
├── db/                  schema.sql y DER_SIMTELE_RISK.png
├── datos_ejemplo/       matrices y vectores de entrada (JSON)
├── tests/               pruebas contra soluciones de referencia
└── docs/                informes de cada semana (PDF)
```

## Cómo funciona

La interfaz envía los parámetros a un **servicio** (`backend/servicio.py`) que valida, ejecuta el módulo y guarda en SQLite la simulación completa: escenario y parámetros, cada método con su tolerancia, paso e iteraciones, errores y resumen. El historial lee de la base de datos, no de memoria.

- **Con servidor (Flask):** `python iniciar.py` (o `python -m backend.app`) y abrir `http://127.0.0.1:5000/`. La base es el archivo `simtele.db`.
- **Sin servidor (GitHub Pages):** `frontend/transporte.js` ejecuta ese mismo código Python dentro del navegador con Pyodide y guarda el archivo SQLite en IndexedDB, por lo que el historial sobrevive al cierre y la recarga de la página. Requiere internet para descargar Pyodide la primera vez (unos segundos).

## Ejecución local

Requiere Python 3.9 o superior.

```bash
git clone https://github.com/TU-USUARIO/simtele-risk.git
cd simtele-risk
pip install -r requirements.txt

python -m backend.app                                   # aplicación con Flask + SQLite
python -m motor_numerico.experimento_semana2            # los 12 casos en consola
python -m motor_numerico.experimento_semana2 3 ESTRES   # un módulo y escenario
pytest                                                  # pruebas
```

## Publicar en GitHub Pages

*Settings → Pages → Source: «Deploy from a branch» → Branch: `main` / `(root)` → Save.* El enlace será `https://TU-USUARIO.github.io/simtele-risk/`. El repositorio debe ser público.

## Resultados de referencia

| Módulo | Escenario | Resultado verificado |
|---|---|---|
| 1 Detención | NORMAL | t = 10 s, d = 25 m (RK2 y RK4 exactos con a constante); con a(v) = a + kv el error baja con orden 2 (RK2) y 4 (RK4) |
| 1 Detención | MAL CONDICIONADO | v = 0.05(t−10)², raíz doble: Newton converge linealmente (36 it.), Newton modificado en 1, la bisección no aplica |
| 2 Deterioro | NORMAL / ESTRÉS | t = 13.72 y 9.26 meses (mantenimiento retrasado: 4.47 meses antes) |
| 2 Deterioro | MAL CONDICIONADO | umbral 0.20 → 0.2001 separa la raíz doble en 19.55 y 20.45; Jacobi diverge (ρ = 2.895), Gauss-Seidel 3230 it., CG 5 it. |
| 3 Oscilaciones | NORMAL / ESTRÉS | error de RK2 ∝ h², de RK4 ∝ h⁴; en resonancia la amplitud estacionaria es 0.25 m |
| 4 Sensores | NORMAL | 9 nodos: error Lagrange/Newton ≤ 2.0×10⁻⁴, spline ≤ 8.9×10⁻⁴ |
| 4 Sensores | MAL CONDICIONADO | 20 nodos equiespaciados con ruido: Lagrange 1.35 frente a 8×10⁻⁴ del spline; κ(Vandermonde) = 4.7×10²² |

## Modelo de datos

`db/schema.sql` (SQLite) y `db/DER_SIMTELE_RISK.png`: `caso_estudio`, `escenario`, `simulacion`, `ejecucion_metodo`, `iteracion_resultado`, `resultado_resumen`. El resultado completo de cada simulación (tablas, gráficos e interpretación) se guarda en `resultado_resumen.valor_json` de la fila «Resultado completo del módulo».

## Aviso

Proyecto académico sin fines operativos. Los resultados describen únicamente los modelos sintéticos utilizados.
