
# SIMTELE-RISK

**Proyecto integrador final de Métodos Numéricos (INF-373)**  
Carrera de Informática · Facultad de Ciencias Puras y Naturales  
Universidad Mayor de San Andrés (UMSA) · La Paz, Bolivia.

**Docente:** Lic. Brígida Alexandra Carvajal Blanco.

SIMTELE-RISK es una aplicación web educativa que estudia y resuelve, mediante métodos numéricos, cuatro casos de estudio inspirados en un sistema de transporte por cable como Mi Teleférico.

El proyecto integra algoritmos numéricos, simulaciones, comparación de métodos, análisis de errores, visualización de resultados y persistencia de experimentos.

> **Consideración importante:** todos los datos son sintéticos y los parámetros son supuestos con fines académicos. El sistema no se conecta con equipos reales, no realiza diagnósticos operativos ni atribuye fallas a ninguna empresa.

## Integrantes

- Huaricona Laurel Najib Brayan (mención: Desarrollo de Software e Innovación Tecnológica).
- Salgado Llusco Carlos Alejandro (mención: Desarrollo de Software e Innovación Tecnológica).

## Enlaces del proyecto

- **Repositorio GitHub:** https://github.com/AleSll/SEMANA-1---PROYECTO
- **Aplicación publicada:** https://alesll.github.io/SEMANA-1---PROYECTO/frontend/
- **Video de presentación:** Pendiente de publicación.

## Módulos y métodos numéricos

La aplicación contempla cuatro módulos, cada uno con tres escenarios de experimentación: NORMAL, ESTRÉS y MAL CONDICIONADO.

| Módulo | Métodos implementados | Referencia de validación |
|---|---|---|
| 1. Detención de emergencia | RK2 (Heun), RK4, trapecio, Simpson 1/3, Romberg, bisección, Newton y secante. | Solución analítica para aceleración constante y modelo variable a = a₀ + c·v. |
| 2. Deterioro y mantenimiento | Bisección, Newton, secante, Jacobi, Gauss-Seidel, LU y gradiente conjugado. | Fórmula cuadrática y solución conocida x* para sistemas b = A·x*. |
| 3. Oscilaciones por viento | RK2, RK4, trapecio, Simpson 1/3 y Romberg aplicados a la integral de x². | Solución analítica contrastada con DOP853 (rtol = 10⁻¹²). |
| 4. Reconstrucción de sensores | Lagrange, Newton por diferencias divididas, spline cúbico natural, bisección y secante para cruces de umbral. | Función sin(t) evaluada en puntos de prueba ocultos. |

### Análisis de errores

La teoría de errores se aplica transversalmente a los cuatro módulos:

- Error absoluto.
- Error relativo, evitando divisiones entre cero.
- Error porcentual.
- Error residual.
- Análisis de sensibilidad.
- Número de condición (κ).
- Constante de Lebesgue.
- Orden empírico de convergencia.

## Estado del proyecto — Semana 2

| Componente | Estado |
|---|---|
| Interpolación, raíces, integración y EDO | Implementados y probados en `motor_numerico/`. |
| Cuatro módulos y tres escenarios por módulo | Implementados en `motor_numerico/modulos/`. |
| Tablas de resultados, errores, gráficos y conclusiones | Implementados en los experimentos. |
| API Flask y validación de parámetros | Implementadas en `backend/app.py`. |
| Base de datos SQLite | Implementada mediante `db/schema.sql` y `backend/db.py`. |
| Guardar, recuperar y relanzar simulaciones | Implementado y probado. |
| Interfaz web: inicio, módulos, comparación e historial | Implementada en `frontend/index.html`. |
| Conclusiones finales, defensa y video | Pendientes para la Semana 3. |

## Estructura del proyecto

La aplicación utiliza una arquitectura modular que separa la interfaz web, el servicio de persistencia, los algoritmos numéricos y los experimentos.

```text
SEMANA-1---PROYECTO/
│
├── README.md
├── requirements.txt
├── pytest.ini
├── Procfile
├── render.yaml
├── wsgi.py
│
├── backend/
│   ├── app.py
│   └── db.py
│
├── motor_numerico/
│   ├── errores.py
│   ├── sistemas_lineales.py
│   ├── raices.py
│   ├── integracion.py
│   ├── edo.py
│   ├── interpolacion.py
│   └── modulos/
│       ├── módulos y casos de estudio
│       └── escenarios NORMAL, ESTRÉS y MAL CONDICIONADO
│
├── frontend/
│   └── index.html
│
├── db/
│   ├── schema.sql
│   └── DER_SIMTELE_RISK.png
│
├── datos_ejemplo/
│   ├── entradas de la Semana 1
│   └── experimentos_semana2.json
│
├── scripts/
│   ├── prueba_persistencia.py
│   └── generar_der.py
│
├── tests/
│   ├── pruebas de métodos numéricos
│   ├── pruebas de módulos
│   └── pruebas de persistencia
│
└── docs/
    ├── informes semanales
    └── DESPLIEGUE.md
```

