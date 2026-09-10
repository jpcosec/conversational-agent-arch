/* Metricas (frontends/dashboard/index.html): datos de /api/metrics reales,
   estetica del mock fab8344 (KPI cards con sparkline, chart de linea con
   gradiente, barras horizontales). Sin inline: todo DOM o clases. */
(function () {
  'use strict';

  var esc = function (s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };
  var KIND_LABEL = { nl: 'Respuesta libre', fallback: 'No supe responder', tool_call: 'Ejecutó una tool', derived: 'Derivado a una persona' };
  var KIND_COLOR = { nl: 'var(--family-self)', fallback: 'var(--danger)', tool_call: 'var(--family-conversation)', derived: 'var(--family-user)' };
  var LEAD_LABEL = { nuevo: 'Nuevos', calificado: 'Calificados', con_preferencia: 'Con preferencia', datos_completos: 'Datos completos' };

  function ms(v) { return v == null ? '—' : (v >= 1000 ? (v / 1000).toFixed(1) + ' s' : v + ' ms'); }

  function empty(icon, text, inline) {
    return '<div class="empty-state' + (inline ? ' empty-state-inline' : '') + '"><span class="empty-state-icon">' + icon + '</span>' + text + '</div>';
  }

  // ---- sparkline SVG (misma tecnica del mock fab8344, datos reales) ----
  function sparkPath(data, w, h, pad) {
    var mn = Math.min.apply(0, data), mx = Math.max.apply(0, data), rg = (mx - mn) || 1;
    return data.map(function (v, i) {
      var x = pad + i / (data.length - 1) * (w - 2 * pad);
      var y = h - pad - (v - mn) / rg * (h - 2 * pad);
      return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
    }).join(' ');
  }

  function renderSpark(node, data, color) {
    var w = 260, h = 70, pad = 6;
    if (data.length < 2) { node.innerHTML = empty('📈', 'Serie en construcción', true); return; }
    var d = sparkPath(data, w, h, pad);
    var id = 'g' + Math.random().toString(36).slice(2);
    node.innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" height="' + h + '" preserveAspectRatio="none" role="img">' +
      '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="' + color + '" stop-opacity=".28"/><stop offset="1" stop-color="' + color + '" stop-opacity="0"/></linearGradient></defs>' +
      '<path d="' + d + ' L' + (w - pad) + ' ' + (h - pad) + ' L' + pad + ' ' + (h - pad) + ' Z" fill="url(#' + id + ')"/>' +
      '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="2" stroke-linejoin="round"/></svg>';
  }

  // ---- KPI cards ----
  function kpiCard(k) {
    var c = document.createElement('div');
    c.className = 'db-card';
    c.setAttribute('data-testid', 'kpi-' + k.k);
    var spark = '<div class="db-spark"></div>';
    c.innerHTML = '<div class="db-card-head"><div class="db-badge ' + k.badgeCls + '">' + k.icon + '</div>' +
      '<div class="db-card-title">' + k.label + '</div><span class="db-info" title="' + esc(k.title || '') + '">ⓘ</span></div>' +
      '<div class="db-big ' + (k.cls || '') + '">' + esc(k.value) + (k.u ? '<span class="u">' + esc(k.u) + '</span>' : '') + '</div>' +
      '<div class="db-delta"><b>' + k.delta + '</b> <span>' + esc(k.sub) + '</span></div>' + spark;
    if (k.series) renderSpark(c.querySelector('.db-spark'), k.series, k.color || 'var(--accent)');
    else c.querySelector('.db-spark').innerHTML = empty('·', k.note || 'Sin serie diaria', true);
    return c;
  }

  function renderKpis(d, porDia) {
    var lat = d.latencia_ms || {};
    var serieTurnos = porDia.map(function (x) { return x.turnos; });
    var kpis = [
      { k: 'turnos', icon: '💬', badgeCls: 'badge-user', color: 'var(--family-user)', label: 'Turnos', value: d.turnos, delta: (d.usuarios || 0) + ' usuarios', sub: (d.leads_total || 0) + ' leads en la base', series: serieTurnos, title: 'Mensajes del cliente respondidos por el agente' },
      { k: 'fallback', icon: '∅', badgeCls: 'badge-danger', color: 'var(--danger)', label: 'Sin respuesta útil', value: (d.fallback_pct || 0) + '%', delta: d.fallback_n + ' turnos', sub: 'el agente no supo responder', cls: (d.fallback_pct > 20 ? 'db-warn' : ''), series: [], note: 'Serie por día no instrumentada', title: 'Turnos que terminaron en fallback' },
      { k: 'derivados', icon: '🚦', badgeCls: 'badge-gate', color: 'var(--family-conversation)', label: 'Derivados a una persona', value: (d.derivados_pct || 0) + '%', delta: d.derivados_n + ' borradores', sub: 'rechazados por la validación', series: [], note: 'Serie por día no instrumentada', title: 'El policy gate derivó el turno a un humano' },
      { k: 'visitas', icon: '📅', badgeCls: 'badge-accent', color: 'var(--accent)', label: 'Visitas por confirmar', value: d.visitas_por_confirmar || 0, delta: 'cola del equipo', sub: 'esperan hora del equipo', series: [], note: 'Estado actual de la cola', title: 'Leads con preferencia de visita sin hora confirmada' },
      { k: 'latencia', icon: '◷', badgeCls: 'badge-self', color: 'var(--family-self)', label: 'Latencia mediana', value: ms(lat.mediana), delta: 'p90 ' + ms(lat.p90), sub: (lat.n || 0) + ' turnos medidos', series: [], note: 'Snapshot actual', title: 'Tiempo entre el mensaje del cliente y la respuesta' }
    ];
    var wrap = document.getElementById('kpis');
    wrap.innerHTML = '';
    kpis.forEach(function (k) { wrap.appendChild(kpiCard(k)); });
  }

  // ---- chart de linea grande (turnos por dia / por semana) ----
  function bigChart(node, cur, labels, color) {
    if (cur.length < 2) { node.innerHTML = empty('📊', 'Sin turnos todavía.'); return; }
    var w = 560, h = 260, pl = 42, pr = 14, pt = 14, pb = 28;
    var iw = w - pl - pr, ih = h - pt - pb;
    var mx = Math.max.apply(0, cur) || 1;
    function X(i) { return pl + i / (cur.length - 1) * iw; }
    function Y(v) { return pt + ih - v / mx * ih; }
    var line = cur.map(function (v, i) { return (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1); }).join(' ');
    var area = line + ' L' + X(cur.length - 1).toFixed(1) + ' ' + (pt + ih) + ' L' + pl + ' ' + (pt + ih) + ' Z';
    var id = 'c' + Math.random().toString(36).slice(2);
    var grid = '', lbl = '';
    var yMax = mx, yTicks = [];
    var step = yMax <= 5 ? 1 : Math.ceil(yMax / 4);
    for (var t = 0; t <= yMax; t += step) yTicks.push(t);
    if (yTicks[yTicks.length - 1] !== yMax) yTicks.push(yMax);
    yTicks.forEach(function (t) {
      var y = Y(t);
      grid += '<line x1="' + pl + '" y1="' + y + '" x2="' + (w - pr) + '" y2="' + y + '" stroke="var(--border)" stroke-width="1"/>';
      lbl += '<text class="db-axis" x="' + (pl - 8) + '" y="' + (y + 3) + '" text-anchor="end">' + t + '</text>';
    });
    var nLab = Math.min(labels.length, 6);
    var xax = '';
    for (var i = 0; i < nLab; i++) {
      var li = Math.round(i * (labels.length - 1) / (nLab - 1 || 1));
      xax += '<text class="db-axis" x="' + X(li).toFixed(1) + '" y="' + (h - 8) + '" text-anchor="middle">' + esc(labels[li]) + '</text>';
    }
    var dots = cur.map(function (v, i) { return '<circle cx="' + X(i).toFixed(1) + '" cy="' + Y(v).toFixed(1) + '" r="2.4" fill="' + color + '"/>'; }).join('');
    node.innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" role="img">' +
      '<defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="' + color + '" stop-opacity=".22"/><stop offset="1" stop-color="' + color + '" stop-opacity="0"/></linearGradient></defs>' +
      grid + lbl + xax +
      '<path d="' + area + '" fill="url(#' + id + ')"/>' +
      '<path d="' + line + '" fill="none" stroke="' + color + '" stroke-width="2.2" stroke-linejoin="round"/>' + dots + '</svg>';
  }

  function groupByWeek(porDia) {
    var weeks = {}, order = [];
    porDia.forEach(function (x) {
      var dt = new Date(x.dia + 'T00:00:00');
      var day = (dt.getDay() + 6) % 7; // lunes = 0
      dt.setDate(dt.getDate() - day);
      var wk = dt.toISOString().slice(0, 10);
      if (!weeks[wk]) { weeks[wk] = 0; order.push(wk); }
      weeks[wk] += x.turnos;
    });
    return { labels: order, values: order.map(function (k) { return weeks[k]; }) };
  }

  function renderChart(d) {
    var porDia = d.por_dia || [];
    var gran = document.getElementById('dbGranularity').value;
    var labels = porDia.map(function (x) { return String(x.dia).slice(5); });
    var values = porDia.map(function (x) { return x.turnos; });
    if (gran === 'semana') {
      var wk = groupByWeek(porDia);
      labels = wk.labels.map(function (l) { return l.slice(5); });
      values = wk.values;
    }
    bigChart(document.getElementById('chartTurnos'), values, labels, 'var(--family-user)');
  }

  // ---- barras horizontales (tipos, leads, latencia) ----
  function hbarRows(rows, total) {
    if (!rows.length) return empty('📊', 'Sin datos todavía.', true);
    var mx = Math.max.apply(0, rows.map(function (r) { return r.v; })) || 1;
    return rows.map(function (r) {
      return '<div class="db-hbar-row"><div class="db-hbar-label">' + r.label + '</div>' +
        '<div class="db-hbar-track"><div class="db-hbar' + (r.cls ? ' ' + r.cls : '') + '" data-w="' + Math.round(100 * r.v / mx) + '"></div></div>' +
        '<div class="db-hbar-n">' + (total != null && total ? Math.round(1000 * r.v / total) / 10 + '%' : esc(r.v)) + '</div></div>';
    }).join('');
  }

  function paintBars(container) {
    container.querySelectorAll('.db-hbar[data-w]').forEach(function (b) {
      b.style.width = b.getAttribute('data-w') + '%';
    });
  }

  function renderKinds(d) {
    var kinds = d.kinds || {}, tot = d.turnos || 0;
    var rows = Object.keys(kinds).sort(function (a, b) { return kinds[b] - kinds[a]; }).map(function (k) {
      return { label: (KIND_LABEL[k] || k) + ' <span class="chip chip-muted">' + esc(k) + '</span>', v: kinds[k], cls: '' };
    });
    var box = document.getElementById('kindsPanel');
    box.innerHTML = hbarRows(rows, tot);
    paintBars(box);
    document.getElementById('kindsLegend').innerHTML = Object.keys(kinds).map(function (k) {
      return '<div class="db-legend-item"><span class="db-legend-dot" data-kind="' + esc(k) + '"></span>' + esc(KIND_LABEL[k] || k) + '</div>';
    }).join('');
  }

  function renderLeads(d) {
    var leads = d.leads || {};
    var tot = d.leads_total || 0;
    var rows = ['nuevo', 'calificado', 'con_preferencia', 'datos_completos'].map(function (k) {
      return { label: LEAD_LABEL[k], v: leads[k] || 0 };
    });
    var box = document.getElementById('leadsPanel');
    box.innerHTML = hbarRows(rows, tot);
    paintBars(box);
    document.getElementById('leadsLegend').innerHTML = '<div class="db-legend-item">Total: ' + tot + ' leads</div>';
  }

  function renderLatency(d) {
    var lat = d.latencia_ms || {};
    var mx = lat.max || 1;
    var rows = [
      { label: 'Mediana', v: lat.mediana || 0 },
      { label: 'p90', v: lat.p90 || 0 },
      { label: 'Máximo', v: lat.max || 0 }
    ];
    var html = rows.map(function (r) {
      return '<div class="db-hbar-row"><div class="db-hbar-label">' + r.label + '</div>' +
        '<div class="db-hbar-track"><div class="db-hbar" data-lat="' + r.v + '" data-mx="' + mx + '"></div></div>' +
        '<div class="db-hbar-n">' + ms(r.v) + '</div></div>';
    }).join('') || empty('⏱', 'Sin turnos medidos.', true);
    var box = document.getElementById('latencyPanel');
    box.innerHTML = html;
    box.querySelectorAll('.db-hbar[data-lat]').forEach(function (b) {
      b.style.width = Math.max(2, Math.round(100 * (+b.getAttribute('data-lat')) / (+b.getAttribute('data-mx') || 1))) + '%';
    });
  }

  function fmtWindow(d) {
    var porDia = d.por_dia || [];
    if (!porDia.length) return 'sin datos';
    return porDia[0].dia + ' – ' + porDia[porDia.length - 1].dia;
  }

  function load() {
    return fetch('/api/metrics').then(function (r) { return r.json(); }).then(function (d) {
      renderKpis(d, d.por_dia || []);
      renderChart(d);
      renderKinds(d);
      renderLeads(d);
      renderLatency(d);
      document.getElementById('dbWindow').textContent = fmtWindow(d);
      document.getElementById('dbDays').textContent = d.days || '—';
      document.getElementById('ts').textContent = new Date().toLocaleString('es', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }).catch(function (e) {
      document.getElementById('kpis').innerHTML = empty('⚠️', 'No se pudieron cargar las métricas: ' + esc(e.message));
    });
  }

  document.getElementById('dbGranularity').addEventListener('change', function () {
    fetch('/api/metrics').then(function (r) { return r.json(); }).then(renderChart);
  });

  load();
})();
