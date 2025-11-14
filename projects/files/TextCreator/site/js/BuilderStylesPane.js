// js/BuilderStylesPane.js
//
// ===============================================
//  STYLES PANE — HOW TO USE
// ===============================================
//
// This pane manages a simple list of "styles" for
// the profile/builder, e.g.:
//
//   "Professional", "Friendly", "Direct", "Concise"
//
// These are stored in the shared builder state:
//
//   window[builderGlobal].styles = [
//     "Professional",
//     "Friendly",
//     "Direct"
//   ];
//
//
// -----------------------------------------------
// 1) Add the pane to your HTML:
//
//   <div
//     data-pane="builder-styles"
//     data-builder-global="LETTER_BUILDER_STATE"
//     data-profile-event="profileLoaded"
//     data-default-styles="Professional,Friendly,Direct,Concise"
//     data-title="Styles">
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
//       loaded. Expects: ev.detail.profile.styles
//       Default: "profileLoaded"
//
//   data-default-styles  (optional)
//       Fallback styles (CSV) used when there is no
//       styles array in state/profile.
//       Example: "Professional,Friendly,Direct"
//
//   data-title           (optional)
//       Custom pane title text. Default: "Styles"
//
//
// -----------------------------------------------
// 3) Programmatic API:
//
//   window.BuilderStyles.setFromArray(arr, globalName)
//
//       - Replaces the builder state's `.styles`
//         array with `arr` (or fallback list).
//       - Re-initializes all [data-pane="builder-styles"]
//         elements, respecting each container's data-*.
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {
  // Default styles used when none are provided
  var FALLBACK_STYLES = ['Professional', 'Friendly', 'Direct', 'Concise'];

  // -------------------------------------------------------------------
  // Convert a raw CSV string to an array of styles.
  // Falls back to FALLBACK_STYLES if empty.
  // -------------------------------------------------------------------
  function parseStyles(raw) {
    if (!raw) return FALLBACK_STYLES.slice();
    return String(raw)
      .split(',')
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  // -------------------------------------------------------------------
  // Ensure the builder state object exists on window[globalName].
  // Creates a default one if missing.
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
  // Read all inputs under rowsWrap and push them into State.styles.
  // This keeps the global state in sync with the UI.
  // -------------------------------------------------------------------
  function syncStyles(rowsWrap, globalName) {
    var State = ensureState(globalName);
    var vals = Array.prototype.map.call(
      rowsWrap.querySelectorAll('input'),
      function (i) { return i.value.trim(); }
    ).filter(Boolean);
    State.styles = vals;
  }

  // -------------------------------------------------------------------
  // Create one "Style" row:
  //   [label "Style"] [input value] [× remove button]
  // -------------------------------------------------------------------
  function addStyleRow(rowsWrap, value, globalName) {
    var State = ensureState(globalName);

    // Input for the style name
    var input = document.createElement('input');
    input.placeholder = 'e.g., Professional';
    input.value = value || '';
    input.addEventListener('input', function () {
      syncStyles(rowsWrap, globalName);
    });

    // Remove button (small ×)
    var btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'mini danger';
    btnRemove.textContent = '×';
    btnRemove.addEventListener('click', function () {
      row.remove();
      syncStyles(rowsWrap, globalName);
    });

    // Label for the row
    var lab = document.createElement('label');
    lab.textContent = 'Style';

    // Row wrapper
    var row = document.createElement('div');
    row.className = 'group builder-style-row';

    row.appendChild(lab);
    row.appendChild(input);
    row.appendChild(btnRemove);

    rowsWrap.appendChild(row);
    syncStyles(rowsWrap, globalName);
  }

  // -------------------------------------------------------------------
  // Render the entire Styles pane into a container.
  // -------------------------------------------------------------------
  function render(container, opts) {
    opts = opts || {};

    var builderGlobal  = opts.builderGlobal || 'LETTER_BUILDER_STATE';
    var titleText      = opts.title || 'Styles';
    var defaultStyles  = opts.defaultStyles || FALLBACK_STYLES.slice();

    var State = ensureState(builderGlobal);

    // Clear container
    container.innerHTML = '';

    // Pane wrapper
    var section = document.createElement('section');
    section.className = 'pane';

    // Pane title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    // Where all style rows will be appended
    var rowsWrap = document.createElement('div');
    rowsWrap.id = 'builder-styles-rows';

    // "+ Add Style" button
    var btnAdd = document.createElement('button');
    btnAdd.className = 'mini';
    btnAdd.textContent = '+ Add Style';

    var actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(btnAdd);

    section.appendChild(h2);
    section.appendChild(rowsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    // Add a new empty style row when clicking "+ Add Style"
    btnAdd.addEventListener('click', function () {
      addStyleRow(rowsWrap, '', builderGlobal);
    });

    // Use existing State.styles if present; otherwise use defaults
    var existing = (State.styles && State.styles.length)
      ? State.styles
      : defaultStyles;

    // Populate rows based on existing/default styles
    existing.forEach(function (s) {
      addStyleRow(rowsWrap, s, builderGlobal);
    });
  }

  // -------------------------------------------------------------------
  // Initialize a single builder-styles pane from a container.
  // Reads data-* configuration and wires up profile event if present.
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    var builderGlobal = ds.builderGlobal || ds.builderState || 'LETTER_BUILDER_STATE';
    var profileEvent  = ds.profileEvent || 'profileLoaded';
    var title         = ds.title || 'Styles';
    var defaultStyles = parseStyles(ds.defaultStyles);

    var opts = {
      builderGlobal: builderGlobal,
      title: title,
      defaultStyles: defaultStyles
    };

    // 1) Initial render using existing builder state or defaults
    render(container, opts);

    // 2) If a profile event is configured, update styles when profile is loaded
    if (profileEvent) {
      window.addEventListener(profileEvent, function (ev) {
        var profile = ev.detail && ev.detail.profile;
        if (!profile) return;

        var State = ensureState(builderGlobal);

        // If profile.styles is a non-empty array, use it; otherwise use defaults
        State.styles = Array.isArray(profile.styles) && profile.styles.length
          ? profile.styles.slice()
          : defaultStyles.slice();

        // Re-render with updated state
        render(container, opts);
      });
    }
  }

  // -------------------------------------------------------------------
  // Auto-init all [data-pane="builder-styles"] on DOMContentLoaded.
  // Also expose a small BuilderStyles helper API.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="builder-styles"]');
    Array.prototype.forEach.call(containers, initOne);

    // Optional: expose helper so other panes/tools can reset styles
    window.BuilderStyles = {
      setFromArray: function (arr, globalName) {
        var key = globalName || 'LETTER_BUILDER_STATE';
        var State = ensureState(key);

        State.styles = Array.isArray(arr) && arr.length
          ? arr.slice()
          : FALLBACK_STYLES.slice();

        var cs = document.querySelectorAll('[data-pane="builder-styles"]');
        Array.prototype.forEach.call(cs, function (c) {
          // Re-render each builder-styles pane with its own data-*
          initOne(c);
        });
      }
    };
  });
})();
