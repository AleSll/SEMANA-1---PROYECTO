/* Interfaz de SIMTELE-RISK: inicio, módulo (modelo, parámetros y escenario), resultados,
   interpretación e historial. Los cálculos y el guardado los realiza Transporte (Flask o Pyodide). */
(function () {
  'use strict';
  var T = window.Transporte;
  var $ = function (id) { return document.getElementById(id); };

  var MODULOS = {
    1: { pregunta: '¿Cómo varían el tiempo y la distancia de detención con la velocidad, el tiempo de reacción y la desaceleración?',
         metodos: 'EDO: RK2 · RK4 | Integración: trapecio · Simpson · Romberg | Raíces: bisección · Newton · secante' },
    2: { pregunta: '¿Cuándo alcanza un indicador hipotético de deterioro el umbral de inspección?',
         metodos: 'Raíces: bisección · Newton · secante | Sistemas lineales: Jacobi · Gauss-Seidel · LU · gradiente conjugado' },
    3: { pregunta: '¿Cómo cambia la oscilación ante la fuerza externa y el amortiguamiento?',
         metodos: 'EDO: RK2 · RK4 | Integración de x(t)²: trapecio · Simpson · Romberg' },
    4: { pregunta: '¿Cómo reconstruir registros faltantes y medir la distorsión que produce el ruido?',
         metodos: 'Interpolación: Lagrange · Newton (diferencias divididas) · splines cúbicos | Raíces: bisección' }
  };
  var ESCENARIOS = { NORMAL: 'NORMAL', ESTRES: 'ESTRÉS', MAL_CONDICIONADO: 'MAL CONDICIONADO' };
  var DESC_ESC = {
    NORMAL: 'Parámetros nominales sintéticos, datos consistentes y configuración numérica adecuada. Sirve de caso base con su referencia analítica.',
    ESTRES: 'Condiciones más exigentes dentro del modelo (pasos distintos, perturbaciones o más ruido). Se compara el desempeño y la sensibilidad; una situación exigente no es mal condicionamiento.',
    MAL_CONDICIONADO: 'Subexperimento numérico sensible (matriz con κ elevado, raíz múltiple o nodos desfavorables). Se distingue el mal condicionamiento del fallo de convergencia y del peligro físico.'
  };
  var ETIQUETAS = {
    1: { v0: 'Velocidad inicial v₀ (m/s)', a: 'Desaceleración a (m/s²)', tr: 'Tiempo de reacción t_r (s)',
         pasos: 'Pasos h (s), separados por comas', k_arrastre: 'Coeficiente k de la ampliación a(v)=a+k·v (1/s)',
         c: 'Constante c de v(t)=c(t−t*)² (m/s³)', t_raiz: 'Raíz t* (s)', x0_newton: 'Semilla inicial de Newton (s)' },
    2: { D0: 'Deterioro inicial D₀', alpha: 'α (1/mes)', beta: 'β (1/mes²)', umbral: 'Umbral de inspección',
         D_min: 'Valor mínimo del deterioro', t_min: 'Instante del mínimo (meses)', delta_umbral: 'Aumento del umbral para la sensibilidad' },
    3: { m: 'Masa equivalente m (kg)', c: 'Amortiguamiento c (N·s/m)', k: 'Rigidez k (N/m)', x0: 'Desplazamiento inicial x₀ (m)',
         v0: 'Velocidad inicial v₀ (m/s)', F0: 'Amplitud de la fuerza F₀ (N)', w: 'Frecuencia de la fuerza ω (rad/s)',
         T: 'Duración T (s)', h: 'Paso h (s)', pasos: 'Pasos h (s) (múltiplos de 0.001 que dividan a T)',
         amortiguamientos: 'Valores de c a comparar (N·s/m)' },
    4: { n_nodos: 'Número de nodos', ocultos: 'Puntos ocultos t (entre 0 y 6.283)', sigma: 'Desviación del ruido σ',
         semilla: 'Semilla del ruido (entero)' }
  };
  var ENTEROS = { n_nodos: 1, semilla: 1 };
  var COLORES = ['#163a5f', '#c0392b', '#267080', '#d68910', '#7d3c98', '#1e8449'];

  var estado = { modulo: null, escenario: 'NORMAL', defecto: null, nombres: null, graficos: [], ocupado: false };

  // ------------------------------------------------------------ utilidades
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fmt(x) {
    if (x === null || x === undefined) return '—';
    if (typeof x === 'boolean') return x ? 'Sí' : 'No';
    if (typeof x === 'string') return esc(x);
    if (typeof x !== 'number') return esc(JSON.stringify(x));
    if (x === 0) return '0';
    if (Number.isInteger(x) && Math.abs(x) < 1e9) return String(x);
    var a = Math.abs(x);
    return (a >= 1e5 || a < 1e-3) ? x.toExponential(3) : String(Number(x.toPrecision(5)));
  }
  function tick() { return new Promise(function (r) { setTimeout(r, 40); }); }
  function msg(id, tipo, texto) { $(id).innerHTML = texto ? '<div class="msg ' + tipo + '">' + texto + '</div>' : ''; }
  function nombreEsc(e) { return ESCENARIOS[e] || e; }

  function vista(nombre) {
    ['inicio', 'modulo', 'historial'].forEach(function (v) { $('vista-' + v).classList.toggle('oculto', v !== nombre); });
    $('nav-inicio').classList.toggle('activo', nombre !== 'historial');
    $('nav-historial').classList.toggle('activo', nombre === 'historial');
    window.scrollTo(0, 0);
  }

  // ------------------------------------------------------------ inicio y módulo
  function pintarTarjetas() {
    var cont = $('tarjetas'); cont.innerHTML = '';
    [1, 2, 3, 4].forEach(function (n) {
      var d = document.createElement('article'); d.className = 'card';
      d.innerHTML = '<div class="tag">MÓDULO 0' + n + '</div><h2>' + esc(estado.nombres[n]) + '</h2><p>' + esc(MODULOS[n].pregunta) +
        '</p><div class="metodos">' + esc(MODULOS[n].metodos) + '</div><button>Configurar módulo</button>';
      d.querySelector('button').onclick = function () { abrirModulo(n); };
      cont.appendChild(d);
    });
  }

  function abrirModulo(n) {
    estado.modulo = n; estado.escenario = 'NORMAL';
    $('mod-titulo').textContent = 'Módulo ' + n + ' — ' + estado.nombres[n];
    $('mod-pregunta').textContent = MODULOS[n].pregunta;
    $('mod-metodos').textContent = 'Métodos: ' + MODULOS[n].metodos;
    $('res-modulo').innerHTML = ''; msg('mod-msg', '', '');
    pintarEscenarios(); pintarFormulario(); vista('modulo');
  }

  function pintarEscenarios() {
    var cont = $('escenarios'); cont.innerHTML = '';
    Object.keys(ESCENARIOS).forEach(function (e) {
      var b = document.createElement('button'); b.textContent = ESCENARIOS[e];
      b.className = e === estado.escenario ? 'activo' : '';
      b.onclick = function () { estado.escenario = e; pintarEscenarios(); pintarFormulario(); msg('mod-msg', '', ''); };
      cont.appendChild(b);
    });
    $('esc-desc').textContent = DESC_ESC[estado.escenario];
  }

  function pintarFormulario() {
    var p = estado.defecto[estado.modulo][estado.escenario], cont = $('formulario'); cont.innerHTML = '';
    Object.keys(p).forEach(function (k) {
      var l = document.createElement('label');
      l.innerHTML = esc((ETIQUETAS[estado.modulo] || {})[k] || k) + '<input data-clave="' + esc(k) + '" value="' +
        esc(Array.isArray(p[k]) ? p[k].join(', ') : p[k]) + '">';
      cont.appendChild(l);
    });
  }

  function leerFormulario() {
    var out = {}, errores = [];
    Array.prototype.forEach.call($('formulario').querySelectorAll('input'), function (inp) {
      var k = inp.getAttribute('data-clave'), base = estado.defecto[estado.modulo][estado.escenario][k], txt = inp.value.trim();
      if (txt === '') { errores.push('«' + k + '» está vacío'); return; }
      if (Array.isArray(base)) {
        var xs = txt.split(',').map(function (s) { return Number(s.trim().replace(',', '.')); });
        if (xs.some(function (x) { return !isFinite(x); })) { errores.push('«' + k + '» debe ser una lista de números separados por comas'); return; }
        out[k] = xs;
      } else {
        var x = Number(txt.replace(',', '.'));
        if (!isFinite(x)) { errores.push('«' + k + '» debe ser un número'); return; }
        out[k] = ENTEROS[k] ? Math.round(x) : x;
      }
    });
    return { valores: out, errores: errores };
  }

  function ejecutar() {
    if (estado.ocupado) return;
    var f = leerFormulario();
    if (f.errores.length) { msg('mod-msg', 'error', esc(f.errores.join('; '))); return; }
    var guardar = $('guardar').checked;
    estado.ocupado = true; $('ejecutar').disabled = true;
    msg('mod-msg', 'info', 'Calculando…');
    tick().then(function () {
      return T.llamar('simular', { modulo: estado.modulo, escenario: estado.escenario, parametros: f.valores, guardar: guardar });
    }).then(function (res) {
      if (guardar && res.id) return T.llamar('abrir', { id: res.id });   // se muestra lo recuperado de la base de datos
      return res;
    }).then(function (res) {
      msg('mod-msg', 'ok', res.id ? 'Simulación #' + res.id + ' ejecutada y guardada en el historial.' : 'Simulación ejecutada (no guardada).');
      mostrarResultado($('res-modulo'), res);
    }).catch(function (e) { msg('mod-msg', 'error', esc(e.message)); })
      .then(function () { estado.ocupado = false; $('ejecutar').disabled = false; });
  }

  // ------------------------------------------------------------ resultados
  function limpiarGraficos() { estado.graficos.forEach(function (c) { try { c.destroy(); } catch (e) {} }); estado.graficos = []; }

  function tablaHTML(t) {
    var h = '<div class="tablawrap"><table><caption>' + esc(t.nombre) + '</caption><thead><tr>' +
      t.columnas.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join('') + '</tr></thead><tbody>';
    t.filas.forEach(function (f) { h += '<tr>' + f.map(function (v) { return '<td>' + fmt(v) + '</td>'; }).join('') + '</tr>'; });
    return h + '</tbody></table></div>';
  }

  function mostrarResultado(cont, res) {
    limpiarGraficos();
    var cab = '<div class="panel"><h2>Resultado · Módulo ' + res.modulo + ' · ' + esc(nombreEsc(res.escenario)) + '</h2>' +
      (res.id ? '<div style="color:var(--gris);font-size:13px">Simulación #' + res.id + (res.fecha ? ' · guardada el ' + esc(res.fecha) + ' (UTC)' : '') + '</div>' : '') +
      '<div class="tabs"><button data-t="res" class="activo">Resultados</button><button data-t="graf">Gráficos</button>' +
      '<button data-t="int">Interpretación</button><button data-t="met">Métodos y registros</button></div>' +
      '<div id="t-res"></div><div id="t-graf" class="oculto"></div><div id="t-int" class="oculto"></div><div id="t-met" class="oculto"></div></div>';
    cont.innerHTML = cab;
    var raiz = cont.firstChild;
    var q = function (id) { return raiz.querySelector('#' + id); };

    q('t-res').innerHTML = '<p style="color:var(--gris);font-size:13px">Parámetros: ' +
      esc(JSON.stringify(res.parametros)) + '</p>' + res.tablas.map(tablaHTML).join('');

    var g = q('t-graf');
    g.innerHTML = '<div class="graficos">' + res.graficos.map(function (x, i) {
      return '<div class="g"><b style="color:var(--azul);font-size:13px">' + esc(x.titulo) + '</b><canvas id="gr-' + i + '"></canvas></div>';
    }).join('') + '</div>';

    var it = res.interpretacion || {};
    q('t-int').innerHTML =
      '<div class="concl numerica"><h3>Conclusión numérica (sobre los métodos)</h3>' + esc(it.numerica || '') + '</div>' +
      '<div class="concl"><h3>Conclusión del problema (sobre el fenómeno simulado)</h3>' + esc(it.problema || '') + '</div>' +
      '<div class="concl limites"><h3>Qué no puede inferirse</h3>' + esc(it.no_inferible || '') + '</div>';

    var metodos = res.metodos, m = q('t-met');
    if (metodos) {
      m.innerHTML = '<div class="tablawrap"><table><thead><tr><th>Método</th><th>Convergió</th><th>Tolerancia</th><th>Paso</th><th>Registros</th><th></th></tr></thead><tbody>' +
        metodos.map(function (x) {
          return '<tr><td>' + esc(x.metodo) + '</td><td>' + fmt(x.convergio) + '</td><td>' + fmt(x.tolerancia) + '</td><td>' + fmt(x.paso) +
            '</td><td>' + x.iteraciones + '</td><td><button class="sec" data-ej="' + x.id + '">Ver iteraciones</button></td></tr>';
        }).join('') + '</tbody></table></div><div id="iter-detalle"></div>';
      Array.prototype.forEach.call(m.querySelectorAll('button[data-ej]'), function (b) {
        b.onclick = function () { verIteraciones(m, b.getAttribute('data-ej')); };
      });
    } else {
      m.innerHTML = '<p>' + ((res.ejecuciones || []).length) + ' ejecuciones de métodos (no guardadas). Active «Guardar en el historial» para conservarlas.</p>';
    }

    Array.prototype.forEach.call(raiz.querySelectorAll('.tabs button'), function (b) {
      b.onclick = function () {
        Array.prototype.forEach.call(raiz.querySelectorAll('.tabs button'), function (x) { x.classList.toggle('activo', x === b); });
        ['res', 'graf', 'int', 'met'].forEach(function (t) { q('t-' + t).classList.toggle('oculto', t !== b.getAttribute('data-t')); });
        if (b.getAttribute('data-t') === 'graf') dibujarGraficos(res.graficos);
      };
    });
    cont.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function verIteraciones(cont, id) {
    T.llamar('iteraciones', { ejecucion_id: Number(id) }).then(function (r) {
      var filas = r.iteraciones.map(function (i) {
        return '<tr><td>' + i.numero + '</td><td>' + i.aproximacion.map(fmt).join(' ; ') + '</td><td>' + fmt(i.residual) +
          '</td><td>' + fmt(i.error_abs) + '</td><td>' + fmt(i.error_rel) + '</td></tr>';
      }).join('');
      cont.querySelector('#iter-detalle').innerHTML = '<div class="tablawrap"><table><caption>Iteraciones guardadas (' +
        r.iteraciones.length + ' de ' + r.total + ')</caption><thead><tr><th>N.º</th><th>Aproximación</th><th>Residual</th><th>Error abs.</th><th>Error rel.</th></tr></thead><tbody>' +
        filas + '</tbody></table></div>';
    }).catch(function (e) { cont.querySelector('#iter-detalle').innerHTML = '<div class="msg error">' + esc(e.message) + '</div>'; });
  }

  function dibujarGraficos(lista) {
    if (typeof Chart === 'undefined') {
      lista.forEach(function (x, i) {
        var c = document.getElementById('gr-' + i);
        if (c) c.parentNode.insertAdjacentHTML('beforeend', '<div class="msg error">No se pudo cargar la biblioteca de gráficos (se necesita conexión a internet).</div>');
      });
      return;
    }
    limpiarGraficos();
    lista.forEach(function (g, i) {
      var cv = document.getElementById('gr-' + i); if (!cv) return;
      var logY = g.escala === 'semilogy' || g.escala === 'loglog', logX = g.escala === 'loglog';
      var cat = typeof g.x[0] === 'string';
      var ds = Object.keys(g.series).map(function (nombre, k) {
        var ys = g.series[nombre];
        return { label: nombre, borderColor: COLORES[k % COLORES.length], backgroundColor: COLORES[k % COLORES.length],
                 borderWidth: 2, tension: 0, spanGaps: false, pointRadius: g.x.length > 60 ? 0 : 3,
                 data: cat ? ys : g.x.map(function (x, j) { return { x: x, y: ys[j] }; }) };
      });
      if (g.nodos) ds.push({ type: 'scatter', label: 'nodos (datos)', borderColor: '#000', backgroundColor: '#000', pointRadius: 5, showLine: false,
        data: g.nodos.x.map(function (x, j) { return { x: x, y: g.nodos.y[j] }; }) });
      var opciones = { responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: { x: cat ? { type: 'category', title: { display: !!g.xlabel, text: g.xlabel || '' } } :
                  { type: logX ? 'logarithmic' : 'linear', title: { display: !!g.xlabel, text: g.xlabel || '' } },
                  y: { type: logY ? 'logarithmic' : 'linear' } } };
      var datos = cat ? { labels: g.x, datasets: ds } : { datasets: ds };
      estado.graficos.push(new Chart(cv, { type: 'line', data: datos, options: opciones }));
    });
  }

  // ------------------------------------------------------------ historial
  function cargarHistorial() {
    msg('hist-msg', '', '');
    T.llamar('listar', { q: $('buscar').value.trim() || null }).then(function (r) {
      var t = $('tabla-historial');
      if (!r.simulaciones.length) { t.innerHTML = ''; msg('hist-msg', 'info', 'No hay simulaciones guardadas todavía. Ejecute un módulo con «Guardar en el historial».'); return; }
      t.innerHTML = '<thead><tr><th>#</th><th>Fecha (UTC)</th><th>Módulo</th><th>Escenario</th><th>Estado</th><th>Métodos</th><th></th></tr></thead><tbody>' +
        r.simulaciones.map(function (s) {
          return '<tr><td>' + s.id + '</td><td>' + esc(s.fecha) + '</td><td>' + esc(s.caso) + '</td><td>' + esc(nombreEsc(s.escenario)) +
            '</td><td>' + esc(s.estado) + '</td><td>' + s.metodos + '</td><td><button class="sec" data-a="abrir" data-id="' + s.id +
            '">Abrir</button> <button class="sec" data-a="relanzar" data-id="' + s.id + '">Relanzar</button> <button class="peligro" data-a="eliminar" data-id="' +
            s.id + '">Eliminar</button></td></tr>';
        }).join('') + '</tbody>';
      Array.prototype.forEach.call(t.querySelectorAll('button[data-a]'), function (b) {
        b.onclick = function () { accionHistorial(b.getAttribute('data-a'), Number(b.getAttribute('data-id'))); };
      });
    }).catch(function (e) { msg('hist-msg', 'error', esc(e.message)); });
  }

  function accionHistorial(accion, id) {
    if (accion === 'abrir') {
      T.llamar('abrir', { id: id }).then(function (r) { msg('hist-msg', 'info', 'Simulación #' + id + ' recuperada de la base de datos.'); mostrarResultado($('res-historial'), r); })
        .catch(function (e) { msg('hist-msg', 'error', esc(e.message)); });
    } else if (accion === 'relanzar') {
      msg('hist-msg', 'info', 'Repitiendo el cálculo de la simulación #' + id + '…');
      tick().then(function () { return T.llamar('relanzar', { id: id }); }).then(function (r) {
        var txt = 'Simulación #' + id + ' relanzada como #' + r.nueva_id + '. ' + (r.coincide ? 'Los resultados COINCIDEN' : 'Los resultados NO coinciden') +
          ' dentro de la tolerancia ' + fmt(r.tolerancia) + ' (' + r.valores_comparados + ' valores comparados, diferencia relativa máxima ' + fmt(r.max_dif_relativa) + ').';
        msg('hist-msg', r.coincide ? 'ok' : 'error', txt);
        return T.llamar('abrir', { id: r.nueva_id }).then(function (n) { mostrarResultado($('res-historial'), n); cargarHistorial(); msg('hist-msg', r.coincide ? 'ok' : 'error', txt); });
      }).catch(function (e) { msg('hist-msg', 'error', esc(e.message)); });
    } else if (accion === 'eliminar') {
      if (!window.confirm('¿Eliminar la simulación #' + id + ' del historial?')) return;
      T.llamar('eliminar', { id: id }).then(function () { $('res-historial').innerHTML = ''; cargarHistorial(); })
        .catch(function (e) { msg('hist-msg', 'error', esc(e.message)); });
    }
  }

  // ------------------------------------------------------------ arranque
  function iniciar() {
    $('nav-inicio').onclick = function () { vista('inicio'); };
    $('nav-historial').onclick = function () { vista('historial'); cargarHistorial(); };
    $('volver').onclick = function () { vista('inicio'); };
    $('ejecutar').onclick = ejecutar;
    $('restaurar').onclick = pintarFormulario;
    $('recargar').onclick = cargarHistorial;
    var t = null;
    $('buscar').oninput = function () { clearTimeout(t); t = setTimeout(cargarHistorial, 250); };

    T.iniciar(function (txt) { $('cargando-texto').textContent = txt; }).then(function (info) {
      return T.llamar('parametros').then(function (p) {
        estado.defecto = {}; Object.keys(p.parametros).forEach(function (m) { estado.defecto[Number(m)] = p.parametros[m]; });
        estado.nombres = {}; Object.keys(p.nombres).forEach(function (m) { estado.nombres[Number(m)] = p.nombres[m]; });
        $('modo').textContent = info.modo === 'flask' ? ' Cálculo en el servidor (Flask + SQLite).' :
          ' Cálculo en su navegador (Python con Pyodide); el historial se guarda en este navegador' + (info.persistente ? '.' : ' pero no es persistente en este modo de navegación.');
        pintarTarjetas();
        $('cargando').classList.add('oculto');
      });
    }).catch(function (e) {
      var ayuda = location.protocol === 'file:' ?
        'La página se abrió como archivo local (file://) y los navegadores bloquean así la carga del motor de cálculo.<br>' +
        'Ejecute <b>python iniciar.py</b> en la carpeta del proyecto y abra <b>http://127.0.0.1:5000/</b>, o use la versión publicada en GitHub Pages.' :
        'Compruebe su conexión a internet y recargue la página (Ctrl+F5).';
      $('cargando-texto').innerHTML = '<div style="max-width:560px;text-align:center">No se pudo iniciar la aplicación.<br><small>Detalle: ' +
        esc(e.message) + '</small><br><br>' + ayuda + '</div>';
      var b = document.querySelector('#cargando .barra'); if (b) b.style.display = 'none';
    });
  }

  if (typeof window !== 'undefined' && T) iniciar();
  if (typeof module !== 'undefined') module.exports = { iniciar: iniciar };
})();
