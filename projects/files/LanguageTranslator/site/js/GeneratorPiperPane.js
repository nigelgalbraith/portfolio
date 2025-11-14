// js/GeneratorPiperPane.js
//
// ===============================================
//  GENERATOR PIPER TTS PANE — HOW TO USE
// ===============================================
//
// This pane provides Text-To-Speech (TTS) playback for the
// generated preview text using a local **Piper TTS server**.
//
// It creates:
//
//   - A title: "Voice (Piper)"
//   - A label showing the selected voice ID
//   - A “Speak Preview” button
//   - A “Stop” button
//   - A status/flash indicator (animated dots while speaking)
//
// It sends the preview text to Piper’s HTTP API:
//
//   POST {base}/  (default: /piper/)
//   body: plain text
//   returns: WAV audio
//
//
// -----------------------------------------------
// 1) Add to HTML:
//
//   <div
//     data-pane="generator-piper"
//     data-piper-base="/piper"            // optional
//     data-voice-id="en_US-amy-low"       // optional
//     data-target-selector="#generator-letter"
//
//     data-ticker-id="profile-main"       // optional
//     data-ticker-speaking="Reading preview aloud."
//     data-ticker-stopped="Stopped voice playback."
//     data-ticker-error="Piper TTS error."
//     data-ticker-busy="Already speaking…"
//     data-ticker-empty="Nothing to speak."
//   ></div>
//
// The output text (the preview letter) must be found at
// the CSS selector given in data-target-selector.
//
// The default target is: #generator-letter
//
//
// -----------------------------------------------
// 2) data-* Attributes:
//
//   data-piper-base
//       Base URL for Piper TTS endpoint.
//       Default: "/piper"
//
//   data-voice-id  /  data-voice
//       Voice identifier for Piper.
//       Default: "en_US-amy-low"
//
//   data-target-selector
//       CSS selector that points to the preview text.
//       The pane reads textContent from this node.
//       Default: "#generator-letter"
//
//   data-ticker-id              (optional)
//       ID of the StatusTickerPane to send temporary messages to.
//
//   data-ticker-speaking        (optional)
//       Message sent to ticker when playback starts.
//       Default: 'Reading preview aloud.'
//
//   data-ticker-stopped         (optional)
//       Message sent to ticker when playback is stopped or finishes.
//       Default: 'Stopped voice playback.'
//
//   data-ticker-error           (optional)
//       Message sent to ticker when Piper errors.
//       Default: 'Piper TTS error.'
//
//   data-ticker-busy            (optional)
//       Message sent to ticker when user clicks Speak while already speaking.
//       Default: 'Already speaking…'
//
//   data-ticker-empty           (optional)
//       Message sent to ticker when there is no text to speak.
//       Default: 'Nothing to speak.'
//
//
// -----------------------------------------------
// 3) Requirements:
//
//   - A Piper server MUST be running and accessible.
//   - POST /piper/ must respond with WAV audio.
//   - The preview pane must contain readable text.
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {
  var DEFAULT_PIPER_BASE = '/piper';
  var DEFAULT_VOICE_ID = 'en_US-amy-low';

  var currentAudio = null;

  // -------------------------------------------------------------------
  // Helper: ping the status ticker (StatusTickerPane.js)
  // -------------------------------------------------------------------
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

  // -------------------------------------------------------------------
  // Send text to Piper TTS server, return playing Audio() instance
  // -------------------------------------------------------------------
  function speak(text, base, voiceId) {
    if (!text || !text.trim()) return Promise.resolve();

    base = base || DEFAULT_PIPER_BASE;
    voiceId = voiceId || DEFAULT_VOICE_ID;

    // Clean multi-line formatting, remove leading "text:"
    var clean = String(text)
      .replace(/\r\n/g, '\n')
      .replace(/  +\n/g, '\n')
      .replace(/^\s*text:\s*/i, '');

    // POST → /piper/
    return fetch(base + '/', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: clean
    })
      .then(function (res) {
        if (!res.ok) {
          throw new Error('Piper TTS failed (HTTP ' + res.status + ')');
        }
        return res.arrayBuffer();
      })
      .then(function (buf) {
        // Convert to WAV → play via <audio>
        var blob = new Blob([buf], { type: 'audio/wav' });

        if (currentAudio) currentAudio.pause();

        currentAudio = new Audio(URL.createObjectURL(blob));
        currentAudio.play();

        return currentAudio;
      });
  }

  // -------------------------------------------------------------------
  // Stop any currently playing audio
  // -------------------------------------------------------------------
  function stop() {
    if (currentAudio) currentAudio.pause();
    currentAudio = null;
  }

  // -------------------------------------------------------------------
  // Initialize a single Piper pane instance
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    var base = ds.piperBase || DEFAULT_PIPER_BASE;
    var voiceId = ds.voiceId || ds.voice || DEFAULT_VOICE_ID;

    // CSS selector for preview text (generator output)
    var targetSelector = ds.targetSelector || '#generator-letter';

    // Optional: link to a status ticker pane
    var tickerId = ds.tickerId || null;

    // Ticker messages (configurable via HTML)
    var tickerMsgSpeaking = ds.tickerSpeaking || 'Reading preview aloud.';
    var tickerMsgStopped  = ds.tickerStopped  || 'Stopped voice playback.';
    var tickerMsgError    = ds.tickerError    || 'Piper TTS error.';
    var tickerMsgBusy     = ds.tickerBusy     || 'Already speaking…';
    var tickerMsgEmpty    = ds.tickerEmpty    || 'Nothing to speak.';

    // Clear container for rendering
    container.innerHTML = '';

    // Pane
    var section = document.createElement('section');
    section.className = 'pane';

    // Title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = 'Voice (Piper)';

    // Voice display area
    var details = document.createElement('div');
    details.className = 'voice-details';

    var lab = document.createElement('label');
    lab.textContent = 'Voice in use';

    var voiceDiv = document.createElement('div');
    voiceDiv.id = 'voice-label';
    voiceDiv.textContent = voiceId;

    details.appendChild(lab);
    details.appendChild(voiceDiv);

    // Action buttons
    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnSay = document.createElement('button');
    btnSay.className = 'primary';
    btnSay.textContent = 'Speak Preview';

    var btnStop = document.createElement('button');
    btnStop.textContent = 'Stop';

    actions.appendChild(btnSay);
    actions.appendChild(btnStop);

    // Flash/status area
    var flashDiv = document.createElement('div');
    flashDiv.className = 'flash';
    flashDiv.id = 'tts-flash';

    // Assemble pane
    section.appendChild(h2);
    section.appendChild(details);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    container.appendChild(section);

    // -------------------------------------------------------------------
    // TTS interaction state
    // -------------------------------------------------------------------
    var isSpeaking = false;
    var dotTimer = null;

    function setFlash(msg) {
      flashDiv.textContent = msg || '';
    }

    // Show animated dots while speaking
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

    // -------------------------------------------------------------------
    // "Speak Preview" button handler
    // -------------------------------------------------------------------
    btnSay.addEventListener('click', function () {
      if (isSpeaking) {
        setFlash('Already speaking…');
        notifyTicker(tickerId, tickerMsgBusy, 2000, '#f97316'); // orange-ish
        return;
      }

      // Find the text to speak
      var target = document.querySelector(targetSelector);
      var text = target ? (target.textContent || '') : '';

      if (!text.trim()) {
        var msgEmpty = tickerMsgEmpty;
        setFlash(msgEmpty);
        notifyTicker(tickerId, msgEmpty, 2500, '#f97316');
        return;
      }

      isSpeaking = true;
      btnSay.disabled = true;
      btnStop.disabled = false;

      // Notify ticker that we started speaking
      var speakMsg = tickerMsgSpeaking.replace('{voice}', voiceId);
      notifyTicker(tickerId, speakMsg, 4000, 'var(--accent)');

      startDots('Speaking with ' + voiceId);

      speak(text, base, voiceId)
        .then(function (audio) {
          // When audio finishes, restore state
          if (audio && typeof audio.addEventListener === 'function') {
            var onDone = function () {
              audio.removeEventListener('ended', onDone);
              audio.removeEventListener('error', onDone);

              isSpeaking = false;
              btnSay.disabled = false;
              stopDots('Done.');
              notifyTicker(tickerId, tickerMsgStopped, 2500, 'var(--accent)');
            };
            audio.addEventListener('ended', onDone);
            audio.addEventListener('error', onDone);
          } else {
            // No audio object, just reset state
            isSpeaking = false;
            btnSay.disabled = false;
            stopDots('Done.');
            notifyTicker(tickerId, tickerMsgStopped, 2500, 'var(--accent)');
          }
        })
        .catch(function () {
          isSpeaking = false;
          btnSay.disabled = false;
          stopDots('Piper error — cannot speak.');
          notifyTicker(tickerId, tickerMsgError, 3500, '#f87171');
        });
    });

    // -------------------------------------------------------------------
    // "Stop" button handler
    // -------------------------------------------------------------------
    btnStop.addEventListener('click', function () {
      stop();
      isSpeaking = false;
      btnSay.disabled = false;
      stopDots('Stopped.');
      notifyTicker(tickerId, tickerMsgStopped, 2500, 'var(--accent)');
    });
  }

  // -------------------------------------------------------------------
  // Auto-init all <div data-pane="generator-piper">
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="generator-piper"]');
    Array.prototype.forEach.call(containers, initOne);
  });

})();
