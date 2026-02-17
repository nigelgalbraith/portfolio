// js/Builder/BuilderStylesPane.js
//
// Builder styles pane (scoped).
// - Edits profile.styles (array of strings)
// - Reads/writes via Panes scoped state
// - Re-renders on state:changed:<stateKey>

(function () {
  'use strict';

  var FALLBACK_STYLES = ['Professional', 'Friendly', 'Direct', 'Concise'];

  function parseStyles(raw) {
    if (!raw) return FALLBACK_STYLES.slice();
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
    if (!Array.isArray(st.styles)) st.styles = [];
    return st;
  }

  function setStyles(api, stateKey, styles) {
    var st = getState(api, stateKey);
    st.styles = Array.isArray(styles) ? styles : [];
    api.state.set(stateKey, st);
  }

  function render(container, api, cfg, markLocalWrite) {
    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--builder-styles';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = cfg.title || 'Styles';

    var rowsWrap = document.createElement('div');
    rowsWrap.className = 'builder-styles-rows';

    var btnAdd = document.createElement('button');
    btnAdd.className = 'mini';
    btnAdd.type = 'button';
    btnAdd.textContent = '+ Add Style';

    var actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(btnAdd);

    section.appendChild(h2);
    section.appendChild(rowsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    function readStylesFromDOM() {
      var inputs = rowsWrap.querySelectorAll('input[data-role="style"]');
      return Array.prototype.map.call(inputs, function (i) {
        return String(i.value || '').trim();
      }).filter(Boolean);
    }

    function commitDOMToState() {
      markLocalWrite();
      setStyles(api, cfg.stateKey, readStylesFromDOM());
    }

    function addStyleRow(value) {
      var row = document.createElement('div');
      row.className = 'group builder-style-row';

      var lab = document.createElement('label');
      lab.textContent = 'Style';

      var input = document.createElement('input');
      input.placeholder = 'e.g., Professional';
      input.value = value || '';
      input.dataset.role = 'style';

      var btnRemove = document.createElement('button');
      btnRemove.type = 'button';
      btnRemove.className = 'mini danger';
      btnRemove.textContent = '×';

      input.addEventListener('input', commitDOMToState);
      btnRemove.addEventListener('click', function () {
        row.remove();
        commitDOMToState();
      });

      row.appendChild(lab);
      row.appendChild(input);
      row.appendChild(btnRemove);
      rowsWrap.appendChild(row);
    }

    // Seed UI from state (or defaults)
    var st = getState(api, cfg.stateKey);

    var existing = (Array.isArray(st.styles) && st.styles.length)
      ? st.styles
      : cfg.defaultStyles;

    if (!existing.length) existing = FALLBACK_STYLES.slice();

    existing.forEach(function (s) { addStyleRow(s); });

    // Persist seeded defaults into state if state was empty
    if (!st.styles || !st.styles.length) {
      commitDOMToState();
    }

    btnAdd.addEventListener('click', function () {
      addStyleRow('');
      commitDOMToState();
    });

    return { destroy: function () {} };
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('BuilderStylesPane: missing Panes api');
    }

    var ds = container.dataset || {};
    var cfg = {
      stateKey: ds.stateKey || 'TEXT_PROFILE',
      title: ds.title || 'Styles',
      defaultStyles: parseStyles(ds.defaultStyles)
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
    throw new Error('BuilderStylesPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('builder-styles', function (container, api) {
    container.classList.add('pane-builder-styles');
    return initOne(container, api);
  });
})();