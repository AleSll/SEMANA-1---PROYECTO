-- SIMTELE-RISK | Script SQL del modelo de datos (SQLite; adaptable a PostgreSQL)
PRAGMA foreign_keys = ON;

CREATE TABLE caso_estudio (
   id             INTEGER PRIMARY KEY AUTOINCREMENT,
   nombre         TEXT NOT NULL UNIQUE,
   descripcion    TEXT,
   modelo_version TEXT NOT NULL DEFAULT '1.0'
);

CREATE TABLE escenario (
   id              INTEGER PRIMARY KEY AUTOINCREMENT,
   caso_id         INTEGER NOT NULL REFERENCES caso_estudio(id) ON DELETE CASCADE,
   tipo            TEXT NOT NULL CHECK (tipo IN ('NORMAL','ESTRES','MAL_CONDICIONADO')),
   parametros_json TEXT NOT NULL,
   fuente_datos    TEXT NOT NULL DEFAULT 'sintetico'
);

CREATE TABLE simulacion (
   id            INTEGER PRIMARY KEY AUTOINCREMENT,
   escenario_id INTEGER NOT NULL REFERENCES escenario(id) ON DELETE CASCADE,
   fecha         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
   estado        TEXT NOT NULL DEFAULT 'PENDIENTE'
                 CHECK (estado IN ('PENDIENTE','COMPLETADA','ERROR')),
   observaciones TEXT
);

CREATE TABLE ejecucion_metodo (
   id            INTEGER PRIMARY KEY AUTOINCREMENT,
   simulacion_id INTEGER NOT NULL REFERENCES simulacion(id) ON DELETE CASCADE,
   metodo        TEXT NOT NULL,
   tolerancia    REAL,
   paso          REAL,
   max_iter      INTEGER,
   convergio     INTEGER CHECK (convergio IN (0,1)),
   tiempo_ms     REAL
);

CREATE TABLE iteracion_resultado (
   id                INTEGER PRIMARY KEY AUTOINCREMENT,
   ejecucion_id      INTEGER NOT NULL REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
   numero            INTEGER NOT NULL,
   aproximacion_json TEXT NOT NULL,
   residual          REAL,
   error_abs         REAL,
   error_rel         REAL,          -- NULL si el valor de referencia es 0
   UNIQUE (ejecucion_id, numero)
);

CREATE TABLE resultado_resumen (
   id                 INTEGER PRIMARY KEY AUTOINCREMENT,
   ejecucion_id       INTEGER NOT NULL UNIQUE REFERENCES ejecucion_metodo(id) ON DELETE CASCADE,
   referencia         TEXT,
   valor_json         TEXT,
   metrica_error_json TEXT,
   interpretacion     TEXT
);

CREATE INDEX idx_escenario_caso     ON escenario(caso_id);
CREATE INDEX idx_simulacion_esc     ON simulacion(escenario_id);
CREATE INDEX idx_ejecucion_sim      ON ejecucion_metodo(simulacion_id);
CREATE INDEX idx_iteracion_ejec     ON iteracion_resultado(ejecucion_id);

INSERT INTO caso_estudio (nombre, descripcion) VALUES
  ('Detención de emergencia', 'EDO, integración y raíces'),
  ('Deterioro y mantenimiento', 'Raíces y sistemas lineales'),
  ('Oscilaciones por viento', 'EDO e integración'),
  ('Reconstrucción de sensores', 'Interpolación');