## Instalación y ejecución local

### Requisitos

- Python 3.9 o superior.
- pip.
- Git.
- Navegador web actualizado.

### 1. Clonar el repositorio

```bash
git clone https://github.com/AleSll/SEMANA-1---PROYECTO.git
cd SEMANA-1---PROYECTO
```

### 2. Crear el entorno virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación, también puedes ejecutar los comandos de instalación utilizando:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Linux o macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
python -m pip install -r requirements.txt
```

### 4. Iniciar la aplicación

```bash
python -m backend.app
```

Abrir en el navegador:

http://127.0.0.1:5000/

### 5. Ejecutar las pruebas

```bash
pytest
```

Las pruebas verifican los métodos numéricos, los casos de estudio y el funcionamiento de la persistencia.

### 6. Ejecutar la prueba de persistencia

```bash
python -m scripts.prueba_persistencia
```

Esta prueba verifica el flujo:

1. Ejecutar una simulación.
2. Guardar los resultados.
3. Reiniciar el servicio.
4. Recuperar la simulación.
5. Repetir el experimento.
6. Comparar los resultados.

### 7. Ejecutar experimentos de la Semana 1

```bash
python -m motor_numerico.experimento_semana1
```

## Persistencia y almacenamiento

La aplicación utiliza SQLite para almacenar los experimentos y permitir su recuperación.

La estructura de la base de datos se define en `db/schema.sql`.

La ubicación predeterminada de almacenamiento es:

```text
data/simtele.db
```

También se puede configurar una ruta personalizada mediante la variable de entorno `SIMTELE_DB`.

La persistencia permite conservar los parámetros, escenarios, métodos ejecutados y resultados de las simulaciones.

## Resultados numéricos verificables

Los siguientes resultados corresponden a los parámetros de referencia utilizados en los experimentos del proyecto.

| Experimento | Resultado de referencia |
|---|---|
| M1 NORMAL | Tiempo de detención: 10 s. Distancia total: 32.5 m. RK2 y RK4 exactos para la solución polinomial. |
| M1 ESTRÉS | Con a = a₀ + c·v: t_det = 13.863 s y d_total = 61.10 m. Error máximo RK2: 4.7 × 10⁻² m; RK4: 5.8 × 10⁻⁶ m. |
| M1 MAL CONDICIONADO | Raíz doble: Newton requiere 36 iteraciones, con razón de convergencia 0.5; Newton modificado requiere 1. La bisección no aplica directamente. |
| M2 NORMAL | Tiempo estimado: 13.7228 meses. Jacobi: 24 iteraciones; Gauss-Seidel: 13; CG: 4. |
| M2 MAL CONDICIONADO | κ₂ = 10⁴. Jacobi diverge (ρ = 2.895); Gauss-Seidel: 3230 iteraciones; CG: 5. Amplificación: ×880. |
| M3 ESTRÉS | Casi resonancia: amplitud máxima de 0.235 m. Error RK2: 3.3 × 10⁻³ m; RK4: 1.6 × 10⁻⁶ m. |
| M3 MAL CONDICIONADO | ζ = 0.999 y h = 1.2 s. RK2 diverge (‖R‖ = 1.45 > 1), mientras RK4 permanece estable. |
| M4 MAL CONDICIONADO | 21 nodos y σ = 10⁻³. Constante de Lebesgue Λ ≈ 1.1 × 10⁴. Error del polinomio ≈ 1.5 frente a ≈ 2 × 10⁻³ del spline. |

## Modelo de datos

El modelo de datos utiliza SQLite y se encuentra definido en:

- `db/schema.sql`: definición de las tablas y relaciones.
- `db/DER_SIMTELE_RISK.png`: diagrama entidad-relación.

Las principales entidades son:

- `caso_estudio`
- `escenario`
- `simulacion`
- `ejecucion_metodo`
- `iteracion_resultado`
- `resultado_resumen`

La estructura permite registrar los experimentos y conservar sus resultados para posteriores consultas y comparaciones.

## Publicación y despliegue

El proyecto contempla archivos de configuración para despliegue:

- `Procfile`
- `render.yaml`
- `wsgi.py`

La guía de configuración y publicación se encuentra en:

`docs/DESPLIEGUE.md`

Aplicación publicada:

https://alesll.github.io/SEMANA-1---PROYECTO/frontend/

## Aviso académico

SIMTELE-RISK es un proyecto académico desarrollado exclusivamente con fines educativos y de experimentación numérica.

Los resultados representan únicamente el comportamiento de los modelos matemáticos sintéticos implementados. No deben interpretarse como mediciones reales, diagnósticos, predicciones operativas ni evaluaciones de seguridad de un sistema de transporte existente.
