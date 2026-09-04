/* Topbar comun a todas las vistas: marca, etiquetas, health y grupos.
 *
 * Antes cada pagina llevaba una copia del mismo IIFE (5 copias que se
 * desincronizaban: agregar una vista obligaba a editarlas todas). Los <a>
 * siguen en el HTML de cada pagina -- son parte del contrato de tests
 * (data-testid="nav-chat", "nav-leads", ...) y deben existir sin esperar a
 * /api/config; este script solo los agrupa, los rotula y marca el activo.
 *
 * Grupos (UI-GUIDE 1): Chat (producto) · Operacion (leads, metricas) ·
 * Desarrollo (inspector, flujo, KB). El grupo se declara por data-nav-group
 * en cada <a>; el separador lo dibuja CSS (.app-nav a[data-group-start]).
 */
(function () {
  var GROUPS = { chat: 'Chat', operacion: 'Operación', desarrollo: 'Desarrollo' };
  var DEFAULT_LABELS = {
    chat: 'Chat', leads: 'Leads', dashboard: 'Métricas',
    inspector: 'Inspector', flow: 'Flujo', mindmap: 'KB', users: 'Perfiles'
  };

  function markActive() {
    var path = location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('#appNav a').forEach(function (a) {
      var href = a.getAttribute('href').replace(/\/$/, '') || '/';
      var active = href === path;
      a.classList.toggle('active', active);
      if (active) a.setAttribute('data-active', 'true');
      else a.removeAttribute('data-active');
    });
  }

  function markGroups() {
    var seen = {};
    document.querySelectorAll('#appNav a').forEach(function (a) {
      var g = a.getAttribute('data-nav-group');
      if (!g || seen[g]) return;
      seen[g] = true;
      a.setAttribute('data-group-start', 'true');
      if (GROUPS[g]) a.setAttribute('data-group-label', GROUPS[g]);
    });
  }

  function applyConfig(cfg, health) {
    var brand = document.getElementById('appBrand');
    var kb = document.getElementById('kbLabel');
    var hl = document.getElementById('healthLabel');
    if (brand) brand.textContent = cfg.name || cfg.runtime_title || 'Agente';
    if (kb) kb.textContent = cfg.kb_label || cfg.name || 'KB';
    if (hl) hl.textContent = health.status || 'unknown';
    var labels = cfg.nav_labels || {};
    Object.keys(DEFAULT_LABELS).forEach(function (key) {
      var el = document.querySelector('[data-testid="nav-' + key + '"]');
      if (el) el.textContent = labels[key] || DEFAULT_LABELS[key];
    });
    var input = document.querySelector('[data-testid="chat-input"]');
    if (input && cfg.input_placeholder) input.placeholder = cfg.input_placeholder;
  }

  function boot() {
    markActive();
    markGroups();
    Promise.all([
      fetch('/api/config').then(function (r) { return r.json() }).catch(function () { return {} }),
      fetch('/api/health').then(function (r) { return r.json() }).catch(function () { return {} })
    ]).then(function (res) { applyConfig(res[0] || {}, res[1] || {}) });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
