// js/Generator/GeneratorFormPane.js
//
// Generator form pane (scoped).
// - Renders a "Details" form using the profile in Panes scoped state
// - Reacts to PanesCore state events: state:changed:<stateKey>
// - Does NOT write to state (generator inputs are consumed by PreviewPane)

(function () {
  'use strict';

  var DEFAULT_TEXTAREA_ROWS = 20;

  function toTitle(label) {
    return String(label || '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function parseStyles(raw) {
    if (!raw) return ['Professional', 'Friendly', 'Direct', 'Concise'];
    return String(raw)
      .split(',')
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  function buildSchema(profile) {
    profile = profile || {};

    if (Array.isArray(profile.formSchema) && profile.formSchema.length) {
      return profile.formSchema;
    }

    var form = profile.form || profile.profile || {};
    var keys = Object.keys(form);

    return keys.map(function (key) {
      var lower = String(key).toLowerCase();
      var type = 'text';

      if (lower.indexOf('desc') !== -1) type = 'textarea';
      else if (lower.indexOf('style') !== -1) type = 'select';

      return {
        key: key,
        label: toTitle(key),
        type: type,
        rows: DEFAULT_TEXTAREA_ROWS
      };
    });
  }

  function renderForm(container, profile, opts) {
    opts = opts || {};

    var titleText = opts.title || 'Details';
    var defaultStyles = opts.defaultStyles || ['Professional', 'Friendly', 'Direct', 'Concise'];

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--generator-form';

    var h2 = document.createElement('h2');
    h2.textContent = titleText;
    h2.className = 'pane-title';

    var wrap = document.createElement('div');

    var schema = buildSchema(profile);
    var formDefaults = (profile && (profile.form || profile.profile)) || {};
    var styles = Array.isArray(profile && profile.styles) ? profile.styles : defaultStyles;

    schema.forEach(function (field) {
      var key = field.key;
      var label = field.label;
      var type = field.type;
      var rows = field.rows || DEFAULT_TEXTAREA_ROWS;

      var group = document.createElement('div');
      group.className = 'group';

      var lab = document.createElement('label');
      lab.textContent = label;

      var input;

      if (type === 'textarea') {
        input = document.createElement('textarea');
        input.rows = rows;
      } else if (type === 'select') {
        input = document.createElement('select');
        styles.forEach(function (s) {
          var opt = document.createElement('option');
          opt.value = s;
          opt.textContent = s;
          input.appendChild(opt);
        });
      } else {
        input = document.createElement('input');
      }

      input.dataset.key = key;

      var initial = formDefaults[key];
      if (initial != null) input.value = String(initial);

      group.appendChild(lab);
      group.appendChild(input);
      wrap.appendChild(group);
    });

    section.appendChild(h2);
    section.appendChild(wrap);
    container.appendChild(section);
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('GeneratorFormPane: missing Panes api');
    }

    var ds = container.dataset || {};

    // Single source of truth now
    var stateKey = ds.stateKey || 'TEXT_PROFILE';

    var opts = {
      title: ds.title || 'Details',
      defaultStyles: parseStyles(ds.defaultStyles)
    };

    function renderFromState() {
      var profile = api.state.get(stateKey);
      if (!profile) return;
      renderForm(container, profile, opts);
    }

    // Initial render
    renderFromState();

    // React to state changes for this profile key
    var off = api.events.on('state:changed:' + stateKey, function () {
      renderFromState();
    });

    return {
      destroy: function () {
        if (off) off();
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('GeneratorFormPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('generator-form', function (container, api) {
    container.classList.add('pane-generator-form');
    return initOne(container, api);
  });
})();