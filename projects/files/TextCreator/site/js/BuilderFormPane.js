// js/BuilderFormPane.js
//
// ===============================================
//  FORM FIELDS PANE — HOW TO USE
// ===============================================
//
// This pane edits a simple key/value object stored
// in the shared builder state:
//
//   window[builderGlobal].form = {
//     applicant: "Jane Doe",
//     role: "Customer Support Analyst",
//     ...
//   };
//
// Each row is:
//   - a "Field Name" (key)
//   - a "Value"
//   - a "Remove" button
//
// -----------------------------------------------
// 1) Add the pane to your HTML:
//
//   <div
//     data-pane="builder-form"
//     data-builder-global="LETTER_BUILDER_STATE"
//     data-profile-event="profileLoaded"
//     data-title="Form Fields"
//     data-default-fields="applicant,role">
//   </div>
//
// -----------------------------------------------
// 2) data-* attributes:
//
//   data-builder-global  (optional)
//       Name of the global object used for state.
//       Default: "LETTER_BUILDER_STATE"
//
//   data-profile-event   (optional)
//       Event name that triggers reloading from a
//       profile object. The handler expects:
//         ev.detail.profile.form
//       Default: "profileLoaded"
//
//   data-title           (optional)
//       Pane title. Default: "Form Fields"
//
//   data-default-fields  (optional)
//       Comma-separated field keys to pre-seed
//       when State.form is empty.
//       Example: "applicant,role,company"
//
// -----------------------------------------------
// 3) Programmatic API:
//
//   window.BuilderForm.setFromObject(obj, globalName)
//
//       - Replaces the State.form object, then
//         re-initializes all [data-pane="builder-form"]
//         containers with their own data-* config.
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {

  // -------------------------------------------------------------------
  // Ensure a builder state object exists on window[globalName].
  // If missing, it creates one with default shape.
  // -------------------------------------------------------------------
  function ensureState(globalName) {
    var key = globalName || 'LETTER_BUILDER_STATE';
    if (!window[key]) {
      window[key] = {
        form: {},       // <-- this pane edits this object
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
  // Take a raw CSV string and turn it into an array of field names.
  // Used to seed default form keys when State.form is empty.
  // -------------------------------------------------------------------
  function parseDefaultFields(raw) {
    if (!raw) return ['applicant', 'role'];
    return String(raw)
      .split(',')
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  // -------------------------------------------------------------------
  // Create a single "field row" block:
  //   - key input ("Field Name")
  //   - value input ("Value")
  //   - remove button
  //
  // Changing either input updates State.form.
  // Removing the row deletes the key from State.form.
  // -------------------------------------------------------------------
  function addFieldRow(rowsWrap, key, val, State) {
    // Key input: field name (object property name)
    var keyInput = document.createElement('input');
    keyInput.className = 'form-key-input';
    keyInput.placeholder = 'key (e.g., applicant)';
    keyInput.value = key || '';

    // Value input: stored value for that key
    var valInput = document.createElement('input');
    valInput.className = 'form-value-input';
    valInput.placeholder = 'value (e.g., Jane Doe)';
    valInput.value = val || '';

    // Keep State.form in sync when the key changes
    keyInput.addEventListener('input', function () {
      var k = keyInput.value.trim();
      if (k) {
        State.form[k] = valInput.value;
      }
    });

    // Keep State.form in sync when the value changes
    valInput.addEventListener('input', function () {
      var k = keyInput.value.trim();
      if (k) {
        State.form[k] = valInput.value;
      }
    });

    // Row for key label + key input (+ remove button)
    var keyRow = document.createElement('div');
    keyRow.className = 'form-field-key-row';
    var kLab = document.createElement('label');
    kLab.textContent = 'Field Name';
    keyRow.appendChild(kLab);
    keyRow.appendChild(keyInput);

    // Row for value label + value input
    var valRow = document.createElement('div');
    valRow.className = 'form-field-value-row';
    var vLab = document.createElement('label');
    vLab.textContent = 'Value';
    valRow.appendChild(vLab);
    valRow.appendChild(valInput);

    // Outer block for this field
    var block = document.createElement('div');
    block.className = 'group form-field-block';

    // Remove button: deletes this key from State.form and DOM
    var btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'mini danger';
    btnRemove.textContent = 'Remove';
    btnRemove.addEventListener('click', function () {
      var k = keyInput.value.trim();
      if (k && State.form && Object.prototype.hasOwnProperty.call(State.form, k)) {
        delete State.form[k];
      }
      if (block.parentNode) {
        block.parentNode.removeChild(block);
      }
    });

    // Put remove button in the key row so it sits on the same visual line
    keyRow.appendChild(btnRemove);

    block.appendChild(keyRow);
    block.appendChild(valRow);

    rowsWrap.appendChild(block);

    // If this row was created from an existing key, store its initial value
    if (key) State.form[key] = val;
  }

  // -------------------------------------------------------------------
  // Render the entire "Form Fields" pane into a container.
  // -------------------------------------------------------------------
  function render(container, opts) {
    opts = opts || {};
    var builderGlobal   = opts.builderGlobal || 'LETTER_BUILDER_STATE';
    var titleText       = opts.title || 'Form Fields';
    var defaultFieldCfg = opts.defaultFields || 'applicant,role';

    var State = ensureState(builderGlobal);

    // Reset the container
    container.innerHTML = '';

    // Pane wrapper
    var section = document.createElement('section');
    section.className = 'pane';

    // Pane title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    // Where all field rows go
    var rowsWrap = document.createElement('div');
    rowsWrap.id = 'builder-form-rows';

    // "+ Add Field" button
    var btnAdd = document.createElement('button');
    btnAdd.className = 'mini';
    btnAdd.textContent = '+ Add Field';

    var actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(btnAdd);

    section.appendChild(h2);
    section.appendChild(rowsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    // Handler for adding a new empty row
    btnAdd.addEventListener('click', function () {
      addFieldRow(rowsWrap, '', '', State);
    });

    // Existing form values from state
    var form = State.form || {};
    var keys = Object.keys(form);

    if (keys.length) {
      // Recreate rows from existing state
      keys.forEach(function (k) {
        addFieldRow(rowsWrap, k, form[k], State);
      });
    } else {
      // No existing form: seed default fields (configurable)
      parseDefaultFields(defaultFieldCfg).forEach(function (k) {
        addFieldRow(rowsWrap, k, '', State);
      });
    }
  }

  // -------------------------------------------------------------------
  // Replace State.form with a new object.
  // -------------------------------------------------------------------
  function applyFormObjectToState(obj, builderGlobal) {
    var State = ensureState(builderGlobal);
    State.form = {};
    Object.keys(obj || {}).forEach(function (k) {
      State.form[k] = obj[k];
    });
  }

  // -------------------------------------------------------------------
  // Initialize a single builder-form pane from its container.
  // Reads data-* attributes for configuration and sets up the
  // profile event listener, if configured.
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};
    var builderGlobal = ds.builderGlobal || ds.builderState || 'LETTER_BUILDER_STATE';
    var profileEvent  = ds.profileEvent || 'profileLoaded';
    var title         = ds.title || 'Form Fields';
    var defaultFields = ds.defaultFields || 'applicant,role';

    var opts = {
      builderGlobal: builderGlobal,
      title: title,
      defaultFields: defaultFields
    };

    // Initial render with current builder state
    render(container, opts);

    // Optionally hook into profile load event
    if (profileEvent) {
      window.addEventListener(profileEvent, function (ev) {
        var profile = ev.detail && ev.detail.profile;
        if (!profile) return;

        // Replace form in state with profile.form
        applyFormObjectToState(profile.form || {}, builderGlobal);

        // Re-render all builder-form panes so they reflect the new form
        var containers = document.querySelectorAll('[data-pane="builder-form"]');
        Array.prototype.forEach.call(containers, function (c) {
          // Re-read each container’s data-* so each pane can have its own config
          initOne(c);
        });
      });
    }
  }

  // -------------------------------------------------------------------
  // Auto-init all [data-pane="builder-form"] containers on DOM ready.
  // Expose a simple BuilderForm helper API.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="builder-form"]');
    Array.prototype.forEach.call(containers, initOne);

    // Optional helper if you want to drive it manually:
    window.BuilderForm = {
      setFromObject: function (obj, globalName) {
        var g = globalName || 'LETTER_BUILDER_STATE';
        applyFormObjectToState(obj || {}, g);

        var containers = document.querySelectorAll('[data-pane="builder-form"]');
        Array.prototype.forEach.call(containers, function (c) {
          initOne(c);
        });
      }
    };
  });

})();
