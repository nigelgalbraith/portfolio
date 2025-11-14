// js/ProfileLoaderPane.js
// Pane: Load Profile button.
// -----------------------------------------------------------------------------
// HOW TO USE:
//
//   <!-- Loader button -->
//   <div
//     data-pane="profile-loader"
//     data-profile-global="LETTER_PROFILE"
//     data-default-profile="data/default.json"
//     data-profile-event="profileLoaded"
//     data-button-label="Load Profile"
//     data-accept="application/json"
//     data-ticker-id="profile-main"
//
//     data-msg-default-loaded="Default profile loaded"
//     data-msg-default-failed="Failed to load default profile"
//     data-msg-profile-loaded="Profile loaded: {file}"
//     data-msg-invalid-json="Invalid JSON file"
//     data-msg-read-failed="Failed to read file"
//   ></div>
//
//   <!-- Ticker (separate pane) -->
//   <div
//     data-pane="status-ticker"
//     data-messages-url="data/messages.json"
//     data-ticker-id="profile-main"
//   ></div>
//
// WHAT IT DOES:
//   ✓ Lets user pick a JSON profile file
//   ✓ Optionally auto-loads a default profile URL
//   ✓ Writes profile into a global (LETTER_PROFILE by default)
//   ✓ Dispatches a CustomEvent (profileLoaded) to notify other panes
//   ✓ Optionally notifies a ticker by dispatching 'ticker:temporary'
//   ✓ Messages can be customised via data-msg-* attributes
// -----------------------------------------------------------------------------

(function () {

  // Reads a file (File object) and returns its text content as Promise<string>
  function readFileAsText(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result || '')); };
      reader.onerror = function () { reject(new Error('File read error')); };
      reader.readAsText(file);
    });
  }

  // Safe JSON.parse — returns {ok, value} or {ok:false, error}
  function parseJSONSafe(text) {
    try {
      return { ok: true, value: JSON.parse(text) };
    } catch (e) {
      return { ok: false, error: 'Invalid JSON file' };
    }
  }

  // Helper to ping ticker if configured
  function notifyTicker(tickerId, text, ms, color) {
    if (!tickerId || !text) return;
    var ev = new CustomEvent('ticker:temporary', {
      detail: {
        tickerId: tickerId,
        text: text,
        ms: ms,
        color: color
      }
    });
    window.dispatchEvent(ev);
  }

  // Load default profile from URL (optional)
  function loadDefaultProfile(url, profileGlobal, eventName, statusEl, tickerId, container, messages) {
    return fetch(url)
      .then(function (res) { return res.text(); })
      .then(function (txt) {
        var parsed = parseJSONSafe(txt);
        if (!parsed.ok) {
          var msgErr = messages.invalidJson || parsed.error || 'Invalid JSON file';
          if (statusEl) {
            statusEl.textContent = msgErr;
            statusEl.style.color = '#f87171';
          }
          notifyTicker(tickerId, msgErr, 3000, '#f87171');
          return;
        }

        var profile = parsed.value;
        window[profileGlobal] = profile;

        var evOut = new CustomEvent(eventName, {
          detail: {
            profile: profile,
            fileName: url,
            source: container
          }
        });
        window.dispatchEvent(evOut);

        var msg = messages.defaultLoaded || 'Default profile loaded';
        if (statusEl) {
          statusEl.textContent = msg;
          statusEl.style.color = 'var(--accent)';
        }
        notifyTicker(tickerId, msg, 2500, 'var(--accent)');
      })
      .catch(function () {
        var emsg = messages.defaultFailed || 'Failed to load default profile';
        if (statusEl) {
          statusEl.textContent = emsg;
          statusEl.style.color = '#f87171';
        }
        notifyTicker(tickerId, emsg, 3000, '#f87171');
      });
  }

  function initOne(container) {
    var ds = container.dataset || {};

    var eventName      = ds.profileEvent   || 'profileLoaded';
    var buttonLabel    = ds.buttonLabel    || 'Load Profile';
    var accept         = ds.accept         || 'application/json';
    var defaultProfile = ds.defaultProfile || null;
    var profileGlobal  = ds.profileGlobal  || 'LETTER_PROFILE';

    // Optional: which ticker to talk to
    var tickerId       = ds.tickerId || null;

    // Message config (pass-through from the div)
    var messages = {
      defaultLoaded: ds.msgDefaultLoaded || 'Default profile loaded',
      defaultFailed: ds.msgDefaultFailed || 'Failed to load default profile',
      profileLoaded: ds.msgProfileLoaded || 'Profile loaded: {file}',
      invalidJson:   ds.msgInvalidJson   || 'Invalid JSON file',
      readFailed:    ds.msgReadFailed    || 'Failed to read file'
    };

    // --- Create UI elements ---
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

    // Fallback status element (only if no ticker is used)
    var status = null;
    if (!tickerId) {
      status = document.createElement('div');
      status.className = 'status-text';
      container.appendChild(status);
    }

    // Auto-load default profile, if configured
    if (defaultProfile) {
      loadDefaultProfile(
        defaultProfile,
        profileGlobal,
        eventName,
        status,
        tickerId,
        container,
        messages
      );
    }

    // --- File picker logic ---
    btn.addEventListener('click', function () {
      input.click();
    });

    input.addEventListener('change', function (ev) {
      var file = ev.target.files && ev.target.files[0];
      if (!file) return;

      readFileAsText(file)
        .then(function (txt) {
          var parsed = parseJSONSafe(txt);
          if (!parsed.ok) {
            var msgErr = messages.invalidJson || parsed.error || 'Invalid JSON file';
            if (status) {
              status.textContent = msgErr;
              status.style.color = '#f87171';
            }
            notifyTicker(tickerId, msgErr, 3000, '#f87171');
            return;
          }

          var profile = parsed.value;
          window[profileGlobal] = profile;

          var evOut = new CustomEvent(eventName, {
            detail: {
              profile: profile,
              fileName: file.name || 'profile.json',
              source: container
            }
          });
          window.dispatchEvent(evOut);

          var fileName = file.name || 'profile.json';
          var msgTpl = messages.profileLoaded || 'Profile loaded: {file}';
          var msg = msgTpl.replace('{file}', fileName);

          if (status) {
            status.textContent = msg;
            status.style.color = 'var(--accent)';
          }
          notifyTicker(tickerId, msg, 2500, 'var(--accent)');
        })
        .catch(function () {
          var emsg = messages.readFailed || 'Failed to read file';
          if (status) {
            status.textContent = emsg;
            status.style.color = '#f87171';
          }
          notifyTicker(tickerId, emsg, 3000, '#f87171');
        })
        .finally(function () {
          ev.target.value = '';
        });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var panes = document.querySelectorAll('[data-pane="profile-loader"]');
    for (var i = 0; i < panes.length; i++) {
      initOne(panes[i]);
    }
  });
})();
