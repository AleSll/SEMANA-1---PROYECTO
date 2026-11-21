
# SIMTELE-RISK

**Proyecto integrador final de Métodos Numéricos (INF-373)**  
Carrera de Informática · Facultad de Ciencias Puras y Naturales  
Universidad Mayor de San Andrés (UMSA) · La Paz, Bolivia

**Docente:** Lic. Brígida Alexandra Carvajal Blanco.

SIMTELE-RISK es una aplicación web educativa que implementa, compara y verifica métodos numéricos mediante cuatro casos de estudio inspirados en un sistema de transporte por cable, como Mi Teleférico.

El proyecto integra algoritmos numéricos, visualización de resultados, interpretación de errores y almacenamiento de experimentos.

> **Consideración importante:** todos los datos utilizados son sintéticos y los parámetros son supuestos con fines académicos. La aplicación no tiene conexión con equipos reales, no realiza diagnósticos operativos y no atribuye fallas a ninguna empresa.

## Integrantes

- Huaricona Laurel Najib Brayan.  (mención: Desarrollo de Software e Innovación Tecnológica)
- Salgado Llusco Carlos Alejandro (mención: Desarrollo de Software e Innovación Tecnológica).

## Aplicación en línea

- **Aplicación web:** https://alesll.github.io/SEMANA-1---PROYECTO/frontend/
- **Repositorio:** https://github.com/AleSll/SEMANA-1---PROYECTO

La versión publicada mediante GitHub Pages ejecuta los cálculos en el navegador utilizando Python con Pyodide.

## Cómo iniciar la aplicación

### Opción A. Ejecución local

**Requisitos:**
- Python 3.9 o superior.
- Conexión a Internet para instalar las dependencias.

**Pasos:**

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/AleSll/SEMANA-1---PROYECTO.git
   ```

2. Ingresar a la carpeta:

   ```bash
   cd SEMANA-1---PROYECTO
   ```

3. Instalar las dependencias:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Iniciar la aplicación:

   ```bash
   python iniciar.py
   ```

   En Windows también se puede ejecutar mediante doble clic en `iniciar.bat`.

5. Abrir en el navegador:

   http://127.0.0.1:5000/

### Opción B. Ejecución en línea (GitHub Pages)

1. Abrir el enlace de la aplicación.
2. Esperar a que se cargue el entorno Python mediante Pyodide.
3. Seleccionar el módulo y escenario que se desea ejecutar.

La primera carga requiere conexión a Internet para descargar los componentes necesarios de Pyodide.

> No se recomienda abrir `frontend/index.html` directamente mediante doble clic (`file://`), ya que el navegador puede bloquear la carga de algunos recursos. Para la ejecución local se debe utilizar el servidor Flask.

## Casos de estudio y escenarios

La aplicación contempla cuatro módulos:

| N.º | Módulo | Descripción |
|---|---|---|
| 1 | Detención de emergencia de cabinas | Análisis del movimiento y tiempo de detención mediante modelos matemáticos. |
| 2 | Deterioro mecánico y mantenimiento | Estimación del comportamiento del deterioro y determinación de umbrales de mantenimiento. |
| 3 | Oscilaciones por viento | Simulación del comportamiento dinámico de un sistema sometido a fuerzas externas. |
| 4 | Reconstrucción de señales de sensores | Aproximación de datos mediante métodos de interpolación. |

Cada módulo contempla tres escenarios:

- **NORMAL:** representa condiciones de referencia.
- **ESTRÉS:** introduce condiciones más exigentes para evaluar el comportamiento de los métodos.
- **MAL CONDICIONADO:** analiza situaciones de sensibilidad numérica y dificultades de estabilidad o convergencia.

Los experimentos presentan resultados numéricos, tablas de iteraciones, errores, gráficos e interpretaciones.

## Métodos numéricos implementados

| Área | Métodos |
|---|---|
| Sistemas lineales | Jacobi, Gauss-Seidel, descomposición LU y gradiente conjugado. |
| Ecuaciones no lineales | Bisección, Newton-Raphson y secante. |
| Interpolación | Lagrange, Newton por diferencias divididas y spline cúbico. |
| Integración numérica | Trapecio compuesto, Simpson 1/3 compuesto y Romberg. |
| Ecuaciones diferenciales ordinarias | Runge-Kutta de segundo orden (Heun) y Runge-Kutta de cuarto orden (RK4). |
| Análisis de errores | Error absoluto, relativo, porcentual, residuo y sensibilidad numérica. |

## Estado del proyecto

| Componente | Estado |
|---|---|
| Teoría de errores y sistemas lineales | Implementado y con pruebas. |
| Métodos de raíces, interpolación e integración | Implementados y con pruebas. |
| Métodos numéricos para EDO | Implementados y con pruebas. |
| Cuatro módulos y tres escenarios | Implementados en `motor_numerico/casos.py`. |
| Interfaz web | Implementada en `frontend/`. |
| Servicio de ejecución y validación | Implementado en `backend/`. |
| Base de datos SQLite | Implementada para almacenar y recuperar simulaciones. |
| Pruebas automatizadas | Incluyen algoritmos, API y persistencia. |
| Informe final, video y conclusiones integradoras | Pendiente (Semana 3). |

## Arquitectura y estructura del repositorio

El proyecto está organizado en módulos independientes para separar la interfaz, la lógica numérica, el servicio de almacenamiento y las pruebas.

