// js/Builder/BuilderSnippetsPane.js
//
// Builder snippets editor (scoped).
// - Edits an array of { subject, text, selected? } blocks.
// - Intended for reusable "example" style content.
// - Stores data in Panes scoped state under: state.snippets
// - Re-renders on state:changed:<stateKey>

(function () {
  'use strict';

  function ensureState(api, stateKey) {
    var s = api.state.get(stateKey);
    if (!s || typeof s !== 'object') {
      s = {
        form: {},
        styles: [],
        options: [],
        snippets: [],
        mode: 'template',
        template: '',
        prompt: '',
        ollama: null
      };
      api.state.set(stateKey, s);
    }
    if (!Array.isArray(s.snippets)) s.snippets = [];
    return s;
  }

  function syncFromDOM(rowsWrap, State, api, stateKey) {
    var rows = rowsWrap.querySelectorAll('.snippet-row');
    var out = [];

    Array.prototype.forEach.call(rows, function (row) {
      var subject = (row.querySelector('input[data-role="subject"]') || {}).value || '';
      var text = (row.querySelector('textarea[data-role="text"]') || {}).value || '';
      var selectedEl = row.querySelector('input[type="checkbox"][data-role="selected"]');
      var selected = selectedEl ? !!selectedEl.checked : false;

      subject = String(subject).trim();
      text = String(text).trim();

      // Ignore fully empty rows
      if (!subject && !text) return;

      out.push({ subject: subject, text: text, selected: selected });
    });

    State.snippets = out;
    api.state.set(stateKey, State);
  }

  function snippetRow(rowsWrap, State, api, stateKey, data, markLocalWrite) {
    data = data || {};

    var row = document.createElement('div');
    row.className = 'group snippet-row';

    // Subject + include toggle in one line
    var top = document.createElement('div');
    top.className = 'snippet-row-top';

    var subjectWrap = document.createElement('div');
    subjectWrap.className = 'snippet-subject-wrap';

    var subjectLab = document.createElement('label');
    subjectLab.textContent = 'Subject';

    var subject = document.createElement('input');
    subject.placeholder = 'What this relates to (e.g., Troubleshooting, Leadership)';
    subject.value = data.subject || '';
    subject.dataset.role = 'subject';

    subject.addEventListener('input', function () {
      markLocalWrite();
      syncFromDOM(rowsWrap, State, api, stateKey);
    });

    subjectWrap.appendChild(subjectLab);
    subjectWrap.appendChild(subject);

    var includeWrap = document.createElement('label');
    includeWrap.className = 'snippet-include';

    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.dataset.role = 'selected';
    cb.checked = data.selected !== false; // default true

    cb.addEventListener('change', function () {
      markLocalWrite();
      syncFromDOM(rowsWrap, State, api, stateKey);
    });

    var span = document.createElement('span');
    span.textContent = 'Default include';

    includeWrap.appendChild(cb);
    includeWrap.appendChild(span);

    top.appendChild(subjectWrap);
    top.appendChild(includeWrap);

    // Example text
    var textLab = document.createElement('label');
    textLab.textContent = 'Example text';

    var ta = document.createElement('textarea');
    ta.placeholder = 'Example of use (keep it reusable)';
    ta.rows = 5;
    ta.dataset.role = 'text';
    ta.value = data.text || '';

    ta.addEventListener('input', function () {
      markLocalWrite();
      syncFromDOM(rowsWrap, State, api, stateKey);
    });

    // Remove
    var btnRemove = document.createElement('button');
    btnRemove.type = 'button';
    btnRemove.className = 'mini danger';
    btnRemove.textContent = 'Remove';
    btnRemove.addEventListener('click', function () {
      row.remove();
      markLocalWrite();
      syncFromDOM(rowsWrap, State, api, stateKey);
    });

    row.appendChild(top);
    row.appendChild(textLab);
    row.appendChild(ta);
    row.appendChild(btnRemove);

    return row;
  }

  function render(container, api, stateKey, opts, markLocalWrite) {
    opts = opts || {};

    var titleText = opts.title || 'Snippets';
    var State = ensureState(api, stateKey);

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--builder-snippets';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    var help = document.createElement('p');
    help.className = 'muted';
    help.textContent = 'Reusable blocks + an example. You can choose which ones to include when generating.';

    var rowsWrap = document.createElement('div');
    rowsWrap.className = 'builder-snippets';

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnAdd = document.createElement('button');
    btnAdd.type = 'button';
    btnAdd.className = 'mini';
    btnAdd.textContent = '+ Add Snippet';

    btnAdd.addEventListener('click', function () {
      rowsWrap.appendChild(snippetRow(rowsWrap, State, api, stateKey, { selected: true }, markLocalWrite));
      markLocalWrite();
      syncFromDOM(rowsWrap, State, api, stateKey);
    });

    actions.appendChild(btnAdd);

    section.appendChild(h2);
    section.appendChild(help);
    section.appendChild(rowsWrap);
    section.appendChild(actions);
    container.appendChild(section);

    var existing = Array.isArray(State.snippets) ? State.snippets : [];
    if (existing.length) {
      existing.forEach(function (sn) {
        rowsWrap.appendChild(snippetRow(rowsWrap, State, api, stateKey, sn, markLocalWrite));
      });
    } else {
      // Start with one empty row
      rowsWrap.appendChild(snippetRow(rowsWrap, State, api, stateKey, { selected: true }, markLocalWrite));
    }
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('BuilderSnippetsPane: missing Panes api');
    }

    var ds = container.dataset || {};
    var stateKey = ds.stateKey || 'TEXT_PROFILE';

    var opts = {
      title: ds.title || 'Snippets'
    };

    // Prevent re-render loops when *this pane* writes state on input.
    var ignoreNext = false;
    function markLocalWrite() {
      ignoreNext = true;
      setTimeout(function () { ignoreNext = false; }, 0);
    }

    render(container, api, stateKey, opts, markLocalWrite);

    var off = api.events.on('state:changed:' + stateKey, function () {
      if (ignoreNext) return;
      render(container, api, stateKey, opts, markLocalWrite);
    });

    return {
      destroy: function () {
        if (off) off();
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('BuilderSnippetsPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('builder-snippets', function (container, api) {
    container.classList.add('pane-builder-snippets');
    return initOne(container, api);
  });
})();
