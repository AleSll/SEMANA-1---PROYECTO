-- SIMTELE-RISK | Script SQL del modelo de datos v2.0 (SQLite; adaptable a PostgreSQL)
-- Cambios respecto de la Semana 1: (1) todas las sentencias son idempotentes (IF NOT EXISTS / OR IGNORE) para poder
-- ejecutarse en cada arranque; (2) simulacion.resultado_json guarda el resultado completo (tablas, gráficos, conclusiones)
-- para recuperarlo después de reiniciar; (3) simulacion.modelo_version y ejecucion_metodo.mensaje.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS caso_estudio (
   id             INTEGER PRIMARY KEY AUTOINCREMENT,
   nombre         TEXT NOT NULL UNIQUE,
   descripcion    TEXT,
   modelo_version TEXT NOT NULL DEFAULT '2.0'
);

CREATE TABLE IF NOT EXISTS escenario (
   id              INTEGER PRIMARY KEY AUTOINCREMENT,
   caso_id         INTEGER NOT NULL REFERENCES caso_estudio(id) ON DELETE CASCADE,
   tipo            TEXT NOT NULL CHECK (tipo IN ('NORMAL','ESTRES','MAL_CONDICIONADO')),
   parametros_json TEXT NOT NULL,
   fuente_datos    TEXT NOT NULL DEFAULT 'sintetico'
);

CREATE TABLE IF NOT EXISTS simulacion (
   id             INTEGER PRIMARY KEY AUTOINCREMENT,
   escenario_id   INTEGER NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
   fecha          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
   estado         TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE','COMPLETADA','ERROR')),
   observaciones  TEXT,
   modelo_version TEXT NOT NULL DEFAULT '2.0',
   resultado_json TEXT                       -- tablas, gráficos y conclusiones (sin las iteraciones, que están en iteracion_resultado)
);

CREATE TABLE IF NOT EXISTS ejecucion_metodo (
   id            INTEGER PRIMARY KEY AUTOINCREMENT,
   simulacion_id INTEGER NOT NULL REFERENCES simulacion(id) ON DELETE CASCADE,
   metodo        TEXT NOT NULL,
   familia       TEXT,
   tolerancia    REAL,
   paso          REAL,
   max_iter      INTEGER,
   convergio     INTEGER CHECK (convergio IN (0,1)),
   tiempo_ms     REAL,
   mensaje       TEXT
);

CREATE TABLE IF NOT EXISTS iteracion_resultado (
   id                INTEGER PRIMARY KEY AUTOINCREMENT,
   ejecucion_id      INTEGER NOT NULL REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
   numero            INTEGER NOT NULL,
   aproximacion_json TEXT NOT NULL,
   residual          REAL,
   error_abs         REAL,
   error_rel         REAL,          -- NULL si el valor de referencia es 0
   UNIQUE (ejecucion_id, numero)
);

CREATE TABLE IF NOT EXISTS resultado_resumen (
   id                 INTEGER PRIMARY KEY AUTOINCREMENT,
   ejecucion_id       INTEGER NOT NULL UNIQUE REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
   referencia         TEXT,
   valor_json         TEXT,
   metrica_error_json TEXT,
   interpretacion     TEXT
);

CREATE INDEX IF NOT EXISTS idx_escenario_caso ON escenario(caso_id);
CREATE INDEX IF NOT EXISTS idx_simulacion_esc ON simulacion(escenario_id);
CREATE INDEX IF NOT EXISTS idx_ejecucion_sim  ON ejecucion_metodo(simulacion_id);
CREATE INDEX IF NOT EXISTS idx_iteracion_ejec ON iteracion_resultado(ejecucion_id);

INSERT OR IGNORE INTO caso_estudio (id, nombre, descripcion) VALUES
  (1, 'Detención de emergencia', 'EDO, integración y raíces'),
  (2, 'Deterioro y mantenimiento', 'Raíces y sistemas lineales'),
  (3, 'Oscilaciones por viento', 'EDO e integración'),
  (4, 'Reconstrucción de sensores', 'Interpolación y raíces');
