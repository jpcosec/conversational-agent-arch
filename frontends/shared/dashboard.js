/* Metricas (frontends/dashboard/index.html): KPIs, turnos por dia, tipo de
   respuesta y leads por estado. Datos de /api/metrics. */
(function () {
  'use strict';

  var esc = function (s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };
  // Label humano por tipo de respuesta; el valor crudo va en un chip al lado.
  var KIND_LABEL = { nl: 'Respuesta libre', fallback: 'No supe responder', tool_call: 'Ejecutó una tool', derived: 'Derivado a una persona', desconocido: 'Sin clasificar' };
  var KIND_TIP = { nl: 'nl', fallback: 'fallback', tool_call: 'tool_call', derived: 'derivado' };
  var LEAD_LABEL = { nuevo: 'Nuevos', calificado: 'Calificados', con_preferencia: 'Con preferencia de visita', datos_completos: 'Datos completos' };

  function ms(v) { return v == null ? '—' : (v >= 1000 ? (v / 1000).toFixed(1) + ' s' : v + ' ms'); }

  function empty(icon, text, inline) {
    return '<div class="empty-state' + (inline ? ' empty-state-inline' : '') + '"><span class="empty-state-icon">' + icon + '</span>' + text + '</div>';
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function renderKpis(d) {
    var lat = d.latencia_ms || {};
    var kpis = [
      { k: 'turnos', label: 'Turnos', value: d.turnos, sub: (d.usuarios || 0) + ' usuarios · ' + (d.leads_total || 0) + ' leads' },
      { k: 'fallback', label: '<span data-tooltip="fallback">Sin respuesta útil</span>', value: (d.fallback_pct || 0) + '%', sub: (d.fallback_n || 0) + ' turnos en que el agente no supo responder', cls: (d.fallback_pct > 20 ? 'bad' : d.fallback_pct > 5 ? 'warn' : '') },
      { k: 'derivados', label: '<span data-tooltip="gate">Derivados a una persona</span>', value: (d.derivados_pct || 0) + '%', sub: (d.derivados_n || 0) + ' borradores rechazados por la validación', cls: (d.derivados_pct > 15 ? 'warn' : '') },
      { k: 'visitas', label: 'Visitas por confirmar', value: d.visitas_por_confirmar || 0, sub: 'esperan hora del equipo' },
      { k: 'latencia', label: '<span data-tooltip="latencia">Latencia mediana</span>', value: ms(lat.mediana), sub: 'p90 ' + ms(lat.p90) + ' · ' + (lat.n || 0) + ' turnos medidos' }
    ];
    document.getElementById('kpis').innerHTML = kpis.map(function (x) {
      return '<div class="kpi ' + (x.cls || '') + '" data-testid="kpi-' + x.k + '"><div class="kpi-label">' + x.label + '</div><div class="kpi-value">' + esc(x.value) + '</div><div class="kpi-sub">' + esc(x.sub) + '</div></div>';
    }).join('');
  }

  // La altura de cada barra es dinamica: se fija por JS (el.style.height),
  // nunca con style="" en el HTML.
  function renderBars(d) {
    var box = document.getElementById('bars');
    var dias = d.por_dia || [];
    box.innerHTML = '';
    if (!dias.length) { box.innerHTML = empty('📊', 'Sin turnos todavía.'); return; }
    var max = Math.max.apply(null, dias.map(function (x) { return x.turnos; }).concat([1]));
    dias.forEach(function (x) {
      var col = el('div', 'dash-bar-col');
      col.setAttribute('data-testid', 'metrics-bar');
      col.appendChild(el('span', 'dash-bar-n', String(x.turnos)));
      var bar = el('div', 'dash-bar');
      bar.style.height = Math.round(100 * x.turnos / max) + '%';
      col.appendChild(bar);
      col.appendChild(el('span', 'dash-bar-d', String(x.dia).slice(5)));
      box.appendChild(col);
    });
  }

  function renderKinds(d) {
    var kinds = d.kinds || {}, tot = d.turnos || 0;
    document.getElementById('kinds').innerHTML = Object.keys(kinds).sort(function (a, b) { return kinds[b] - kinds[a]; }).map(function (k) {
      var label = KIND_LABEL[k] ? (KIND_TIP[k] ? '<span data-tooltip="' + KIND_TIP[k] + '">' + KIND_LABEL[k] + '</span>' : KIND_LABEL[k]) : esc(k);
      return '<tr><td>' + label + '<span class="chip chip-muted dash-kind-raw">' + esc(k) + '</span></td><td class="num">' + kinds[k] + '</td><td class="num">' + (tot ? Math.round(1000 * kinds[k] / tot) / 10 : 0) + '%</td></tr>';
    }).join('') || '<tr><td colspan="3">' + empty('📊', 'Sin turnos todavía.', true) + '</td></tr>';
  }

  function renderLeads(d) {
    var leads = d.leads || {};
    document.getElementById('leadRows').innerHTML = ['nuevo', 'calificado', 'con_preferencia', 'datos_completos'].map(function (k) {
      return '<tr><td>' + esc(LEAD_LABEL[k]) + '</td><td class="num">' + (leads[k] || 0) + '</td></tr>';
    }).join('');
  }

  fetch('/api/metrics').then(function (r) { return r.json(); }).then(function (d) {
    renderKpis(d);
    renderBars(d);
    renderKinds(d);
    renderLeads(d);
    if (window.initGlossaryTooltips) initGlossaryTooltips();
  }).catch(function (e) {
    document.getElementById('kpis').innerHTML = '<div class="error-state">No se pudo cargar: ' + esc(e.message || e) + '</div>';
    document.getElementById('bars').innerHTML = '';
    document.getElementById('kinds').innerHTML = '';
    document.getElementById('leadRows').innerHTML = '';
  });

  if (window.initGlossaryTooltips) initGlossaryTooltips();
  if (window.DemoTour) DemoTour.run();
})();
