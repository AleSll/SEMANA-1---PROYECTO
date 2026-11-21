/* Transporte de SIMTELE-RISK: decide si los cálculos y el historial los atiende
   (a) el servidor Flask (backend/app.py), o (b) Python ejecutado dentro del navegador con Pyodide,
   que es lo que ocurre en GitHub Pages. En ambos casos se usa el mismo código Python y la misma
   base de datos SQLite (db/schema.sql). En el navegador el archivo .db se guarda en IndexedDB,
   de modo que el historial sobrevive al cierre o la recarga de la página. */
(function (global) {
  'use strict';

  var VERSION_PYODIDE = '0.27.7';
  var RUTA_BD = '/home/pyodide/simtele.db';
  var CLAVE_BD = 'simtele.db';
  var ARCHIVOS = [
    'motor_numerico/__init__.py', 'motor_numerico/errores.py', 'motor_numerico/sistemas_lineales.py',
    'motor_numerico/raices.py', 'motor_numerico/interpolacion.py', 'motor_numerico/integracion.py',
    'motor_numerico/edo.py', 'motor_numerico/casos.py', 'motor_numerico/interpretacion.py',
    'backend/__init__.py', 'backend/validacion.py', 'backend/servicio.py',
    'db/schema.sql', 'datos_ejemplo/sistemas_semana1.json'
  ];
  var ACCIONES_QUE_ESCRIBEN = { simular: 1, relanzar: 1, eliminar: 1 };

  function crearTransporte(env) {
    var modo = null, py = null, llamarPy = null, persistente = false;

    // ---------------- IndexedDB (persistencia de la base en el navegador)
    function abrirIDB() {
      return new Promise(function (res, rej) {
        var r = env.indexedDB.open('simtele-risk', 1);
        r.onupgradeneeded = function () { r.result.createObjectStore('archivos'); };
        r.onsuccess = function () { res(r.result); };
        r.onerror = function () { rej(r.error); };
      });
    }
    function leerIDB(clave) {
      return abrirIDB().then(function (db) {
        return new Promise(function (res, rej) {
          var q = db.transaction('archivos', 'readonly').objectStore('archivos').get(clave);
          q.onsuccess = function () { res(q.result); };
          q.onerror = function () { rej(q.error); };
        });
      });
    }
    function escribirIDB(clave, valor) {
      return abrirIDB().then(function (db) {
        return new Promise(function (res, rej) {
          var t = db.transaction('archivos', 'readwrite');
          t.objectStore('archivos').put(valor, clave);
          t.oncomplete = function () { res(); };
          t.onerror = function () { rej(t.error); };
        });
      });
    }

    // ---------------- detección del modo
    function detectar() {
      return env.fetch(env.apiBase + 'api/salud', { cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { return j && j.ok ? 'flask' : 'pyodide'; })
        .catch(function () { return 'pyodide'; });
    }

    function cargarScript(url) {
      return new Promise(function (res, rej) {
        var s = env.document.createElement('script');
        s.src = url; s.onload = res; s.onerror = function () { rej(new Error('No se pudo cargar ' + url)); };
        env.document.head.appendChild(s);
      });
    }

    function iniciarPyodide(progreso) {
      var disponible = env.loadPyodide || global.loadPyodide;
      var cargador = disponible ? Promise.resolve() :
        (progreso('Descargando Python (Pyodide)…'), cargarScript(env.indexURL + 'pyodide.js'));
      return cargador.then(function () {
        progreso('Iniciando Python…');
        return (env.loadPyodide || global.loadPyodide)({ indexURL: env.indexURL });
      }).then(function (p) {
        py = p;
        progreso('Cargando NumPy y SQLite…');
        return py.loadPackage(['numpy', 'sqlite3']);
      }).then(function () {
        progreso('Cargando el motor numérico…');
        return Promise.all(ARCHIVOS.map(function (f) {
          return env.fetch(env.base + f).then(function (r) {
            if (!r.ok) throw new Error('No se pudo leer ' + f);
            return r.text();
          }).then(function (txt) { return [f, txt]; });
        }));
      }).then(function (lista) {
        lista.forEach(function (par) {
          var ruta = '/home/pyodide/' + par[0];
          py.FS.mkdirTree(ruta.substring(0, ruta.lastIndexOf('/')));
          py.FS.writeFile(ruta, par[1]);
        });
        progreso('Recuperando el historial guardado…');
        return leerIDB(CLAVE_BD).then(function (bytes) {
          persistente = true;
          if (bytes) py.FS.writeFile(RUTA_BD, new Uint8Array(bytes));
        }).catch(function () { persistente = false; });
      }).then(function () {
        py.runPython(
          "import sys\nsys.path.insert(0, '/home/pyodide')\n" +
          "from backend import servicio as _servicio\n" +
          "_srv = _servicio.Servicio(_servicio.conectar('" + RUTA_BD + "'))\n");
        llamarPy = py.runPython('_srv.llamar_json');
      });
    }

    function persistir() {
      if (!persistente) return Promise.resolve();
      var bytes = py.FS.readFile(RUTA_BD);
      return escribirIDB(CLAVE_BD, new Uint8Array(bytes)).catch(function () { persistente = false; });
    }

    // ---------------- API pública
    function iniciar(progreso) {
      progreso = progreso || function () {};
      return detectar().then(function (m) {
        modo = m;
        if (m === 'flask') { persistente = true; return; }
        return iniciarPyodide(progreso);
      }).then(function () { return { modo: modo, persistente: persistente }; });
    }

    function llamar(accion, datos) {
      datos = datos || {};
      var promesa;
      if (modo === 'flask') {
        promesa = env.fetch(env.apiBase + 'api/' + accion, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(datos)
        }).then(function (r) { return r.json(); });
      } else {
        try { promesa = Promise.resolve(JSON.parse(llamarPy(accion, JSON.stringify(datos)))); }
        catch (e) { promesa = Promise.reject(e); }
        if (ACCIONES_QUE_ESCRIBEN[accion]) promesa = promesa.then(function (r) { return persistir().then(function () { return r; }); });
      }
      return promesa.then(function (r) {
        if (r && r.error) throw new Error(r.error);
        return r;
      });
    }

    return { iniciar: iniciar, llamar: llamar, modo: function () { return modo; }, persistente: function () { return persistente; } };
  }

  function entornoNavegador() {
    var base = new URL('../', global.location.href).href;
    return {
      fetch: global.fetch.bind(global), indexedDB: global.indexedDB, document: global.document,
      loadPyodide: null, base: base, apiBase: base,
      indexURL: 'https://cdn.jsdelivr.net/pyodide/v' + VERSION_PYODIDE + '/full/'
    };
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = crearTransporte;
  if (typeof window !== 'undefined' && global.document) global.Transporte = crearTransporte(entornoNavegador());
})(typeof window !== 'undefined' ? window : globalThis);
