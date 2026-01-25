// js/GeneratorPiperPane.js
//
// Generator Piper TTS pane (scoped).
// - Uses PanesCore events for ticker (no window events)
// - No DOMContentLoaded fallback (requires PanesCore)
// - Audio state is per-pane instance (no shared module global)

(function () {
  'use strict';

  var DEFAULT_PIPER_BASE = '/piper';
  var DEFAULT_VOICE_ID = 'en_US-amy-low';

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
      .replace(/^\s*text:\s*/i, '');
  }

  // Create a speak function that closes over a per-pane audio reference
  function makeSpeaker() {
    var currentAudio = null;

    function stop() {
      if (currentAudio) {
        try { currentAudio.pause(); } catch (e) {}
      }
      currentAudio = null;
    }

    function speak(text, base, voiceId) {
      if (!text || !text.trim()) return Promise.resolve(null);

      base = base || DEFAULT_PIPER_BASE;
      voiceId = voiceId || DEFAULT_VOICE_ID;

      var clean = cleanText(text);

      return fetch(base + '/', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: clean
      })
        .then(function (res) {
          if (!res.ok) throw new Error('Piper TTS failed (HTTP ' + res.status + ')');
          return res.arrayBuffer();
        })
        .then(function (buf) {
          var blob = new Blob([buf], { type: 'audio/wav' });

          // Stop previous audio in THIS pane instance
          stop();

          currentAudio = new Audio(URL.createObjectURL(blob));
          currentAudio.play();
          return currentAudio;
        });
    }

    return { speak: speak, stop: stop };
  }

  function initOne(container, api) {
    var ds = container.dataset || {};

    var base = ds.piperBase || DEFAULT_PIPER_BASE;
    var voiceId = ds.voiceId || ds.voice || DEFAULT_VOICE_ID;

    var targetSelector = ds.targetSelector || '#generator-text';

    var tickerId = ds.tickerId || null;

    var tickerMsgSpeaking = ds.tickerSpeaking || 'Reading preview aloud.';
    var tickerMsgStopped  = ds.tickerStopped  || 'Stopped voice playback.';
    var tickerMsgError    = ds.tickerError    || 'Piper TTS error.';
    var tickerMsgBusy     = ds.tickerBusy     || 'Already speaking…';
    var tickerMsgEmpty    = ds.tickerEmpty    || 'Nothing to speak.';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--generator-piper';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = 'Voice (Piper)';

    var details = document.createElement('div');
    details.className = 'voice-details';

    var lab = document.createElement('label');
    lab.textContent = 'Voice in use';

    var voiceDiv = document.createElement('div');
    voiceDiv.className = 'voice-label';
    voiceDiv.textContent = voiceId;

    details.appendChild(lab);
    details.appendChild(voiceDiv);

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnSay = document.createElement('button');
    btnSay.className = 'primary';
    btnSay.type = 'button';
    btnSay.textContent = 'Speak Preview';

    var btnStop = document.createElement('button');
    btnStop.type = 'button';
    btnStop.textContent = 'Stop';
    btnStop.disabled = true;

    actions.appendChild(btnSay);
    actions.appendChild(btnStop);

    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';

    section.appendChild(h2);
    section.appendChild(details);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    container.appendChild(section);

    var speaker = makeSpeaker();

    var isSpeaking = false;
    var dotTimer = null;
    var currentAudio = null;

    function setFlash(msg) {
      flashDiv.textContent = msg || '';
    }

    function startDots(baseMsg) {
      if (dotTimer) clearInterval(dotTimer);

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
      if (msg) setFlash(msg);
    }

    function resetUI(doneMsg, tickerMsg) {
      isSpeaking = false;
      btnSay.disabled = false;
      btnStop.disabled = true;
      currentAudio = null;
      stopDots(doneMsg);
      if (tickerMsg) notifyTicker(tickerId, tickerMsg, 2500, 'var(--accent)', api);
    }

    function onAudioDone() {
      if (currentAudio) {
        try {
          currentAudio.removeEventListener('ended', onAudioDone);
          currentAudio.removeEventListener('error', onAudioDone);
        } catch (e) {}
      }
      resetUI('Done.', tickerMsgStopped);
    }

    function onSpeakClick() {
      if (isSpeaking) {
        setFlash('Already speaking…');
        notifyTicker(tickerId, tickerMsgBusy, 2000, '#f97316', api);
        return;
      }

      var target = document.querySelector(targetSelector);
      var text = target ? (target.textContent || '') : '';

      if (!text.trim()) {
        setFlash(tickerMsgEmpty);
        notifyTicker(tickerId, tickerMsgEmpty, 2500, '#f97316', api);
        return;
      }

      isSpeaking = true;
      btnSay.disabled = true;
      btnStop.disabled = false;

      var speakMsg = String(tickerMsgSpeaking).replace('{voice}', voiceId);
      notifyTicker(tickerId, speakMsg, 4000, 'var(--accent)', api);

      startDots('Speaking with ' + voiceId);

      speaker.speak(text, base, voiceId)
        .then(function (audio) {
          currentAudio = audio;

          if (audio && typeof audio.addEventListener === 'function') {
            audio.addEventListener('ended', onAudioDone);
            audio.addEventListener('error', onAudioDone);
          } else {
            resetUI('Done.', tickerMsgStopped);
          }
        })
        .catch(function () {
          resetUI('Piper error — cannot speak.', null);
          notifyTicker(tickerId, tickerMsgError, 3500, '#f87171', api);
        });
    }

    function onStopClick() {
      speaker.stop();
      if (currentAudio) {
        try {
          currentAudio.removeEventListener('ended', onAudioDone);
          currentAudio.removeEventListener('error', onAudioDone);
        } catch (e) {}
      }
      resetUI('Stopped.', tickerMsgStopped);
    }

    btnSay.addEventListener('click', onSpeakClick);
    btnStop.addEventListener('click', onStopClick);

    return {
      destroy: function () {
        try { speaker.stop(); } catch (e) {}
        if (dotTimer) clearInterval(dotTimer);
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