/* Leads (frontends/leads/index.html): conteos por estado, cola de visitas
   por confirmar y ficha por lead. Datos de /api/leads. */
(function () {
  'use strict';

  var esc = function (s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };
  var FIELD_LABEL = { nombre: 'Nombre', preferencia_visita: 'Visita', modalidad: 'Modalidad', email: 'Email', telefono: 'Teléfono' };
  var STATE_ORDER = ['nuevo', 'calificado', 'con_preferencia', 'datos_completos'];
  var STATE_LABEL = { nuevo: 'Nuevos', calificado: 'Calificados', con_preferencia: 'Con preferencia', datos_completos: 'Datos completos' };
  var STATE_CHIP = { nuevo: 'chip-muted', calificado: 'chip-info', con_preferencia: 'chip-warn', datos_completos: 'chip-ok' };

  function fecha(iso) {
    if (!iso) return '—';
    try {
      var d = new Date(iso);
      return d.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return iso.slice(0, 16).replace('T', ' ');
    }
  }

  function facts(lead) {
    var out = [];
    ['nombre', 'preferencia_visita', 'modalidad', 'email', 'telefono'].forEach(function (k) {
      var v = (lead.collected || {})[k];
      out.push('<span class="chip' + (v ? '' : ' chip-dashed') + '" data-testid="lead-fact-' + k + '">' + FIELD_LABEL[k] + ': ' + (v ? esc(v) : 'pendiente') + '</span>');
    });
    (lead.traits || []).forEach(function (t) {
      out.push('<span class="chip" title="' + esc(t.trait_id) + '">' + esc(t.title) + '</span>');
    });
    return out.join('');
  }

  function card(lead) {
    var estado = esc(lead.estado);
    return '<a class="leads-card" data-testid="lead-card" data-estado="' + estado + '" data-external-id="' + esc(lead.external_id) + '" href="/?user=' + encodeURIComponent(lead.external_id) + '">'
      + '<div class="leads-main"><div class="leads-who">' + esc((lead.collected || {}).nombre || lead.external_id) + '</div>'
      + '<div class="leads-first">' + (lead.primer_mensaje ? esc(lead.primer_mensaje) : 'sin mensajes') + '</div>'
      + '<div class="chips">' + facts(lead) + '</div></div>'
      + '<div class="leads-side"><span class="chip leads-badge ' + (STATE_CHIP[lead.estado] || 'chip-muted') + ' ' + estado + '" data-testid="lead-badge">' + esc(lead.estado_label) + '</span>'
      + '<div class="leads-meta">' + esc(lead.channel || '—') + ' · ' + lead.n_turnos + ' turnos<br>' + fecha(lead.last_active) + '</div></div></a>';
  }

  function empty(icon, text) {
    return '<div class="empty-state"><span class="empty-state-icon">' + icon + '</span>' + text + '</div>';
  }

  function render(d) {
    var counts = d.counts || {};
    document.getElementById('counts').innerHTML = STATE_ORDER.map(function (k) {
      return '<div class="kpi" data-testid="count-' + k + '"><div class="kpi-label">' + STATE_LABEL[k] + '</div><div class="kpi-value">' + (counts[k] || 0) + '</div></div>';
    }).join('');
    var q = d.queue || [];
    document.getElementById('queue').innerHTML = q.length ? q.map(card).join('') : empty('📅', 'Nadie pidió visita todavía.');
    var leads = d.leads || [];
    document.getElementById('leads').innerHTML = leads.length ? leads.map(card).join('') : empty('📭', 'Sin leads todavía. Aparecen cuando alguien escribe al agente.');
    if (window.initGlossaryTooltips) initGlossaryTooltips();
  }

  fetch('/api/leads').then(function (r) { return r.json(); }).then(render).catch(function (e) {
    document.getElementById('counts').innerHTML = '';
    document.getElementById('queue').innerHTML = '';
    document.getElementById('leads').innerHTML = '<div class="error-state">No se pudo cargar: ' + esc(e.message || e) + '</div>';
  });

  if (window.initGlossaryTooltips) initGlossaryTooltips();
  if (window.DemoTour) DemoTour.run();
})();
