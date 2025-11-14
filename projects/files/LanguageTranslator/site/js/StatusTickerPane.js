// js/StatusTickerPane.js
// Pane: Animated typewriter status ticker (standalone).
// -----------------------------------------------------------------------------
// HOW TO USE:
//   <div
//     data-pane="status-ticker"
//     data-messages-url="data/messages.json"
//     data-ticker-id="profile-main"
//   ></div>
//
// NOTES:
//   • It loads ticker messages from data-messages-url (or defaults).
//   • It listens for CustomEvents on window:
//       - 'ticker:temporary'  → show a temporary message, then resume loop
//       - 'ticker:setMessages' → replace base message list
//   • Both events accept an optional `tickerId` in detail to target a specific
//     ticker when you have more than one.
// -----------------------------------------------------------------------------

(function () {

  // ---------------------------------------------------------------------------
  // DEFAULT MESSAGES + TIMING CONSTANTS
  // ---------------------------------------------------------------------------

  var DEFAULT_TICKER_MESSAGES = [
    'Tip: Load a profile JSON to get started.',
    'You can always export your current setup.'
  ];

  var TYPING_DELAY  = 70;
  var HOLD_DELAY    = 4000;
  var BETWEEN_DELAY = 800;
  var INITIAL_DELAY = 600;
  var TEMP_MESSAGE_MS = 5000;

  function loadTickerMessages(url) {
    if (!url) return Promise.resolve(DEFAULT_TICKER_MESSAGES.slice());
    return fetch(url)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (Array.isArray(data)) return data;
        if (data && Array.isArray(data.messages)) return data.messages;
        return DEFAULT_TICKER_MESSAGES.slice();
      })
      .catch(function () {
        return DEFAULT_TICKER_MESSAGES.slice();
      });
  }

  // ---------------------------------------------------------------------------
  // TYPEWRITER TICKER CLASS
  // ---------------------------------------------------------------------------

  function StatusTicker(el, messages, opts) {
    this.el = el;
    this.messages = messages || [];
    this.opts = opts || {};

    this.opts.typingDelay  = this.opts.typingDelay  || TYPING_DELAY;
    this.opts.holdDelay    = this.opts.holdDelay    || HOLD_DELAY;
    this.opts.betweenDelay = this.opts.betweenDelay || BETWEEN_DELAY;
    this.opts.initialDelay = this.opts.initialDelay || INITIAL_DELAY;

    this._idx = 0;
    this._running = false;
    this._stop = false;
    this._interrupt = false;
    this._tempSeq = 0;
  }

  StatusTicker.prototype._sleep = function (ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  };

  StatusTicker.prototype._type = async function (text) {
    var el = this.el;
    el.textContent = '';
    for (var i = 0; i < text.length; i++) {
      if (this._interrupt || this._stop) return;
      el.textContent += text.charAt(i);
      await this._sleep(this.opts.typingDelay);
    }
  };

  StatusTicker.prototype._loop = async function () {
    this._running = true;
    await this._sleep(this.opts.initialDelay);

    while (!this._stop) {
      if (!this.messages.length) {
        await this._sleep(1000);
        continue;
      }

      var text = this.messages[this._idx % this.messages.length];
      this._idx++;

      this._interrupt = false;
      await this._type(text);
      if (this._interrupt || this._stop) break;

      await this._sleep(this.opts.holdDelay);
      if (this._interrupt || this._stop) break;

      await this._sleep(this.opts.betweenDelay);
    }

    this._running = false;
  };

  StatusTicker.prototype.start = function () {
    if (this._running) return;
    this._stop = false;
    this._interrupt = false;
    this._loop();
  };

  StatusTicker.prototype.stop = function () {
    this._stop = true;
    this._interrupt = true;
  };

  StatusTicker.prototype.setMessages = function (msgs) {
    this.messages = msgs || [];
    this._idx = 0;
  };

  StatusTicker.prototype.showTemporary = function (text, ms) {
    var token = ++this._tempSeq;
    var self = this;

    this.stop();
    this.el.textContent = text;

    this._sleep(ms || TEMP_MESSAGE_MS).then(function () {
      if (token !== self._tempSeq) return;
      if (self.messages && self.messages.length) {
        self._stop = false;
        self._interrupt = false;
        self.start();
      }
    });
  };

  // ---------------------------------------------------------------------------
  // INIT ONE TICKER PANE
  // ---------------------------------------------------------------------------

  function initTickerPane(container) {
    var ds = container.dataset || {};
    var messagesUrl = ds.messagesUrl || 'messages.json';
    var tickerId = ds.tickerId || 'default';

    var status = document.createElement('div');
    status.className = 'status-text';

    container.innerHTML = '';
    container.appendChild(status);

    var ticker = null;

    loadTickerMessages(messagesUrl).then(function (msgs) {
      ticker = new StatusTicker(status, msgs, {});
      status.classList.add('show');
      ticker.start();
    });

    // Temporary message: ticker:temporary
    window.addEventListener('ticker:temporary', function (ev) {
      var detail = ev.detail || {};
      if (detail.tickerId && detail.tickerId !== tickerId) return;

      var text = String(detail.text || '');
      var ms   = detail.ms;
      var color = detail.color;

      if (!text) return;

      if (color) {
        status.style.color = color;
      } else {
        status.style.color = '';
      }

      if (ticker) {
        ticker.showTemporary(text, ms);
      } else {
        // If ticker not ready yet, just set text
        status.textContent = text;
      }
    });

    // Replace base messages: ticker:setMessages
    window.addEventListener('ticker:setMessages', function (ev) {
      var detail = ev.detail || {};
      if (detail.tickerId && detail.tickerId !== tickerId) return;

      var msgs = detail.messages;
      if (!Array.isArray(msgs)) return;

      if (ticker) {
        ticker.setMessages(msgs);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var panes = document.querySelectorAll('[data-pane="status-ticker"]');
    for (var i = 0; i < panes.length; i++) {
      initTickerPane(panes[i]);
    }
  });
})();
