(function (globalScope) {
  'use strict';

  var HOTKEY_ROWS = [
    ['Buscar nodo', 'Ctrl+F · /'],
    ['Borrar selección', 'Delete · Backspace'],
    ['Agregar hijo', 'Tab'],
    ['Agregar hermano', 'Enter'],
    ['Link horizontal', 'L'],
    ['Collapse/expand', 'Space'],
    ['Layouts', '1 · 2 · 3'],
    ['Centrar en nodo', 'F'],
    ['Cancelar modo', 'Esc'],
    ['Ayuda', '?']
  ];

  function isEditableTarget(target) {
    if (!target) return false;
    var tagName = target.tagName ? target.tagName.toLowerCase() : '';
    if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
      return true;
    }
    return !!target.isContentEditable;
  }

  function isWithinScope(scopeElement, target) {
    if (!scopeElement || !target || typeof scopeElement.contains !== 'function') {
      return true;
    }
    if (target === document.body || target === document.documentElement) {
      return true;
    }
    return scopeElement.contains(target);
  }

  function ensureOverlay(documentRef) {
    var overlay = documentRef.querySelector('[data-testid="hotkey-overlay"]');
    if (overlay) return overlay;

    overlay = documentRef.createElement('div');
    overlay.setAttribute('data-testid', 'hotkey-overlay');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.cssText = [
      'position:fixed',
      'inset:0',
      'display:none',
      'align-items:center',
      'justify-content:center',
      'padding:24px',
      'background:rgba(10,10,15,.72)',
      'z-index:9999'
    ].join(';');

    var panel = documentRef.createElement('div');
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'false');
    panel.setAttribute('aria-label', 'Atajos de teclado');
    panel.style.cssText = [
      'width:min(520px, 100%)',
      'max-height:min(80vh, 640px)',
      'overflow:auto',
      'background:linear-gradient(180deg, rgba(18,18,26,.98), rgba(10,10,15,.98))',
      'border:1px solid rgba(212,165,116,.18)',
      'border-radius:14px',
      'box-shadow:0 18px 48px rgba(0,0,0,.45)',
      'padding:18px',
      'color:#f5f0e8',
      'font-family:Inter, sans-serif'
    ].join(';');

    var title = documentRef.createElement('div');
    title.textContent = 'Atajos globales';
    title.style.cssText = 'font-size:16px;font-weight:600;margin-bottom:12px;color:#f5f0e8;';
    panel.appendChild(title);

    var list = documentRef.createElement('div');
    list.style.cssText = 'display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 14px;';

    HOTKEY_ROWS.forEach(function (row) {
      var label = documentRef.createElement('div');
      label.textContent = row[0];
      label.style.cssText = 'color:rgba(245,240,232,.82);font-size:14px;';
      list.appendChild(label);

      var key = documentRef.createElement('div');
      key.textContent = row[1];
      key.style.cssText = 'font-family:"JetBrains Mono", monospace;font-size:12px;color:#d4a574;white-space:nowrap;';
      list.appendChild(key);
    });

    panel.appendChild(list);
    overlay.appendChild(panel);

    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) {
        hideOverlay(overlay);
      }
    });

    documentRef.body.appendChild(overlay);
    return overlay;
  }

  function showOverlay(overlay) {
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');
  }

  function hideOverlay(overlay) {
    overlay.style.display = 'none';
    overlay.setAttribute('aria-hidden', 'true');
  }

  function callHandler(handler) {
    if (typeof handler === 'function') {
      handler();
    }
  }

  function initHotkeys(options) {
    options = options || {};

    if (typeof document === 'undefined') {
      return function noopCleanup() {};
    }

    var scopeElement = options.element || document.body;
    var overlay = ensureOverlay(document);

    function toggleHelp() {
      var isVisible = overlay.style.display !== 'none';
      if (isVisible) {
        hideOverlay(overlay);
      } else {
        showOverlay(overlay);
      }
      callHandler(options.onHelp);
    }

    function onKeyDown(event) {
      var target = event.target || document.activeElement;
      if (!isWithinScope(scopeElement, target)) {
        return;
      }

      if (isEditableTarget(target)) {
        return;
      }

      if (event.repeat && (event.key === ' ' || event.key === 'Spacebar')) {
        return;
      }

      var handled = true;
      var key = event.key;
      var lowerKey = typeof key === 'string' ? key.toLowerCase() : '';

      if ((event.ctrlKey || event.metaKey) && lowerKey === 'f') {
        callHandler(options.onSearch);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && key === '/') {
        callHandler(options.onSearch);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && (key === 'Delete' || key === 'Backspace')) {
        callHandler(options.onDelete);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && key === 'Tab') {
        callHandler(options.onAddChild);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && key === 'Enter') {
        callHandler(options.onAddSibling);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && lowerKey === 'l') {
        callHandler(options.onLinkHorizontal);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && (key === ' ' || key === 'Spacebar')) {
        callHandler(options.onCollapse);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && (key === '1' || key === '2' || key === '3')) {
        if (typeof options.onLayout === 'function') {
          options.onLayout(Number(key));
        }
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && lowerKey === 'f') {
        callHandler(options.onFocus);
      } else if (key === 'Escape') {
        hideOverlay(overlay);
        callHandler(options.onCancel);
      } else if (!event.ctrlKey && !event.metaKey && !event.altKey && (key === '?' || (event.shiftKey && key === '/'))) {
        toggleHelp();
      } else {
        handled = false;
      }

      if (handled) {
        event.preventDefault();
      }
    }

    document.addEventListener('keydown', onKeyDown);

    return function cleanupHotkeys() {
      document.removeEventListener('keydown', onKeyDown);
    };
  }

  globalScope.initHotkeys = initHotkeys;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = initHotkeys;
    module.exports.initHotkeys = initHotkeys;
  }
})(typeof window !== 'undefined' ? window : globalThis);
