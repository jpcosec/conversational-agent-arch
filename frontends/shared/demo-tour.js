/* Demo Tour — un ÚNICO recorrido guiado que cruza las 4 vistas.
 *
 * Cuadros flotantes que APUNTAN a elementos con una flecha + anillo de
 * resaltado. "Siguiente" (o Enter / →) avanza de cuadro; al terminar los
 * cuadros de una vista, NAVEGA solo a la siguiente vista y continúa desde
 * donde iba. El progreso se guarda en localStorage para sobrevivir el cambio
 * de página (cada vista es un HTML distinto).
 *
 * Uso (idéntico en las 4 páginas):
 *   <script src="/static/demo-tour.js"></script>
 *   <script>DemoTour.run();</script>
 *
 * Los pasos son globales (DEMO_TOUR_STEPS abajo): cada uno declara `route`
 * (la vista donde vive) + `selector` + textos. Sin dependencias.
 */
(function (global) {
  var KEY_IDX = 'demo-tour-idx';
  var KEY_DONE = 'demo-tour-done';

  // ── Pasos del recorrido completo, en orden, a través de las 4 vistas ──────
  var STEPS = [
    // Chat (/)
    { route: '/', selector: '[data-testid="nav-topbar"]', title: 'Bienvenido a la demo', text: 'Este es un agente conversacional auditable. Te muestro las 4 vistas. Usa <b>Siguiente</b> o <b>Enter</b> para avanzar; el tour cambia de vista solo.', placement: 'bottom' },
    { route: '/', selector: '[data-testid="chat-input"]', title: 'Conversa aquí', text: 'Escribe como una paciente. Para la demo envío un mensaje de ejemplo (<b>“quiero un recordatorio para el lunes a las 20”</b>) y abajo verás cómo se puebla la auditoría →', placement: 'top', onShow: 'chatSeed' },
    { route: '/', selector: '[data-testid="inspector-summary"]', title: 'Summary del turno', text: 'Intención, step del flujo y tool ejecutada en la última respuesta del agente.', placement: 'left' },
    { route: '/', selector: '[data-testid="inspector-context"]', title: 'Contexto', text: 'Los documentos que entraron a responder, agrupados por familia. Cada card explica <b>por qué</b> entró.', placement: 'left' },
    { route: '/', selector: '[data-testid="inspector-reasoning"]', title: 'Razonamiento', text: 'Los 5 agentes del pipeline: Ruteador, Orquestador, Conversador, Gate y Perfilador. Click para expandir cada uno.', placement: 'left' },
    // Flow (/flow)
    { route: '/flow', selector: '[data-testid="flow-palette"]', title: 'Flow · pasos', text: 'El flujo conversacional como grafo. Cada nodo es un paso; arrastra tipos desde esta paleta.', placement: 'right' },
    { route: '/flow', selector: '[data-testid="flow-tools-panel"]', title: 'Tools de la KB', text: 'Las capacidades del backend que el flujo puede disparar (p. ej. agendar recordatorio).', placement: 'right' },
    { route: '/flow', selector: '[data-testid="flow-inspector"]', title: 'Editor del paso', text: 'Haz click en un nodo del canvas y aquí ves/editas instrucciones, slots, transiciones y grounding.', placement: 'left' },
    // Mindmap (/mindmap)
    { route: '/mindmap', selector: '[data-testid="mindmap-sidebar"]', title: 'Mindmap · familias', text: 'Toda la base de conocimiento por familias. Filtra una rama o cambia el layout aquí.', placement: 'right' },
    { route: '/mindmap', selector: '[data-testid="mindmap-search"]', title: 'Buscar y layouts', text: 'Busca nodos y alterna Árbol / Top-down / Embeddings (cercanía semántica).', placement: 'bottom' },
    // Users (/users)
    { route: '/users', selector: '[data-testid="users-list"]', title: 'Users · perfiles', text: 'Usuarios de ejemplo. Selecciona uno para ver su detalle.', placement: 'right' },
    { route: '/users', selector: '[data-testid="users-view-selector"]', title: 'Perfil, eventos, conversaciones', text: 'Cada pestaña muestra rasgos aprendidos, series de actividad y sesiones pasadas. ¡Fin del recorrido!', placement: 'bottom' }
  ];

  var CSS = [
    '.dt-ring{position:fixed;z-index:99998;border:2px solid #d4a574;border-radius:10px;box-shadow:0 0 0 9999px rgba(10,10,15,.55);pointer-events:none;transition:all .2s ease}',
    '.dt-box{position:fixed;z-index:99999;max-width:308px;background:linear-gradient(180deg,rgba(24,20,14,.98),rgba(14,12,9,.98));border:1px solid #d4a574;border-radius:12px;padding:14px 16px;box-shadow:0 16px 44px rgba(0,0,0,.6);font-family:Inter,system-ui,sans-serif;color:#f5f0e8}',
    '.dt-kicker{font-family:"JetBrains Mono",monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:#d4a574;margin-bottom:6px}',
    '.dt-title{font-size:15px;font-weight:600;margin-bottom:6px;line-height:1.2}',
    '.dt-text{font-size:12.5px;line-height:1.55;color:rgba(245,240,232,.82)}',
    '.dt-nav{display:flex;align-items:center;gap:8px;margin-top:12px}',
    '.dt-progress{font-family:"JetBrains Mono",monospace;font-size:10px;color:rgba(245,240,232,.45);margin-right:auto}',
    '.dt-btn{font-family:"JetBrains Mono",monospace;font-size:11px;padding:5px 12px;border-radius:7px;border:1px solid rgba(212,165,116,.35);background:transparent;color:rgba(245,240,232,.75);cursor:pointer;transition:.15s}',
    '.dt-btn:hover{border-color:#d4a574;color:#d4a574}',
    '.dt-btn.dt-primary{background:#d4a574;border-color:#d4a574;color:#0a0a0f;font-weight:600}',
    '.dt-btn.dt-primary:hover{background:#c49560}',
    '.dt-arrow{position:fixed;z-index:99999;width:14px;height:14px;background:linear-gradient(135deg,rgba(24,20,14,.98),rgba(14,12,9,.98));border:1px solid #d4a574;transform:rotate(45deg);pointer-events:none}',
    '.dt-launch{position:fixed;z-index:99997;bottom:18px;left:18px;font-family:"JetBrains Mono",monospace;font-size:11px;padding:8px 14px;border-radius:999px;border:1px solid rgba(212,165,116,.4);background:rgba(18,18,26,.92);color:#d4a574;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.4)}',
    '.dt-launch:hover{background:rgba(212,165,116,.15)}'
  ].join('');

  function norm(p) { p = (p || location.pathname || '/').replace(/\/+$/, ''); return p === '' ? '/' : p; }
  function getIdx() { try { return parseInt(localStorage.getItem(KEY_IDX) || '0', 10) || 0; } catch (e) { return 0; } }
  function setIdx(i) { try { localStorage.setItem(KEY_IDX, String(i)); } catch (e) {} }
  function isDone() { try { return localStorage.getItem(KEY_DONE) === '1'; } catch (e) { return false; } }
  function setDone(v) { try { v ? localStorage.setItem(KEY_DONE, '1') : localStorage.removeItem(KEY_DONE); } catch (e) {} }

  function injectCSS() {
    if (document.getElementById('dt-style')) return;
    var s = document.createElement('style'); s.id = 'dt-style'; s.textContent = CSS; document.head.appendChild(s);
  }
  function el(cls, testid) { var d = document.createElement('div'); d.className = cls; if (testid) d.setAttribute('data-testid', testid); return d; }

  var Tour = {
    ring: null, box: null, arrow: null, onResize: null, onKey: null,

    launcher: function () {
      if (document.querySelector('.dt-launch')) return;
      var b = el('dt-launch', 'demo-tour-launch');
      b.textContent = '❓ Guía demo';
      b.onclick = function () { setDone(false); setIdx(0); Tour.go(0); };
      document.body.appendChild(b);
    },

    // Navega al índice global i: si su vista es otra, cambia de página.
    go: function (i) {
      if (i < 0) i = 0;
      if (i >= STEPS.length) { this.finish(); return; }
      setIdx(i);
      var step = STEPS[i];
      if (norm(step.route) !== norm()) {
        // cruzar de vista: la página destino retoma el tour al cargar
        location.href = step.route;
        return;
      }
      this.render(i);
    },

    next: function () { this.go(getIdx() + 1); },
    prev: function () { this.go(getIdx() - 1); },

    finish: function () { setDone(true); this.cleanup(); },

    cleanup: function () {
      [this.ring, this.box, this.arrow].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
      this.ring = this.box = this.arrow = null;
      if (this.onResize) { window.removeEventListener('resize', this.onResize); window.removeEventListener('scroll', this.onResize, true); this.onResize = null; }
      if (this.onKey) { window.removeEventListener('keydown', this.onKey); this.onKey = null; }
    },

    waitFor: function (selector, cb, tries) {
      tries = tries == null ? 40 : tries;
      var f = document.querySelector(selector);
      if (f || tries <= 0) { cb(f); return; }
      setTimeout(function () { Tour.waitFor(selector, cb, tries - 1); }, 100);
    },

    // Acciones opcionales antes de pintar un paso (poblar la UI para la demo).
    hooks: {
      chatSeed: function (done) {
        // si aun no hay respuesta del asistente, envia un mensaje de ejemplo
        var inp = document.querySelector('[data-testid="chat-input"]');
        var send = document.querySelector('[data-testid="chat-send"]');
        var hasTurn = document.querySelector('[data-testid^="context-atom-"]');
        if (!inp || !send || hasTurn) { done(); return; }
        var setVal = function (v) {
          var proto = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
          proto.set.call(inp, v);
          inp.dispatchEvent(new Event('input', { bubbles: true }));
        };
        setVal('quiero un recordatorio para el lunes a las 20');
        send.click();
        var tries = 60;
        (function wait() {
          if (document.querySelector('[data-testid="inspector-summary"]') || tries-- <= 0) { done(); return; }
          setTimeout(wait, 150);
        })();
      }
    },

    render: function (i) {
      var step = STEPS[i];
      var proceed = function () {
        Tour.waitFor(step.selector, function (target) {
          if (!target) { Tour.go(i + 1); return; } // target ausente: saltar
          Tour.paint(i, step, target);
        });
      };
      if (step.onShow && this.hooks[step.onShow]) { this.hooks[step.onShow](proceed); }
      else { proceed(); }
    },

    paint: function (i, step, target) {
      injectCSS();
      if (!this.box) {
        this.ring = el('dt-ring'); this.arrow = el('dt-arrow'); this.box = el('dt-box', 'demo-tour');
        document.body.appendChild(this.ring); document.body.appendChild(this.arrow); document.body.appendChild(this.box);
        this.onResize = function () { var s = STEPS[getIdx()]; if (s) { var t = document.querySelector(s.selector); if (t) Tour.position(s, t); } };
        window.addEventListener('resize', this.onResize); window.addEventListener('scroll', this.onResize, true);
        this.onKey = function (e) {
          if (e.key === 'Enter' || e.key === 'ArrowRight') { e.preventDefault(); Tour.next(); }
          else if (e.key === 'ArrowLeft') { e.preventDefault(); Tour.prev(); }
          else if (e.key === 'Escape') { e.preventDefault(); Tour.finish(); }
        };
        window.addEventListener('keydown', this.onKey);
      }
      var last = i === STEPS.length - 1;
      this.box.innerHTML = '';
      var k = el('dt-kicker'); k.textContent = 'Guía demo · ' + (norm(step.route) === '/' ? 'Chat' : step.route.replace('/', ''));
      var t = el('dt-title'); t.textContent = step.title || '';
      var x = el('dt-text'); x.innerHTML = step.text || '';
      var nav = el('dt-nav');
      var prog = el('dt-progress'); prog.textContent = (i + 1) + ' / ' + STEPS.length;
      nav.appendChild(prog);
      if (i > 0) { var pv = el('dt-btn', 'demo-tour-prev'); pv.textContent = '‹ Atrás'; pv.onclick = function () { Tour.prev(); }; nav.appendChild(pv); }
      var sk = el('dt-btn', 'demo-tour-close'); sk.textContent = 'Cerrar'; sk.onclick = function () { Tour.finish(); }; nav.appendChild(sk);
      var nx = el('dt-btn dt-primary', 'demo-tour-next'); nx.textContent = last ? 'Listo' : 'Siguiente ›'; nx.onclick = function () { Tour.next(); }; nav.appendChild(nx);
      this.box.appendChild(k); this.box.appendChild(t); this.box.appendChild(x); this.box.appendChild(nav);
      try { target.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' }); } catch (e) {}
      this.position(step, target);
    },

    position: function (step, target) {
      var r = target.getBoundingClientRect(), pad = 6;
      this.ring.style.left = (r.left - pad) + 'px'; this.ring.style.top = (r.top - pad) + 'px';
      this.ring.style.width = (r.width + pad * 2) + 'px'; this.ring.style.height = (r.height + pad * 2) + 'px';
      var bw = this.box.offsetWidth || 308, bh = this.box.offsetHeight || 150, gap = 16, vw = innerWidth, vh = innerHeight;
      var place = step.placement || 'auto';
      if (place === 'auto') {
        if (r.top > bh + gap + 10) place = 'top';
        else if (vh - r.bottom > bh + gap + 10) place = 'bottom';
        else if (r.left > bw + gap + 10) place = 'left';
        else place = 'right';
      }
      var bx, by, ax, ay;
      if (place === 'top') { bx = r.left + r.width / 2 - bw / 2; by = r.top - bh - gap; ax = r.left + r.width / 2 - 7; ay = r.top - gap - 1; }
      else if (place === 'bottom') { bx = r.left + r.width / 2 - bw / 2; by = r.bottom + gap; ax = r.left + r.width / 2 - 7; ay = r.bottom + gap - 6; }
      else if (place === 'left') { bx = r.left - bw - gap; by = r.top + r.height / 2 - bh / 2; ax = r.left - gap - 6; ay = r.top + r.height / 2 - 7; }
      else { bx = r.right + gap; by = r.top + r.height / 2 - bh / 2; ax = r.right + gap - 6; ay = r.top + r.height / 2 - 7; }
      bx = Math.max(8, Math.min(bx, vw - bw - 8)); by = Math.max(8, Math.min(by, vh - bh - 8));
      this.box.style.left = bx + 'px'; this.box.style.top = by + 'px';
      this.arrow.style.left = Math.max(8, Math.min(ax, vw - 22)) + 'px'; this.arrow.style.top = Math.max(8, Math.min(ay, vh - 22)) + 'px';
    }
  };

  global.DemoTour = {
    steps: STEPS,
    // Solo en modo demo (/api/config -> mode === 'demo'): en el runtime real
    // no se monta nada (ni launcher ni auto-arranque).
    run: function (opts) {
      opts = opts || {};
      fetch('/api/config').then(function (r) { return r.json(); }).then(function (cfg) {
        if (!cfg || cfg.mode !== 'demo') return;
        injectCSS();
        Tour.launcher();
        if (isDone()) return;               // ya lo cerró/terminó
        var i = getIdx();
        var here = norm();
        // Retomar solo si el paso actual pertenece a ESTA vista (llegamos por
        // navegación del tour) o si es el arranque en el chat.
        if (norm(STEPS[i] && STEPS[i].route) === here) {
          setTimeout(function () { Tour.go(i); }, opts.delay || 600);
        }
      }).catch(function () {});
    },
    restart: function () { setDone(false); setIdx(0); Tour.go(0); }
  };
})(window);
