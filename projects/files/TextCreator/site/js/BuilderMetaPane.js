// js/BuilderMetaPane.js
//
// ===============================================
//  META / LLM CONFIG PANE — HOW TO USE
// ===============================================
//
// This pane edits the *meta* configuration for your
// profile builder, including:
//
//   - mode:       "template" or "llm"
//   - template:   static letter template text
//   - prompt:     LLM prompt text
//   - ollama:     { model, options: { temperature } }
//
// Data is stored in the shared builder global:
//
//   window[builderGlobal] = {
//     form:    {...},      // from BuilderFormPane
//     styles:  [...],      // from BuilderStylesPane
//     options: [...],      // from BuilderChecklistPane
//     mode:    "template" | "llm",
//     template: "Your template...",
//     prompt:   "Your LLM prompt...",
//     ollama: {
//       model: "phi3",
//       options: { temperature: 0.3 }
//     } | null
//   };
//
//
// -----------------------------------------------
// 1) Add the pane to your HTML:
//
//   <div
//     data-pane="builder-meta"
//     data-builder-global="LETTER_BUILDER_STATE"
//     data-profile-event="profileLoaded"
//     data-title="Profile"
//     data-default-model="phi3"
//     data-default-temp="0.3">
//   </div>
//
//
// -----------------------------------------------
// 2) data-* attributes:
//
//   data-builder-global  (optional)
//       Name of the global builder state object.
//       Default: "LETTER_BUILDER_STATE"
//
//   data-profile-event   (optional)
//       Event name to listen for when a profile is
//       loaded externally. The event is expected to
//       have: ev.detail.profile
//       Default: "profileLoaded"
//
//   data-title           (optional)
//       Title text for this pane. Default: "Profile"
//
//   data-default-model   (optional)
//       Fallback LLM model name if none is found in
//       state or profile. Default: "phi3"
//
//   data-default-temp    (optional)
//       Fallback LLM temperature if none is found in
//       state or profile. Default: 0.3
//
//
// -----------------------------------------------
// 3) Programmatic API:
//
//   window.BuilderMeta.setFromProfile(profile, globalName, extraOpts)
//
//     - Applies `profile` into the builder state:
//         { mode, template, prompt, ollama }
//     - Then re-renders all [data-pane="builder-meta"]
//       containers.
//
//     - globalName  (optional)
//         Name of builder global. Default: "LETTER_BUILDER_STATE"
//
//     - extraOpts   (optional)
//         { defaultModel, defaultTemp } overrides.
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {
  // Default model + temperature used if not present in state/profile
  var FALLBACK_MODEL = 'phi3';
  var FALLBACK_TEMP  = 0.3;

  // Supported modes for the builder
  var MODES = ['template', 'llm'];

  // -------------------------------------------------------------------
  // Parse a temperature value safely, falling back if invalid.
  // -------------------------------------------------------------------
  function parseTemp(raw, fallback) {
    var n = Number(raw);
    return isNaN(n) ? fallback : n;
  }

  // -------------------------------------------------------------------
  // Ensure the builder global state exists.
  // If missing, create a default state object.
  // -------------------------------------------------------------------
  function ensureState(globalName) {
    var key = globalName || 'LETTER_BUILDER_STATE';
    if (!window[key]) {
      window[key] = {
        form: {},
        styles: [],
        options: [],
        mode: 'template',
        template: '',
        prompt: '',
        ollama: null
      };
    }
    return window[key];
  }

  // -------------------------------------------------------------------
  // Render the meta pane: mode, model, temperature, template, prompt.
  // -------------------------------------------------------------------
  function render(container, opts) {
    opts = opts || {};

    var builderGlobal = opts.builderGlobal || 'LETTER_BUILDER_STATE';
    var titleText     = opts.title || 'Profile';
    var defModel      = opts.defaultModel || FALLBACK_MODEL;
    var defTemp       = typeof opts.defaultTemp === 'number'
      ? opts.defaultTemp
      : FALLBACK_TEMP;

    var State = ensureState(builderGlobal);

    // Clear existing content
    container.innerHTML = '';

    // Main pane element
    var section = document.createElement('section');
    section.className = 'pane';

    // Pane title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    // -----------------------------
    // Mode selector (template / llm)
    // -----------------------------
    var modeGroup = document.createElement('div');
    modeGroup.className = 'group';

    var modeLab = document.createElement('label');
    modeLab.textContent = 'Mode';

    var sel = document.createElement('select');
    MODES.forEach(function (m) {
      var opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      sel.appendChild(opt);
    });

    modeGroup.appendChild(modeLab);
    modeGroup.appendChild(sel);

    // -----------------------------
    // LLM Model
    // -----------------------------
    var modelGroup = document.createElement('div');
    modelGroup.className = 'group';

    var modelLab = document.createElement('label');
    modelLab.textContent = 'LLM Model';

    var modelInput = document.createElement('input');

    modelGroup.appendChild(modelLab);
    modelGroup.appendChild(modelInput);

    // -----------------------------
    // LLM Temperature
    // -----------------------------
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

    // -----------------------------
    // Template text area
    // -----------------------------
    var tmplLab = document.createElement('label');
    tmplLab.textContent = 'Template';

    var tmplArea = document.createElement('textarea');

    // -----------------------------
    // Prompt text area
    // -----------------------------
    var promptLab = document.createElement('label');
    promptLab.textContent = 'Prompt';

    var promptArea = document.createElement('textarea');

    // Assemble pane
    section.appendChild(h2);
    section.appendChild(modeGroup);
    section.appendChild(modelGroup);
    section.appendChild(tempGroup);
    section.appendChild(tmplLab);
    section.appendChild(tmplArea);
    section.appendChild(promptLab);
    section.appendChild(promptArea);
    container.appendChild(section);

    // Helper to handle disabling + visual disabled state
    function setDisabled(el, disabled) {
      el.disabled = !!disabled;
      el.classList.toggle('is-disabled', !!disabled);
    }

    // -----------------------------------------------------------------
    // Sync function:
    // - Reads DOM inputs
    // - Updates State.{mode, template, prompt, ollama}
    // - Enables/disables fields depending on mode
    // -----------------------------------------------------------------
    function sync() {
      // Mode: either "template" or "llm"
      State.mode = sel.value === 'llm' ? 'llm' : 'template';
      var isLLM = State.mode === 'llm';

      // Template + prompt
      State.template = tmplArea.value || '';
      State.prompt   = promptArea.value || '';

      // LLM config only meaningful in "llm" mode
      State.ollama = isLLM
        ? {
            model: modelInput.value || defModel,
            options: {
              temperature: parseTemp(tempInput.value, defTemp)
            }
          }
        : null;

      // When in LLM mode, disable the template (so prompt drives generation)
      // When in template mode, disable LLM fields (model/temperature/prompt)
      setDisabled(tmplArea,  isLLM);
      setDisabled(promptArea, !isLLM);
      setDisabled(modelInput, !isLLM);
      setDisabled(tempInput,  !isLLM);
    }

    // -----------------------------------------------------------------
    // Initialise UI from existing state (or defaults).
    // -----------------------------------------------------------------

    // Mode
    sel.value = State.mode === 'llm' ? 'llm' : 'template';

    // Existing ollama model + temperature
    var stateModel = State.ollama && State.ollama.model;
    var stateTemp  = State.ollama &&
                     State.ollama.options &&
                     typeof State.ollama.options.temperature === 'number'
                       ? State.ollama.options.temperature
                       : null;

    // Set initial field values
    modelInput.value = stateModel || defModel;
    tempInput.value  = stateTemp != null ? stateTemp : defTemp;
    tmplArea.value   = State.template || '';
    promptArea.value = State.prompt || '';

    // Wire input listeners
    sel.addEventListener('change', sync);
    modelInput.addEventListener('input', sync);
    tempInput.addEventListener('input', sync);
    tmplArea.addEventListener('input', sync);
    promptArea.addEventListener('input', sync);

    // Initial sync to enforce correct enabled/disabled states
    sync();
  }

  // -------------------------------------------------------------------
  // Apply a loaded profile into the builder state, then re-render
  // all builder-meta panes so the UI reflects it.
  // -------------------------------------------------------------------
  function applyProfileToState(profile, builderGlobal, opts) {
    opts = opts || {};

    var defModel = opts.defaultModel || FALLBACK_MODEL;
    var defTemp  = typeof opts.defaultTemp === 'number'
      ? opts.defaultTemp
      : FALLBACK_TEMP;

    var State = ensureState(builderGlobal);

    // Mode comes from profile, but only "llm" is respected for LLM mode
    State.mode     = profile.mode === 'llm' ? 'llm' : 'template';
    State.template = profile.template || '';
    State.prompt   = profile.prompt || '';

    // Handle ollama block if present on profile
    if (profile.ollama) {
      var pModel = profile.ollama.model || defModel;
      var pTemp  = (profile.ollama.options &&
                    typeof profile.ollama.options.temperature === 'number')
        ? profile.ollama.options.temperature
        : defTemp;

      State.ollama = {
        model: pModel,
        options: { temperature: pTemp }
      };
    } else {
      State.ollama = null;
    }

    // Re-render all builder-meta panes so UI reflects updated state
    var containers = document.querySelectorAll('[data-pane="builder-meta"]');
    Array.prototype.forEach.call(containers, function (c) {
      // Re-read that container's data-* so each can have its own config
      initOne(c);
    });
  }

  // -------------------------------------------------------------------
  // Initialize a single builder-meta pane from its container.
  // Reads its data-* configuration and wires profile event listener.
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    var builderGlobal = ds.builderGlobal || ds.builderState || 'LETTER_BUILDER_STATE';
    var profileEvent  = ds.profileEvent || 'profileLoaded';
    var title         = ds.title || 'Profile';
    var defaultModel  = ds.defaultModel || FALLBACK_MODEL;
    var defaultTemp   = parseTemp(ds.defaultTemp, FALLBACK_TEMP);

    var opts = {
      builderGlobal: builderGlobal,
      title: title,
      defaultModel: defaultModel,
      defaultTemp: defaultTemp
    };

    // Initial render
    render(container, opts);

    // Hook into profile load event, if configured
    if (profileEvent) {
      window.addEventListener(profileEvent, function (ev) {
        var profile = ev.detail && ev.detail.profile;
        if (!profile) return;
        applyProfileToState(profile, builderGlobal, opts);
      });
    }
  }

  // -------------------------------------------------------------------
  // Auto-init all [data-pane="builder-meta"] on DOM ready.
  // Expose a small helper API for manual profile injection.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="builder-meta"]');
    Array.prototype.forEach.call(containers, initOne);

    // Optional helper for driving meta from code
    window.BuilderMeta = {
      setFromProfile: function (profile, globalName, extraOpts) {
        applyProfileToState(
          profile,
          globalName || 'LETTER_BUILDER_STATE',
          extraOpts || {}
        );
      }
    };
  });

})();
