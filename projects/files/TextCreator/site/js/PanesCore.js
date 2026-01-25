// js/PanesCore.js
// -----------------------------------------------------------------------------
// Pane runtime used by all pages.
//
// Provides:
//   - Registry: panes register themselves by name (data-pane value)
//   - Bootstrap: single call instantiates all panes found in the DOM
//   - Lifecycle: factories may return { destroy() } for cleanup
//   - Events: small scoped event bus
//   - State: scoped key/value store (+ emits state change events)
//   - CSS isolation: adds pane-host--<name> to hosts
// -----------------------------------------------------------------------------

(function (global) {
  'use strict';

  if (global.Panes) return;

  var registry = Object.create(null);
  var instances = [];

  // Scoped shared state
  var _state = Object.create(null);

  // Scoped event listeners
  var _listeners = Object.create(null);

  function asKebab(s) {
    return String(s || '').trim().toLowerCase();
  }

  function hostClass(name) {
    return 'pane-host--' + asKebab(name);
  }

  var Events = {
    on: function (eventName, handler) {
      if (!eventName) throw new Error('Panes.events.on: missing eventName');
      if (typeof handler !== 'function') throw new Error('Panes.events.on: handler must be a function');

      var name = String(eventName);
      (_listeners[name] || (_listeners[name] = [])).push(handler);

      return function off() {
        var list = _listeners[name];
        if (!list) return;
        var idx = list.indexOf(handler);
        if (idx >= 0) list.splice(idx, 1);
      };
    },

    emit: function (eventName, detail) {
      if (!eventName) throw new Error('Panes.events.emit: missing eventName');

      var name = String(eventName);
      var list = _listeners[name];
      if (!list || list.length === 0) return;

      // Snapshot the list in case handlers add/remove listeners while emitting.
      var snapshot = list.slice();
      var ev = { type: name, detail: detail || {} };

      snapshot.forEach(function (fn) {
        try { fn(ev); } catch (e) { /* ignore individual handler failures */ }
      });
    }
  };

  var State = {
    get: function (key) {
      return _state[String(key)];
    },

    set: function (key, value) {
      var k = String(key);
      _state[k] = value;

      // Emit generic + key-specific events
      Events.emit('state:changed', { key: k, value: value });
      Events.emit('state:changed:' + k, { key: k, value: value });

      return value;
    },

    has: function (key) {
      return Object.prototype.hasOwnProperty.call(_state, String(key));
    }
  };

  function register(name, factory) {
    if (!name) throw new Error('Panes.register: missing name');
    if (typeof factory !== 'function') throw new Error('Panes.register: factory must be a function');
    registry[String(name)] = factory;
  }

  function bootstrap(rootEl) {
    var root = rootEl || document;
    var nodes = root.querySelectorAll('[data-pane]');

    Array.prototype.forEach.call(nodes, function (el) {
      var name = el.dataset && el.dataset.pane;
      if (!name) return;

      // CSS isolation at host level
      el.classList.add('pane-host', hostClass(name));

      var factory = registry[name];
      if (!factory) return;

      try {
        var api = { events: Events, state: State, name: name };
        var inst = factory(el, api) || null;
        instances.push({ el: el, name: name, inst: inst });
      } catch (e) {
        el.innerHTML = '';
        var box = document.createElement('section');
        box.className = 'pane pane--error';
        var h = document.createElement('h2');
        h.className = 'pane-title';
        h.textContent = 'Pane error: ' + name;
        var pre = document.createElement('pre');
        pre.textContent = String((e && (e.stack || e.message)) || e);
        box.appendChild(h);
        box.appendChild(pre);
        el.appendChild(box);
      }
    });
  }

  function destroyAll() {
    instances.forEach(function (rec) {
      if (rec && rec.inst && typeof rec.inst.destroy === 'function') {
        try { rec.inst.destroy(); } catch (e) { /* ignore */ }
      }
    });
    instances = [];
  }

  global.Panes = {
    register: register,
    bootstrap: bootstrap,
    destroyAll: destroyAll,
    events: Events,
    state: State
  };
})(window);