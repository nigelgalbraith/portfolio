// js/TextEntryPane.js
//
// Simple pane that renders a titled editable text area.
// - PanesCore-scoped (register + bootstrap)
// - Optional: writes current text into Panes state and emits scoped events
//
// HOW TO USE (basic, DOM-only):
//   <div
//     data-pane="text-entry"
//     data-title="English"
//     data-textarea-id="english-text"
//     data-placeholder="Type English text here...">
//   </div>
//
// HOW TO USE (state-driven):
//   <div
//     data-pane="text-entry"
//     data-title="English"
//     data-textarea-id="english-text"
//     data-placeholder="Type English text here..."
//     data-state-key="TRANSLATOR"
//     data-field-key="english">
//   </div>

(function () {
  'use strict';

  function ensureObj(x) {
    return (x && typeof x === 'object') ? x : {};
  }

  function readEditableText(el) {
    if (!el) return '';
    if ('value' in el) return String(el.value || '');
    return String(el.textContent || '');
  }

  function setEditableText(el, value) {
    if (!el) return;
    var v = (value == null) ? '' : String(value);
    if ('value' in el) el.value = v;
    else el.textContent = v;
  }

  function initOne(container, api) {
    if (!api || !api.events || !api.state) {
      throw new Error('TextEntryPane: missing Panes api');
    }

    var ds = container.dataset || {};

    var title       = ds.title || 'Text';
    var textareaId  = ds.textareaId || 'text-entry';
    var placeholder = ds.placeholder || 'Type here...';

    // Optional state wiring
    var stateKey = ds.stateKey || null;     // e.g. "TRANSLATOR"
    var fieldKey = ds.fieldKey || null;     // e.g. "english"
    var initialValue = ds.initialValue || ''; // optional seed (only used if state is empty)

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--text-entry';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = title;

    var wrapper = document.createElement('div');
    wrapper.className = 'field';

    var div = document.createElement('div');
    div.id = textareaId;
    div.className = 'letter';
    div.contentEditable = 'true';
    div.setAttribute('data-placeholder', placeholder);

    wrapper.appendChild(div);
    section.appendChild(h2);
    section.appendChild(wrapper);
    container.appendChild(section);

    function commitToState() {
      if (!stateKey || !fieldKey) return;

      var current = api.state.get(stateKey);
      var next = ensureObj(current);

      next[fieldKey] = readEditableText(div);

      api.state.set(stateKey, next);

      // Convenience events (scoped)
      api.events.emit('text:changed', { stateKey: stateKey, fieldKey: fieldKey, value: next[fieldKey] });
      api.events.emit('text:changed:' + fieldKey, { stateKey: stateKey, fieldKey: fieldKey, value: next[fieldKey] });
    }

    function seedFromStateIfPresent() {
      if (!stateKey || !fieldKey) return;

      var st = api.state.get(stateKey);
      st = ensureObj(st);

      if (st[fieldKey] != null && String(st[fieldKey]) !== '') {
        setEditableText(div, st[fieldKey]);
        return;
      }

      // If state empty, seed with initialValue (and persist)
      if (initialValue) {
        setEditableText(div, initialValue);
        commitToState();
      }
    }

    function onInput() {
      commitToState();
    }

    // Seed + wire
    seedFromStateIfPresent();
    div.addEventListener('input', onInput);

    return {
      destroy: function () {
        div.removeEventListener('input', onInput);
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('TextEntryPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('text-entry', function (container, api) {
    container.classList.add('pane-text-entry');
    return initOne(container, api);
  });
})();