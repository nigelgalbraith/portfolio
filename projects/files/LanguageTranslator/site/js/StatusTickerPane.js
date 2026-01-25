// js/StatusTickerPane.js
// Pane: Animated typewriter status ticker (scoped).
// -----------------------------------------------------------------------------
// HOW TO USE:
//   <div
//     data-pane="status-ticker"
//     data-messages-url="data/messages.json"
//     data-ticker-id="profile-main"
//   ></div>
//
// Emits/Consumes (scoped via PanesCore api.events):
//   - 'ticker:temporary'   detail: { tickerId?, text, ms?, color? }
//   - 'ticker:setMessages' detail: { tickerId?, messages: [] }
// -----------------------------------------------------------------------------

(function () {
  'use strict';

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

  function initOne(container, api) {
    if (!api || !api.events || !api.state) {
      throw new Error('StatusTickerPane: missing Panes api');
    }

    var ds = container.dataset || {};
    var messagesUrl = ds.messagesUrl || null;
    var tickerId = ds.tickerId || 'default';

    var status = document.createElement('div');
    status.className = 'status-text';

    container.innerHTML = '';
    container.appendChild(status);

    var ticker = null;
    var offTemp = null;
    var offSet = null;

    function applyColor(color) {
      status.style.color = color ? String(color) : '';
    }

    function handleTemporary(ev) {
      var detail = (ev && ev.detail) ? ev.detail : {};
      if (detail.tickerId && detail.tickerId !== tickerId) return;

      var text = String(detail.text || '');
      if (!text) return;

      applyColor(detail.color);

      if (ticker) {
        ticker.showTemporary(text, detail.ms);
      } else {
        status.textContent = text;
      }

      // If the temp message ends and loop resumes, reset color back to default
      // (only if no newer temp message arrived)
      var seq = ticker ? ticker._tempSeq : 0;
      var ms = detail.ms || TEMP_MESSAGE_MS;

      setTimeout(function () {
        if (!ticker) return;
        if (ticker._tempSeq !== seq) return; // newer temp happened
        applyColor(''); // back to default
      }, ms + 50);
    }

    function handleSetMessages(ev) {
      var detail = (ev && ev.detail) ? ev.detail : {};
      if (detail.tickerId && detail.tickerId !== tickerId) return;

      var msgs = detail.messages;
      if (!Array.isArray(msgs)) return;

      if (ticker) ticker.setMessages(msgs);
    }

    // Subscribe immediately (even before messages load)
    offTemp = api.events.on('ticker:temporary', handleTemporary);
    offSet = api.events.on('ticker:setMessages', handleSetMessages);

    // Load messages and start
    loadTickerMessages(messagesUrl).then(function (msgs) {
      ticker = new StatusTicker(status, msgs, {});
      status.classList.add('show');
      applyColor(''); // ensure base loop starts "normal"
      ticker.start();
    });

    return {
      destroy: function () {
        try {
          if (ticker) ticker.stop();
        } catch (e) {}

        if (offTemp) offTemp();
        if (offSet) offSet();
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('StatusTickerPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('status-ticker', function (container, api) {
    container.classList.add('pane-status-ticker');
    return initOne(container, api);
  });
})();