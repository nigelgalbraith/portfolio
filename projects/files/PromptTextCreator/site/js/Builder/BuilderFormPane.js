// js/Builder/BuilderFormPane.js
//
// Builder form pane (scoped).
// - Edits profile.form (key/value pairs)
// - Reads/writes via Panes scoped state
// - Re-renders on state:changed:<stateKey>

(function () {
  'use strict';

  function parseDefaultFields(raw) {
    if (!raw) return ['applicant', 'role'];
    return String(raw)
      .split(',')
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  function getState(api, stateKey) {
    var st = api.state.get(stateKey);
    if (!st || typeof st !== 'object') {
      st = {
        form: {},
        styles: [],
        options: [],
        mode: 'template',
        template: '',
        prompt: '',
        ollama: null
      };
      api.state.set(stateKey, st);
    }
    if (!st.form || typeof st.form !== 'object') st.form = {};
    if (!Array.isArray(st.styles)) st.styles = [];
    if (!Array.isArray(st.options)) st.options = [];
    return st;
  }

  function setForm(api, stateKey, nextForm) {
    var st = getState(api, stateKey);
    st.form = nextForm || {};
    api.state.set(stateKey, st);
  }

  function render(container, api, cfg, markLocalWrite) {
    var titleText = cfg.title || 'Form Fields';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--builder-form';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    var rowsWrap = document.createElement('div');
    rowsWrap.className = 'builder-form-rows';

    var btnAdd = document.createElement('button');
    btnAdd.className = 'mini';
    btnAdd.type = 'button';
    btnAdd.textContent = '+ Add Field';

    var actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(btnAdd);

    section.appendChild(h2);
    section.appendChild(rowsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    function readCurrentFormFromDOM() {
      var out = {};
      var blocks = rowsWrap.querySelectorAll('.form-field-block');
      Array.prototype.forEach.call(blocks, function (block) {
        var keyInput = block.querySelector('input[data-role="key"]');
        var valInput = block.querySelector('input[data-role="val"]');
        var k = keyInput ? String(keyInput.value || '').trim() : '';
        if (!k) return;
        out[k] = valInput ? String(valInput.value || '') : '';
      });
      return out;
    }

    function commitDOMToState() {
      markLocalWrite();
      setForm(api, cfg.stateKey, readCurrentFormFromDOM());
    }

    function addFieldRow(key, val) {
      var block = document.createElement('div');
      block.className = 'group form-field-block';

      var keyRow = document.createElement('div');
      keyRow.className = 'form-field-key-row';

      var kLab = document.createElement('label');
      kLab.textContent = 'Field Name';

      var keyInput = document.createElement('input');
      keyInput.className = 'form-key-input';
      keyInput.placeholder = 'key (e.g., applicant)';
      keyInput.value = key || '';
      keyInput.dataset.role = 'key';

      var btnRemove = document.createElement('button');
      btnRemove.type = 'button';
      btnRemove.className = 'mini danger';
      btnRemove.textContent = 'Remove';

      keyRow.appendChild(kLab);
      keyRow.appendChild(keyInput);
      keyRow.appendChild(btnRemove);

      var valRow = document.createElement('div');
      valRow.className = 'form-field-value-row';

      var vLab = document.createElement('label');
      vLab.textContent = 'Value';

      var valInput = document.createElement('input');
      valInput.className = 'form-value-input';
      valInput.placeholder = 'value (e.g., Jane Doe)';
      valInput.value = val || '';
      valInput.dataset.role = 'val';

      valRow.appendChild(vLab);
      valRow.appendChild(valInput);

      function onAnyInput() {
        commitDOMToState();
      }

      keyInput.addEventListener('input', onAnyInput);
      valInput.addEventListener('input', onAnyInput);

      btnRemove.addEventListener('click', function () {
        block.remove();
        commitDOMToState();
      });

      block.appendChild(keyRow);
      block.appendChild(valRow);
      rowsWrap.appendChild(block);
    }

    // Seed UI from state
    var st = getState(api, cfg.stateKey);
    var form = st.form || {};
    var keys = Object.keys(form);

    if (keys.length) {
      keys.forEach(function (k) { addFieldRow(k, form[k]); });
    } else {
      parseDefaultFields(cfg.defaultFieldsRaw).forEach(function (k) {
        addFieldRow(k, '');
      });
      commitDOMToState(); // persist seeded defaults
    }

    btnAdd.addEventListener('click', function () {
      addFieldRow('', '');
      commitDOMToState();
    });

    return {
      destroy: function () { /* no-op */ }
    };
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('BuilderFormPane: missing Panes api');
    }

    var ds = container.dataset || {};
    var cfg = {
      stateKey: ds.stateKey || 'TEXT_PROFILE',
      title: ds.title || 'Form Fields',
      defaultFieldsRaw: ds.defaultFields || 'applicant,role'
    };

    // Prevent re-render loops when *this pane* writes state on input.
    var ignoreNext = false;
    function markLocalWrite() {
      ignoreNext = true;
      setTimeout(function () { ignoreNext = false; }, 0);
    }

    render(container, api, cfg, markLocalWrite);

    // Re-render when state changes externally (e.g., ProfileLoader loads a file).
    var off = api.events.on('state:changed:' + cfg.stateKey, function () {
      if (ignoreNext) return;
      render(container, api, cfg, markLocalWrite);
    });

    return {
      destroy: function () {
        if (off) off();
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('BuilderFormPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('builder-form', function (container, api) {
    container.classList.add('pane-builder-form');
    return initOne(container, api);
  });
})();