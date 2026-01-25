// js/Common/ExportPane.js
//
// Export pane (scoped).
// - Downloads JSON from Panes scoped state (no window globals).
// - Notifies ticker via Panes scoped events.
// - Uses data-state-key (preferred) with backward-compat alias data-builder-global.
// -----------------------------------------------------------------------------

(function () {
  'use strict';

  var FLASH_DURATION_MS = 5000;

  function notifyTicker(tickerId, text, ms, color, api) {
    if (!tickerId || !text) return;
    if (!api || !api.events || !api.events.emit) return;

    api.events.emit('ticker:temporary', {
      tickerId: tickerId,
      text: text,
      ms: ms,
      color: color
    });
  }

  function flash(flashEl, msg) {
    flashEl.textContent = msg || '';
    flashEl.classList.add('show');
    setTimeout(function () {
      flashEl.classList.remove('show');
      flashEl.textContent = '';
    }, FLASH_DURATION_MS);
  }

  function init(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('ExportPane: missing Panes api');
    }
    var ds = container.dataset || {};

    // Preferred: data-state-key.
    var stateKey     = ds.stateKey || 'TEXT_PROFILE';

    var title        = ds.title       || 'Export';
    var filename     = ds.filename    || 'profile.json';
    var buttonLabel  = ds.buttonLabel || 'Download JSON';

    var tickerId = ds.tickerId || null;

    var msgExportEmpty = ds.msgExportEmpty || 'Nothing to export';
    var msgExportSaved = ds.msgExportSaved || 'Saved {filename}';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--builder-export';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = title;

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btn = document.createElement('button');
    btn.className = 'primary';
    btn.type = 'button';
    btn.textContent = buttonLabel;

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    actions.appendChild(btn);
    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    container.appendChild(section);

    function onClick() {
      var obj = api.state.get(stateKey);

      if (!obj) {
        flash(flashDiv, msgExportEmpty);
        notifyTicker(tickerId, msgExportEmpty, FLASH_DURATION_MS, '#f97316', api);
        return;
      }

      var blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });

      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = filename;

      document.body.appendChild(a);
      a.click();
      a.remove();

      URL.revokeObjectURL(url);

      var msg = String(msgExportSaved).replace('{filename}', filename);
      flash(flashDiv, msg);
      notifyTicker(tickerId, msg, FLASH_DURATION_MS, 'var(--accent)', api);
    }

    btn.addEventListener('click', onClick);

    return {
      destroy: function () {
        btn.removeEventListener('click', onClick);
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('ExportPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('builder-export', function (container, api) {
    container.classList.add('pane-builder-export');
    return init(container, api);
  });
})();