```text
SEMANA-1---PROYECTO/
│
├── iniciar.py
├── iniciar.bat
├── index.html
├── requirements.txt
├── pytest.ini
├── .gitignore
│
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── servicio.py
│   └── validacion.py
│
├── motor_numerico/
│   ├── __init__.py
│   ├── errores.py
│   ├── sistemas_lineales.py
│   ├── raices.py
│   ├── interpolacion.py
│   ├── integracion.py
│   ├── edo.py
│   ├── casos.py
│   ├── interpretacion.py
│   ├── experimento_semana1.py
│   └── experimento_semana2.py
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── transporte.js
│   └── prototipo_semana1.html
│
├── db/
│   ├── schema.sql
│   └── DER_SIMTELE_RISK.png
│
├── datos_ejemplo/
│   ├── sistemas_semana1.json
│   └── resultados_semana2.json
│
├── tests/
│   ├── test_sistemas_lineales.py
│   ├── test_raices.py
│   ├── test_interpolacion.py
│   ├── test_integracion.py
│   ├── test_edo.py
│   ├── test_app.py
│   ├── test_casos.py
│   └── test_servicio.py
│
└── docs/
    └── Documentación del proyecto
```

## Funcionamiento general

El sistema está dividido en tres componentes principales:

**1. Frontend**

Proporciona la interfaz web para seleccionar módulos, escenarios, métodos numéricos y parámetros. También permite visualizar resultados, gráficos, errores e historial de simulaciones.

**2. Backend**

Implementa el servicio de ejecución y validación mediante Flask. Recibe los parámetros, ejecuta los casos de estudio y administra el almacenamiento de los experimentos.

**3. Motor numérico**

Contiene los algoritmos matemáticos independientes de la interfaz. Cada método puede ejecutarse y probarse mediante datos de entrada y soluciones de referencia.

### Modalidades de ejecución

- **Con servidor:** `backend/app.py` administra las solicitudes y utiliza SQLite para guardar y recuperar simulaciones. La base de datos se almacena localmente en `simtele.db`.
- **Sin servidor:** `frontend/transporte.js` utiliza Pyodide para ejecutar el código Python en el navegador. El almacenamiento SQLite se conserva en IndexedDB del navegador.

En la modalidad sin servidor se requiere conexión a Internet durante la primera carga de Pyodide.

## Ejecución de experimentos y pruebas

Desde la carpeta principal del proyecto se pueden ejecutar los siguientes comandos:

**Iniciar la aplicación web:**

```bash
python iniciar.py
```

**Iniciar directamente el backend:**

```bash
python -m backend.app
```

**Ejecutar los experimentos de la Semana 2:**

```bash
python -m motor_numerico.experimento_semana2
```

**Ejecutar un módulo y escenario específico:**

```bash
python -m motor_numerico.experimento_semana2 3 ESTRES
```

**Ejecutar las pruebas automatizadas:**

```bash
pytest
```

## Resultados numéricos de referencia

Los siguientes resultados corresponden a los modelos sintéticos y configuraciones utilizadas en los experimentos del proyecto.

| Módulo | Escenario | Resultado de referencia |
|---|---|---|
| 1. Detención | NORMAL | Tiempo de detención: 10 s. Distancia de frenado: 25 m. RK2 y RK4 obtienen resultados exactos para aceleración constante. |
| 1. Detención | MAL CONDICIONADO | Modelo con raíz doble: Newton converge linealmente (36 iteraciones), Newton modificado en 1 iteración. La bisección no aplica directamente. |
| 2. Deterioro | NORMAL / ESTRÉS | Tiempo estimado: 13.72 y 9.26 meses, respectivamente. |
| 2. Deterioro | MAL CONDICIONADO | Umbral 0.20 → 0.2001 separa la raíz doble en 19.55 y 20.45. Jacobi diverge (ρ = 2.895), Gauss-Seidel requiere 3230 iteraciones y CG 5 iteraciones. |
| 3. Oscilaciones | NORMAL / ESTRÉS | El error de RK2 presenta comportamiento proporcional a h² y el de RK4 a h⁴. En resonancia, la amplitud estacionaria es 0.25 m. |
| 4. Sensores | NORMAL | Con 9 nodos, el error de Lagrange/Newton es ≤ 2.0 × 10⁻⁴ y el del spline es ≤ 8.9 × 10⁻⁴. |
| 4. Sensores | MAL CONDICIONADO | Con 20 nodos equiespaciados y ruido, Lagrange presenta error 1.35 frente a 8 × 10⁻⁴ del spline. El condicionamiento de Vandermonde es κ = 4.7 × 10²². |

## Modelo de datos

La persistencia utiliza SQLite y se define en:

- `db/schema.sql`: estructura de la base de datos.
- `db/DER_SIMTELE_RISK.png`: diagrama entidad-relación.

Las principales entidades son:

- `caso_estudio`
- `escenario`
- `simulacion`
- `ejecucion_metodo`
- `iteracion_resultado`
- `resultado_resumen`

El sistema almacena la información de los experimentos, incluyendo los parámetros, métodos ejecutados, iteraciones, errores y resultados. El resultado completo del módulo se conserva en formato JSON dentro de `resultado_resumen.valor_json`.

## Publicación en GitHub Pages

Para publicar la interfaz web:

1. Ingresar al repositorio en GitHub.
2. Abrir **Settings → Pages**.
3. En **Build and deployment**, seleccionar **Deploy from a branch**.
4. Seleccionar la rama `main` y la carpeta `/ (root)` o la configuración correspondiente al despliegue.
5. Guardar los cambios.

La dirección pública configurada para el proyecto es:

https://alesll.github.io/SEMANA-1---PROYECTO/frontend/

## Aviso académico

SIMTELE-RISK es un proyecto académico desarrollado con fines educativos y de experimentación numérica.

Los resultados representan exclusivamente el comportamiento de los modelos matemáticos sintéticos implementados. No deben interpretarse como mediciones, diagnósticos, predicciones operativas ni evaluaciones de seguridad de un sistema de transporte real.
