// js/GeneratorFormPane.js
//
// ===============================================
//  GENERATOR FORM PANE — HOW TO USE
// ===============================================
//
// This pane renders the main "Details" form on the
// generator page, based on the profile schema/data.
//
// It uses either:
//
//   • profile.formSchema  (if provided)
//        -> explicit list of fields to render
//
//   • OR profile.form / profile.profile
//        -> infer schema from object keys
//
// The rendered fields are used later by
// GeneratorPreviewPane.buildCtx() via:
//
//   input.dataset.key = <field key>
//
//
// -----------------------------------------------
// 1) Add to HTML:
//
//   <div
//     data-pane="generator-form"
//     data-profile-event="profileLoaded"
//     data-profile-global="LETTER_PROFILE"
//     data-title="Details"
//     data-default-styles="Professional,Friendly,Direct,Concise">
//   </div>
//
//
// -----------------------------------------------
// 2) Expected profile shape (generator side):
//
//   {
//     form: {
//       applicant: "Jane Doe",
//       role: "Support Analyst",
//       style: "Professional",
//       cover_letter_desc: "..."
//     },
//     styles: ["Professional", "Friendly", ...],
//     formSchema: [               // OPTIONAL override
//       { key: "applicant", label: "Applicant", type: "text" },
//       { key: "role",      label: "Role",      type: "text" },
//       { key: "style",     label: "Style",     type: "select" },
//       { key: "summary",   label: "Summary",   type: "textarea", rows: 20 }
//     ]
//   }
//
// - If formSchema exists and has entries, it is used directly.
// - Otherwise keys are inferred from profile.form or profile.profile.
//
// -----------------------------------------------
// 3) data-* attributes:
//
//   data-profile-event
//       Event name to listen for when a profile is loaded.
//       Default: "profileLoaded"
//
//   data-profile-global
//       Global variable to read an already-loaded profile from.
//       Default: "LETTER_PROFILE"
//
//   data-title
//       Pane title text.
//       Default: "Details"
//
//   data-default-styles
//       Fallback styles (CSV) used for <select> style fields if
//       profile.styles is not defined.
//       Example: "Professional,Friendly,Direct"
//
//
// -----------------------------------------------
// 4) Field types:
//
//   • "text"      → <input>
//   • "textarea"  → <textarea>
//   • "select"    → <select> (populated from profile.styles or defaultStyles)
//
// A field is guessed as "textarea" if its key contains "desc",
// as "select" if its key contains "style", otherwise "text",
// unless formSchema explicitly specifies a type.
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {
  var DEFAULT_TEXTAREA_ROWS = 20;

  // -------------------------------------------------------------------
  // Convert a key like "applicant_name" → "Applicant Name"
  // -------------------------------------------------------------------
  function toTitle(label) {
    return String(label || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  // -------------------------------------------------------------------
  // Parse default styles from a CSV string.
  // Used as fallback if profile.styles is absent.
  // -------------------------------------------------------------------
  function parseStyles(raw) {
    if (!raw) {
      return ['Professional', 'Friendly', 'Direct', 'Concise'];
    }
    // e.g. "Professional, Friendly, Direct"
    return String(raw)
      .split(',')
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  // -------------------------------------------------------------------
  // Build a form schema from the profile.
  //
  // Priority:
  //   1) profile.formSchema (if array and non-empty)
  //   2) Infer from profile.form or profile.profile object keys.
  //
  // Inferred fields:
  //   - type = 'textarea' if key contains "desc"
  //   - type = 'select'   if key contains "style"
  //   - otherwise 'text'
  // -------------------------------------------------------------------
  function buildSchema(profile) {
    profile = profile || {};

    // 1) Explicit schema
    if (Array.isArray(profile.formSchema) && profile.formSchema.length) {
      return profile.formSchema;
    }

    // 2) Infer from form or profile object
    var form = profile.form || profile.profile || {};
    var keys = Object.keys(form);

    return keys.map(function (key) {
      var lower = key.toLowerCase();
      var type = 'text';

      if (lower.indexOf('desc') !== -1) {
        type = 'textarea';
      } else if (lower.indexOf('style') !== -1) {
        type = 'select';
      }

      return {
        key: key,
        label: toTitle(key),
        type: type,
        rows: DEFAULT_TEXTAREA_ROWS
      };
    });
  }

  // -------------------------------------------------------------------
  // Render the generator form into the container:
  //   - Title at the top
  //   - One group per schema field
  //   - Field values prefilled from profile.form/profile.profile
  //   - For "select" fields, options come from profile.styles or defaultStyles
  // -------------------------------------------------------------------
  function renderForm(container, profile, opts) {
    opts = opts || {};

    var titleText = opts.title || 'Details';

    // Fallback style list used for <select> fields
    var defaultStyles = opts.defaultStyles || ['Professional', 'Friendly', 'Direct', 'Concise'];

    // Clear container
    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane';

    var h2 = document.createElement('h2');
    h2.textContent = titleText;
    h2.className = 'pane-title';

    var wrap = document.createElement('div');

    // Schema from profile (formSchema or inferred)
    var schema = buildSchema(profile);

    // Prefill values from profile.form or profile.profile
    var formDefaults = (profile && (profile.form || profile.profile)) || {};

    // Styles array for <select> fields
    var styles = Array.isArray(profile && profile.styles)
      ? profile.styles
      : defaultStyles;

    schema.forEach(function (field) {
      var key   = field.key;
      var label = field.label;
      var type  = field.type;
      var rows  = field.rows || DEFAULT_TEXTAREA_ROWS;

      var group = document.createElement('div');
      group.className = 'group';

      var lab = document.createElement('label');
      lab.textContent = label;

      var input;

      if (type === 'textarea') {
        // Multi-line text field
        input = document.createElement('textarea');
        input.rows = rows;
      } else if (type === 'select') {
        // Select from available styles
        input = document.createElement('select');
        styles.forEach(function (s) {
          var opt = document.createElement('option');
          opt.value = s;
          opt.textContent = s;
          input.appendChild(opt);
        });
      } else {
        // Default single-line text input
        input = document.createElement('input');
      }

      // Key used later by GeneratorPreviewPane.buildCtx()
      input.dataset.key = key;

      // Prefill from profile data if present
      var initial = formDefaults[key];
      if (initial != null) {
        input.value = String(initial);
      }

      group.appendChild(lab);
      group.appendChild(input);
      wrap.appendChild(group);
    });

    section.appendChild(h2);
    section.appendChild(wrap);
    container.appendChild(section);
  }

  // -------------------------------------------------------------------
  // Initialize one generator-form pane:
  //   - Optional immediate render from window[profileGlobal]
  //   - Then listen for profile-loaded event to re-render
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    var eventName      = ds.profileEvent || ds.profileEventName || 'profileLoaded';
    var profileGlobal  = ds.profileGlobal || 'LETTER_PROFILE';
    var title          = ds.title || 'Details';
    var defaultStyles  = parseStyles(ds.defaultStyles);

    var opts = {
      title: title,
      defaultStyles: defaultStyles
    };

    // 1) If a profile is already loaded, render immediately
    if (window[profileGlobal]) {
      renderForm(container, window[profileGlobal], opts);
    }

    // 2) Re-render whenever the profile event fires
    window.addEventListener(eventName, function (ev) {
      var profile = ev.detail && ev.detail.profile;
      if (!profile) return;
      renderForm(container, profile, opts);
    });
  }

  // -------------------------------------------------------------------
  // Auto-init all [data-pane="generator-form"] containers on DOM ready.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="generator-form"]');
    if (!containers.length) return;

    // Support older browsers that don't have NodeList.forEach
    Array.prototype.forEach.call(containers, initOne);
  });
})();
