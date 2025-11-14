// js/TranslatePreviewPane.js
//
// Pane: Translate text (default: English → Spanish) and show the result.
//
// HOW TO USE:
//
//   <div
//     data-pane="translator-preview"
//     data-translate-url="/translate"            // via nginx → LibreTranslate
//     data-source-selector="#english-text"
//     data-target-id="spanish-text"
//     data-source-lang="en"                      // optional, default 'en'
//     data-target-lang="es"                      // optional, default 'es'
//     data-title="Spanish Translation"
//     data-button-label="Translate"
//
//     data-ticker-id="profile-main"              // optional
//     data-ticker-generating="Translating…"
//     data-ticker-complete="Translation ready."
//     data-ticker-error="Translation failed."
//   ></div>

(function () {

  var FLASH_AUTOHIDE_MS = 2000;

  // Helper: ping the status ticker
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

  // Simple flash helper with auto-hide
  function makeFlash(flashDiv) {
    return function flash(msg) {
      flashDiv.textContent = msg || '';
      flashDiv.classList.add('show');
      setTimeout(function () {
        flashDiv.classList.remove('show');
      }, FLASH_AUTOHIDE_MS);
    };
  }

  // Call LibreTranslate-compatible API
  async function translateText(apiUrl, text, sourceLang, targetLang) {
    var body = {
      q: text,
      source: sourceLang || 'en',
      target: targetLang || 'es'
      // no "format" field to match the working curl
    };

    var resp = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (!resp.ok) {
      var errTxt = '';
      try { errTxt = await resp.text(); } catch (e) {}
      throw new Error('Translate HTTP ' + resp.status + ': ' + errTxt);
    }

    var data = await resp.json();

    if (Array.isArray(data) && data.length && data[0].translatedText) {
      return data[0].translatedText;
    }
    if (data && data.translatedText) {
      return data.translatedText;
    }

    return String(data || '');
  }

  function initOne(container) {
    var ds = container.dataset || {};

    var apiUrl         = ds.translateUrl || '/translate';
    var sourceSelector = ds.sourceSelector || '#english-text';
    var targetId       = ds.targetId || 'translated-text';

    var sourceLang     = ds.sourceLang || 'en';
    var targetLang     = ds.targetLang || 'es';

    var titleText      = ds.title || 'Translation';
    var buttonLabel    = ds.buttonLabel || 'Translate';

    var tickerId         = ds.tickerId || null;
    var tickerGenerating = ds.tickerGenerating || 'Translating…';
    var tickerComplete   = ds.tickerComplete   || 'Translation ready.';
    var tickerError      = ds.tickerError      || 'Translation failed.';

    // Reset container
    container.innerHTML = '';

    // Pane wrapper
    var section = document.createElement('section');
    section.className = 'pane';

    // Title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    // Button row
    var actions = document.createElement('div');
    actions.className = 'actions';

    var btn = document.createElement('button');
    btn.className = 'primary';
    btn.textContent = buttonLabel;

    actions.appendChild(btn);

    // Flash / status
    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    var flash = makeFlash(flashDiv);

    // Target text div for translated text (editable)
    var target = document.createElement('div');
    target.className = 'letter';
    target.id = targetId;
    target.contentEditable = 'true';

    var targetPlaceholder = ds.targetPlaceholder || 'Translated text will appear here…';
    target.setAttribute('data-placeholder', targetPlaceholder);

    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    section.appendChild(target);
    container.appendChild(section);

    var isBusy = false;

    btn.addEventListener('click', function () {
      if (isBusy) {
        flash('Already translating…');
        notifyTicker(tickerId, 'Already translating…', 1500, '#f97316');
        return;
      }

      var sourceEl = document.querySelector(sourceSelector);
      var text = '';

      if (sourceEl) {
        if ('value' in sourceEl) {
          text = sourceEl.value || '';
        } else {
          text = sourceEl.textContent || '';
        }
      }

      if (!text.trim()) {
        flash('Nothing to translate');
        notifyTicker(tickerId, 'Nothing to translate.', 2000, '#f97316');
        return;
      }

      isBusy = true;
      btn.disabled = true;

      notifyTicker(tickerId, tickerGenerating, 4000, 'var(--accent)');
      flash('Translating…');

      translateText(apiUrl, text, sourceLang, targetLang)
        .then(function (translated) {
          target.textContent = translated || '';
          flash('Translation complete');
          notifyTicker(tickerId, tickerComplete, 3000, 'var(--accent)');
        })
        .catch(function () {
          flash('Error during translation');
          notifyTicker(tickerId, tickerError, 3500, '#f87171');
        })
        .finally(function () {
          isBusy = false;
          btn.disabled = false;
        });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var panes = document.querySelectorAll('[data-pane="translator-preview"]');
    Array.prototype.forEach.call(panes, initOne);
  });

})();
