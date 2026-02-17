// js/Common/ProfileLoaderPane.js
// Pane: Load Profile button (scoped).
// -----------------------------------------------------------------------------
// Stores profile in Panes scoped state (api.state.set).
// PanesCore emits state:changed + state:changed:<key> automatically.
// Notifies ticker via 'ticker:temporary'.
// Uses data-state-key only.
// -----------------------------------------------------------------------------

(function () {
  'use strict';

  function readFileAsText(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result || '')); };
      reader.onerror = function () { reject(new Error('File read error')); };
      reader.readAsText(file);
    });
  }

  function parseJSONSafe(text, fallbackMsg) {
    try {
      return { ok: true, value: JSON.parse(text) };
    } catch (e) {
      return { ok: false, error: fallbackMsg || 'Invalid JSON file' };
    }
  }

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

  function loadDefaultProfile(url, stateKey, statusEl, tickerId, messages, api) {
    return fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.text();
      })
      .then(function (txt) {
        var parsed = parseJSONSafe(txt, messages.invalidJson);
        if (!parsed.ok) {
          var msgErr = messages.invalidJson || parsed.error || 'Invalid JSON file';
          if (statusEl) {
            statusEl.textContent = msgErr;
            statusEl.style.color = '#f87171';
          }
          notifyTicker(tickerId, msgErr, 3000, '#f87171', api);
          return;
        }

        var profile = parsed.value;

        // This triggers PanesCore: state:changed + state:changed:<stateKey>
        api.state.set(stateKey, profile);

        var msg = messages.defaultLoaded || 'Default profile loaded';
        if (statusEl) {
          statusEl.textContent = msg;
          statusEl.style.color = 'var(--accent)';
        }
        notifyTicker(tickerId, msg, 2500, 'var(--accent)', api);
      })
      .catch(function () {
        var emsg = messages.defaultFailed || 'Failed to load default profile';
        if (statusEl) {
          statusEl.textContent = emsg;
          statusEl.style.color = '#f87171';
        }
        notifyTicker(tickerId, emsg, 3000, '#f87171', api);
      });
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('ProfileLoaderPane: missing Panes api');
    }

    var ds = container.dataset || {};

    var buttonLabel    = ds.buttonLabel    || 'Load Profile';
    var accept         = ds.accept         || 'application/json';
    var defaultProfile = ds.defaultProfile || null;

    // Only source of truth now
    var stateKey       = ds.stateKey || 'TEXT_PROFILE';

    var tickerId       = ds.tickerId || null;

    var messages = {
      defaultLoaded: ds.msgDefaultLoaded || 'Default profile loaded',
      defaultFailed: ds.msgDefaultFailed || 'Failed to load default profile',
      profileLoaded: ds.msgProfileLoaded || 'Profile loaded: {file}',
      invalidJson:   ds.msgInvalidJson   || 'Invalid JSON file',
      readFailed:    ds.msgReadFailed    || 'Failed to read file'
    };

    var actions = document.createElement('div');
    actions.className = 'actions actions-centered';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'primary';
    btn.textContent = buttonLabel;

    var input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.hidden = true;

    actions.appendChild(btn);
    actions.appendChild(input);

    container.innerHTML = '';
    container.appendChild(actions);

    var status = null;
    if (!tickerId) {
      status = document.createElement('div');
      status.className = 'status-text';
      container.appendChild(status);
    }

    function onBtnClick() { input.click(); }
    btn.addEventListener('click', onBtnClick);

    function onInputChange(ev) {
      var file = ev.target.files && ev.target.files[0];
      if (!file) return;

      readFileAsText(file)
        .then(function (txt) {
          var parsed = parseJSONSafe(txt, messages.invalidJson);
          if (!parsed.ok) {
            var msgErr = messages.invalidJson || parsed.error || 'Invalid JSON file';
            if (status) {
              status.textContent = msgErr;
              status.style.color = '#f87171';
            }
            notifyTicker(tickerId, msgErr, 3000, '#f87171', api);
            return;
          }

          var profile = parsed.value;

          // This triggers PanesCore: state:changed + state:changed:<stateKey>
          api.state.set(stateKey, profile);

          var fileName = file.name || 'profile.json';
          var msg = String(messages.profileLoaded || 'Profile loaded: {file}').replace('{file}', fileName);

          if (status) {
            status.textContent = msg;
            status.style.color = 'var(--accent)';
          }
          notifyTicker(tickerId, msg, 2500, 'var(--accent)', api);
        })
        .catch(function () {
          var emsg = messages.readFailed || 'Failed to read file';
          if (status) {
            status.textContent = emsg;
            status.style.color = '#f87171';
          }
          notifyTicker(tickerId, emsg, 3000, '#f87171', api);
        })
        .finally(function () {
          ev.target.value = '';
        });
    }

    input.addEventListener('change', onInputChange);

    if (defaultProfile) {
      loadDefaultProfile(defaultProfile, stateKey, status, tickerId, messages, api);
    }

    return {
      destroy: function () {
        btn.removeEventListener('click', onBtnClick);
        input.removeEventListener('change', onInputChange);
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('ProfileLoaderPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('profile-loader', function (container, api) {
    container.classList.add('pane-profile-loader');
    return initOne(container, api);
  });
})();