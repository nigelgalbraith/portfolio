// js/Builder/BuilderMetaPane.js
//
// Builder meta pane (scoped).
// - Edits profile meta: mode, template, prompt, ollama
// - Reads/writes via Panes scoped state
// - Re-renders on state:changed:<stateKey>

(function () {
  'use strict';

  var FALLBACK_MODEL = 'phi3';
  var FALLBACK_TEMP = 0.3;
  var MODES = ['template', 'llm'];

  function parseTemp(raw, fallback) {
    var n = Number(raw);
    return isNaN(n) ? fallback : n;
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
    if (!Array.isArray(st.options)) st.options = [];
    if (!st.form || typeof st.form !== 'object') st.form = {};
    return st;
  }

  function setDisabled(el, disabled) {
    el.disabled = !!disabled;
    el.classList.toggle('is-disabled', !!disabled);
  }

  function render(container, api, cfg, markLocalWrite) {
    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--builder-meta';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = cfg.title || 'Profile';

    // Mode
    var modeGroup = document.createElement('div');
    modeGroup.className = 'group';

    var modeLab = document.createElement('label');
    modeLab.textContent = 'Mode';

    var selMode = document.createElement('select');
    MODES.forEach(function (m) {
      var opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      selMode.appendChild(opt);
    });

    modeGroup.appendChild(modeLab);
    modeGroup.appendChild(selMode);

    // Model
    var modelGroup = document.createElement('div');
    modelGroup.className = 'group';

    var modelLab = document.createElement('label');
    modelLab.textContent = 'LLM Model';

    var modelInput = document.createElement('input');

    modelGroup.appendChild(modelLab);
    modelGroup.appendChild(modelInput);

    // Temp
    var tempGroup = document.createElement('div');
    tempGroup.className = 'group';

    var tempLab = document.createElement('label');
    tempLab.textContent = 'LLM Temperature';

    var tempInput = document.createElement('input');
    tempInput.type = 'number';
    tempInput.step = 0.05;
    tempInput.min = 0;
    tempInput.max = 1;

    tempGroup.appendChild(tempLab);
    tempGroup.appendChild(tempInput);

    // Template
    var tmplLab = document.createElement('label');
    tmplLab.textContent = 'Template';

    var tmplArea = document.createElement('textarea');

    // Prompt
    var promptLab = document.createElement('label');
    promptLab.textContent = 'Prompt';

    var promptArea = document.createElement('textarea');

    section.appendChild(h2);
    section.appendChild(modeGroup);
    section.appendChild(modelGroup);
    section.appendChild(tempGroup);
    section.appendChild(tmplLab);
    section.appendChild(tmplArea);
    section.appendChild(promptLab);
    section.appendChild(promptArea);
    container.appendChild(section);

    function syncFromDOM() {
      var st = getState(api, cfg.stateKey);

      st.mode = (selMode.value === 'llm') ? 'llm' : 'template';
      var isLLM = st.mode === 'llm';

      st.template = tmplArea.value || '';
      st.prompt = promptArea.value || '';

      st.ollama = isLLM
        ? {
            model: modelInput.value || cfg.defaultModel,
            options: { temperature: parseTemp(tempInput.value, cfg.defaultTemp) }
          }
        : null;

      // enable/disable fields by mode
      setDisabled(tmplArea, isLLM);
      setDisabled(promptArea, !isLLM);
      setDisabled(modelInput, !isLLM);
      setDisabled(tempInput, !isLLM);

      // This write will trigger state:changed — guard in initOne handles loop.
      markLocalWrite();
      api.state.set(cfg.stateKey, st);
    }

    // Init UI from state
    var st0 = getState(api, cfg.stateKey);

    selMode.value = (st0.mode === 'llm') ? 'llm' : 'template';

    var stModel = st0.ollama && st0.ollama.model;
    var stTemp =
      (st0.ollama && st0.ollama.options && typeof st0.ollama.options.temperature === 'number')
        ? st0.ollama.options.temperature
        : null;

    modelInput.value = stModel || cfg.defaultModel;
    tempInput.value = (stTemp != null) ? stTemp : cfg.defaultTemp;
    tmplArea.value = st0.template || '';
    promptArea.value = st0.prompt || '';

    // Wire listeners
    selMode.addEventListener('change', syncFromDOM);
    modelInput.addEventListener('input', syncFromDOM);
    tempInput.addEventListener('input', syncFromDOM);
    tmplArea.addEventListener('input', syncFromDOM);
    promptArea.addEventListener('input', syncFromDOM);

    // First sync to enforce disable states (without changing values unexpectedly)
    // This will write state once, which is fine.
    syncFromDOM();

    return { destroy: function () {} };
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('BuilderMetaPane: missing Panes api');
    }

    var ds = container.dataset || {};

    var cfg = {
      stateKey: ds.stateKey || 'TEXT_PROFILE',
      title: ds.title || 'Profile',
      defaultModel: ds.defaultModel || FALLBACK_MODEL,
      defaultTemp: parseTemp(ds.defaultTemp, FALLBACK_TEMP)
    };

    // Prevent loops when this pane writes state during input.
    var ignoreNext = false;
    function markLocalWrite() {
      ignoreNext = true;
      setTimeout(function () { ignoreNext = false; }, 0);
    }

    render(container, api, cfg, markLocalWrite);

    // Re-render when state changes externally (e.g., ProfileLoaderPane loads a file).
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
    throw new Error('BuilderMetaPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('builder-meta', function (container, api) {
    container.classList.add('pane-builder-meta');
    return initOne(container, api);
  });
})();