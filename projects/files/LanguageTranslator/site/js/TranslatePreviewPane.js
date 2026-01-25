// js/TranslatePreviewPane.js
//
// Pane: Translate text and show the result (scoped).
// -----------------------------------------------------------------------------
// HOW TO USE:
//
//   <div
//     data-pane="translator-preview"
//     data-translate-url="/translate"
//     data-source-selector="#english-text"
//     data-target-id="spanish-text"
//     data-source-lang="en"          // optional
//     data-target-lang="es"          // optional
//     data-title="Spanish Translation"
//     data-button-label="Translate"
//
//     data-ticker-id="profile-main"  // optional
//     data-ticker-generating="Translating…"
//     data-ticker-complete="Translation ready."
//     data-ticker-error="Translation failed."
//   ></div>
//
// Notes:
// - No window events.
// - Uses api.events.emit('ticker:temporary', ...) to talk to StatusTickerPane.
// -----------------------------------------------------------------------------

(function () {
  'use strict';

  var FLASH_AUTOHIDE_MS = 2000;

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

  function makeFlash(flashDiv) {
    return function flash(msg) {
      flashDiv.textContent = msg || '';
      flashDiv.classList.add('show');
      setTimeout(function () {
        flashDiv.classList.remove('show');
      }, FLASH_AUTOHIDE_MS);
    };
  }

  async function translateText(apiUrl, text, sourceLang, targetLang) {
    var body = {
      q: text,
      source: sourceLang || 'en',
      target: targetLang || 'es'
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

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('TranslatePreviewPane: missing Panes api');
    }

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
    var msgBusy          = ds.msgBusy          || 'Already translating…';
    var msgEmpty         = ds.msgEmpty         || 'Nothing to translate';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--translator-preview';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btn = document.createElement('button');
    btn.className = 'primary';
    btn.type = 'button';
    btn.textContent = buttonLabel;

    actions.appendChild(btn);

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    var flash = makeFlash(flashDiv);

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
    var reqSeq = 0;

    function readSourceText() {
      var sourceEl = document.querySelector(sourceSelector);
      if (!sourceEl) return '';

      if ('value' in sourceEl) return sourceEl.value || '';
      return sourceEl.textContent || '';
    }

    // Optional UX: disable translate button when source is empty
    function setEnabledFromSource() {
      var txt = readSourceText();
      btn.disabled = isBusy || !String(txt || '').trim();
    }

    function onClick() {
      if (isBusy) {
        flash(msgBusy);
        notifyTicker(tickerId, msgBusy, 1500, '#f97316', api);
        return;
      }

      var text = readSourceText();
      if (!String(text || '').trim()) {
        flash(msgEmpty);
        notifyTicker(tickerId, msgEmpty, 2000, '#f97316', api);
        setEnabledFromSource();
        return;
      }

      isBusy = true;
      setEnabledFromSource();

      var mySeq = ++reqSeq;

      notifyTicker(tickerId, tickerGenerating, 4000, 'var(--accent)', api);
      flash('Translating…');

      translateText(apiUrl, text, sourceLang, targetLang)
        .then(function (translated) {
          if (mySeq !== reqSeq) return; // ignore stale response
          target.textContent = translated || '';
          flash('Translation complete');
          notifyTicker(tickerId, tickerComplete, 3000, 'var(--accent)', api);
        })
        .catch(function () {
          if (mySeq !== reqSeq) return;
          flash('Error during translation');
          notifyTicker(tickerId, tickerError, 3500, '#f87171', api);
        })
        .finally(function () {
          if (mySeq !== reqSeq) return;
          isBusy = false;
          setEnabledFromSource();
        });
    }

    btn.addEventListener('click', onClick);

    // Track input changes in the source element so button enables/disables live
    var srcEl = document.querySelector(sourceSelector);
    var onSrcInput = function () { setEnabledFromSource(); };

    if (srcEl) {
      // contentEditable divs fire 'input' too
      srcEl.addEventListener('input', onSrcInput);
      srcEl.addEventListener('keyup', onSrcInput);
      srcEl.addEventListener('change', onSrcInput);
    }

    // Initial enable/disable
    setEnabledFromSource();

    return {
      destroy: function () {
        btn.removeEventListener('click', onClick);
        if (srcEl) {
          srcEl.removeEventListener('input', onSrcInput);
          srcEl.removeEventListener('keyup', onSrcInput);
          srcEl.removeEventListener('change', onSrcInput);
        }
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('TranslatePreviewPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('translator-preview', function (container, api) {
    container.classList.add('pane-translator-preview');
    return initOne(container, api);
  });
})();