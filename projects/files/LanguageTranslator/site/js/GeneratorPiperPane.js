// js/GeneratorPiperPane.js
//
// Generator Piper TTS pane (scoped).
// - PanesCore-scoped (register + bootstrap)
// - No window events
// - Sends ticker messages via api.events.emit('ticker:temporary', ...)
// - Per-pane audio instance (no shared globals)
// - Auto-disable Speak button when target text is empty (no polling)
// - More robust target watching (contentEditable uses input + MutationObserver)
// - Handles target not existing yet at init (small retry loop)

(function () {
  'use strict';

  var DEFAULT_PIPER_BASE = '/piper';
  var DEFAULT_VOICE_ID = 'en_US-amy-low';

  var RETRY_FIND_TARGET_MS = 50;
  var RETRY_FIND_TARGET_TRIES = 40; // ~2s total worst-case

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

  function cleanText(text) {
    return String(text || '')
      .replace(/\r\n/g, '\n')
      .replace(/  +\n/g, '\n')
      .replace(/^\s*text:\s*/i, '')
      .trim();
  }

  function getTargetEl(selector) {
    if (!selector) return null;
    return document.querySelector(selector);
  }

  function readTargetTextFromEl(el) {
    if (!el) return '';
    if ('value' in el) return String(el.value || '');
    return String(el.textContent || '');
  }

  function speakViaPiper(text, base, voiceId) {
    if (!text || !text.trim()) return Promise.resolve(null);

    base = base || DEFAULT_PIPER_BASE;
    voiceId = voiceId || DEFAULT_VOICE_ID;

    // NOTE: voiceId is not used in the request body in your current setup.
    // If your server supports voice selection, adjust here.

    return fetch(base + '/', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: cleanText(text)
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Piper TTS failed (HTTP ' + res.status + ')');
        return res.arrayBuffer();
      })
      .then(function (buf) {
        var blob = new Blob([buf], { type: 'audio/wav' });
        var url = URL.createObjectURL(blob);

        var audio = new Audio(url);
        audio._blobUrl = url;

        var p = audio.play();
        if (p && typeof p.catch === 'function') p.catch(function () {});

        return audio;
      });
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('GeneratorPiperPane: missing Panes api');
    }

    var ds = container.dataset || {};

    var base = ds.piperBase || DEFAULT_PIPER_BASE;
    var voiceId = ds.voiceId || ds.voice || DEFAULT_VOICE_ID;
    var targetSelector = ds.targetSelector || '#generator-letter';

    var tickerId = ds.tickerId || null;

    var tickerMsgSpeaking = ds.tickerSpeaking || 'Reading aloud.';
    var tickerMsgStopped  = ds.tickerStopped  || 'Stopped voice playback.';
    var tickerMsgError    = ds.tickerError    || 'Piper TTS error.';
    var tickerMsgBusy     = ds.tickerBusy     || 'Already speaking…';
    var tickerMsgEmpty    = ds.tickerEmpty    || 'Nothing to speak.';

    var autoDisable = String(ds.autoDisable || 'true').toLowerCase() !== 'false';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--generator-piper';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = ds.title || 'Voice (Piper)';

    var details = document.createElement('div');
    details.className = 'voice-details';

    var lab = document.createElement('label');
    lab.textContent = ds.voiceLabel || 'Voice in use';

    var voiceDiv = document.createElement('div');
    voiceDiv.className = 'voice-id';
    voiceDiv.textContent = voiceId;

    details.appendChild(lab);
    details.appendChild(voiceDiv);

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnSay = document.createElement('button');
    btnSay.className = 'primary';
    btnSay.type = 'button';
    btnSay.textContent = ds.speakLabel || 'Speak';

    var btnStop = document.createElement('button');
    btnStop.type = 'button';
    btnStop.textContent = ds.stopLabel || 'Stop';

    actions.appendChild(btnSay);
    actions.appendChild(btnStop);

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    section.appendChild(h2);
    section.appendChild(details);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    container.appendChild(section);

    // per-pane playback state
    var currentAudio = null;
    var isSpeaking = false;
    var dotTimer = null;

    // target watching state
    var targetEl = null;
    var mo = null;
    var retryTimer = null;
    var retriesLeft = RETRY_FIND_TARGET_TRIES;

    function setFlash(msg) {
      flashDiv.textContent = msg || '';
      flashDiv.classList.toggle('show', !!msg);
    }

    function startDots(baseMsg) {
      stopDots();
      var dots = 0;
      dotTimer = setInterval(function () {
        dots = (dots + 1) % 4;
        setFlash(baseMsg + '.'.repeat(dots));
      }, 350);
    }

    function stopDots(msg) {
      if (dotTimer) {
        clearInterval(dotTimer);
        dotTimer = null;
      }
      if (msg != null) setFlash(msg);
    }

    function cleanupAudio(audio) {
      try { if (audio) audio.pause(); } catch (e) {}
      try { if (audio && audio._blobUrl) URL.revokeObjectURL(audio._blobUrl); } catch (e) {}
    }

    function updateSpeakEnabled() {
      if (!autoDisable) return;
      if (isSpeaking) return;
      btnSay.disabled = !cleanText(readTargetTextFromEl(targetEl));
    }

    function stopPlayback(opts) {
      opts = opts || {};
      var hadAudio = !!currentAudio;
      var wasSpeaking = isSpeaking;

      if (currentAudio) cleanupAudio(currentAudio);
      currentAudio = null;
      isSpeaking = false;

      btnStop.disabled = true;
      updateSpeakEnabled();
      stopDots('Stopped.');

      // Only announce if we were actually doing something (polish)
      if (!opts.silent && (hadAudio || wasSpeaking)) {
        notifyTicker(tickerId, tickerMsgStopped, 2500, 'var(--accent)', api);
      }
    }

    // initial button state
    btnStop.disabled = true;
    btnSay.disabled = autoDisable ? true : false;

    function detachWatchers() {
      if (mo) {
        try { mo.disconnect(); } catch (e) {}
        mo = null;
      }

      if (targetEl) {
        // input/change works for both inputs and many contentEditable edits
        targetEl.removeEventListener('input', updateSpeakEnabled);
        targetEl.removeEventListener('change', updateSpeakEnabled);
      }
    }

    function attachWatchers(el) {
      if (!autoDisable || !el) return;

      // Always listen for input/change (works for inputs + contentEditable in practice)
      el.addEventListener('input', updateSpeakEnabled);
      el.addEventListener('change', updateSpeakEnabled);

      // If contentEditable, also use MutationObserver for extra reliability
      if (el.isContentEditable && typeof MutationObserver === 'function') {
        mo = new MutationObserver(function () { updateSpeakEnabled(); });
        mo.observe(el, { childList: true, characterData: true, subtree: true });
      }
    }

    function tryAttachTarget() {
      if (targetEl) return;

      var found = getTargetEl(targetSelector);
      if (found) {
        targetEl = found;
        attachWatchers(targetEl);
        updateSpeakEnabled();
        return;
      }

      retriesLeft--;
      if (retriesLeft <= 0) return;

      retryTimer = setTimeout(tryAttachTarget, RETRY_FIND_TARGET_MS);
    }

    // Start trying to find the target (no polling forever; short retry window)
    tryAttachTarget();

    function onSpeakClick() {
      if (isSpeaking) {
        setFlash(tickerMsgBusy);
        notifyTicker(tickerId, tickerMsgBusy, 2000, '#f97316', api);
        return;
      }

      var text = cleanText(readTargetTextFromEl(targetEl));
      if (!text) {
        setFlash(tickerMsgEmpty);
        notifyTicker(tickerId, tickerMsgEmpty, 2500, '#f97316', api);
        return;
      }

      isSpeaking = true;
      btnSay.disabled = true;
      btnStop.disabled = false;

      notifyTicker(
        tickerId,
        String(tickerMsgSpeaking).replace('{voice}', voiceId),
        4000,
        'var(--accent)',
        api
      );

      startDots('Speaking');

      speakViaPiper(text, base, voiceId)
        .then(function (audio) {
          currentAudio = audio;

          function done() {
            if (!audio) return;

            audio.removeEventListener('ended', done);
            audio.removeEventListener('error', done);

            cleanupAudio(audio);
            if (currentAudio === audio) currentAudio = null;

            isSpeaking = false;
            btnStop.disabled = true;
            updateSpeakEnabled();
            stopDots('Done.');
            notifyTicker(tickerId, tickerMsgStopped, 2500, 'var(--accent)', api);
          }

          if (!audio) {
            isSpeaking = false;
            btnStop.disabled = true;
            updateSpeakEnabled();
            stopDots('Done.');
            notifyTicker(tickerId, tickerMsgStopped, 2500, 'var(--accent)', api);
            return;
          }

          audio.addEventListener('ended', done);
          audio.addEventListener('error', done);
        })
        .catch(function () {
          if (currentAudio) cleanupAudio(currentAudio);
          currentAudio = null;

          isSpeaking = false;
          btnStop.disabled = true;
          updateSpeakEnabled();
          stopDots('Piper error — cannot speak.');
          notifyTicker(tickerId, tickerMsgError, 3500, '#f87171', api);
        });
    }

    function onStopClick() {
      stopPlayback({ silent: false });
    }

    btnSay.addEventListener('click', onSpeakClick);
    btnStop.addEventListener('click', onStopClick);

    return {
      destroy: function () {
        if (retryTimer) {
          try { clearTimeout(retryTimer); } catch (e) {}
          retryTimer = null;
        }

        detachWatchers();
        try { stopPlayback({ silent: true }); } catch (e) {}
        try { if (dotTimer) clearInterval(dotTimer); } catch (e) {}

        btnSay.removeEventListener('click', onSpeakClick);
        btnStop.removeEventListener('click', onStopClick);
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('GeneratorPiperPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('generator-piper', function (container, api) {
    container.classList.add('pane-generator-piper');
    return initOne(container, api);
  });
})();