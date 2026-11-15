# SIMTELE-RISK

Proyecto integrador final de **Métodos Numéricos (INF-373)** · Carrera de Informática · Universidad Mayor de San Andrés (UMSA), La Paz, Bolivia.
Docente: Lic. Brigida Alexandra Carvajal Blanco.

Aplicación web educativa para estudiar, con métodos numéricos, cuatro casos de estudio inspirados en un sistema de transporte por cable como Mi Teleférico. **Todos los datos son sintéticos y los parámetros son supuestos**: el sistema no se conecta con equipos reales ni atribuye fallas a ninguna empresa.

## Integrantes

- Huaricona Laurel Najib Brayan
- Salgado Llusco Carlos Alejandro (mención: Desarrollo de Software e Innovación Tecnológica)

## Casos de estudio

1. Detención de emergencia de cabinas
2. Deterioro mecánico y mantenimiento
3. Oscilaciones por viento
4. Reconstrucción de señales de sensores

Cada caso se ejecutará en tres escenarios: NORMAL, ESTRÉS y MAL CONDICIONADO.

## Estado del proyecto (Semana 1)

| Componente | Estado |
|---|---|
| Teoría de errores (absoluto, relativo, porcentual, residuo, sensibilidad) | Implementado (`motor_numerico/errores.py`) |
| Sistemas lineales: Jacobi, Gauss-Seidel, LU, gradiente conjugado | Implementado y con pruebas (`motor_numerico/sistemas_lineales.py`) |
| Experimento de los 3 escenarios en el Módulo 2 | Implementado (`motor_numerico/experimento_semana1.py`) |
| Prototipo de interfaz (4 módulos, selector de escenarios) | Prototipo estático (`frontend/index.html`); no ejecuta cálculos todavía |
| Modelo de datos (DER y script SQL) | Definido (`db/`); aún no conectado a la aplicación |
| Interpolación, raíces, integración y EDO (RK2, RK4) | Pendiente (Semana 2) |
| API, persistencia conectada, historial y gráficos | Pendiente (Semana 2) |

## Estructura del repositorio

```
simtele-risk/
├── README.md
├── backend/            API: rutas, validaciones, acceso a datos (pendiente)
├── motor_numerico/     algoritmos puros e independientes de la interfaz
│   ├── errores.py
│   ├── sistemas_lineales.py
│   └── experimento_semana1.py
├── frontend/           interfaz web (prototipo index.html)
├── db/                 schema.sql y DER_SIMTELE_RISK.png
├── datos_ejemplo/      matrices, vectores y escenarios de entrada (JSON)
├── tests/              pruebas contra soluciones de referencia conocidas
└── docs/               informes de cada semana (PDF)
```

## Requisitos y ejecución

Requiere Python 3.9 o superior.

```bash
git clone [URL-DEL-REPOSITORIO]
cd simtele-risk
pip install -r requirements.txt

# Experimento de la Semana 1 (tablas de los tres escenarios)
python -m motor_numerico.experimento_semana1

# Pruebas unitarias
pytest
```

Prototipo de interfaz: abrir `frontend/index.html` en el navegador (no necesita servidor).

## Resultados de referencia (Semana 1)

Sistema 4×4 con solución conocida x* = [1, 2, 1, 1], tolerancia 10⁻⁸ sobre el residuo (norma infinito):

| Escenario | Jacobi | Gauss-Seidel | Gradiente conjugado | LU |
|---|---|---|---|---|
| NORMAL (κ₂ ≈ 2.61) | 24 iteraciones | 13 iteraciones | 4 iteraciones | directo |
| ESTRÉS (b perturbado ±5 %) | 24 iteraciones | 13 iteraciones | 4 iteraciones | directo |
| MAL CONDICIONADO (κ₂ = 10 000) | diverge (ρ = 2.895) | 3230 iteraciones (ρ = 0.9938) | 5 iteraciones | directo |

En el escenario mal condicionado una perturbación relativa de 4.77×10⁻⁶ en b produce un cambio relativo de 4.20×10⁻³ en la solución (amplificación de unas 880 veces). Jacobi falla porque ρ > 1, no por el número de condición: mal condicionamiento y falta de convergencia son fenómenos distintos.

## Modelo de datos

Ver `db/schema.sql` (SQLite) y `db/DER_SIMTELE_RISK.png`. Entidades: `caso_estudio`, `escenario`, `simulacion`, `ejecucion_metodo`, `iteracion_resultado` y `resultado_resumen`.

```bash
sqlite3 simtele.db < db/schema.sql
```

## Aviso

Proyecto académico sin fines operativos. Los resultados describen únicamente los modelos sintéticos utilizados.
