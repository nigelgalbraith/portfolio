// js/Generator/GeneratorPreviewPane.js
//
// Generator preview pane (scoped).
// - Generates text (template mode or Ollama LLM mode)
// - Reads profile from Panes scoped state (api.state.get)
// - Reacts to PanesCore state events: state:changed:<stateKey>
// - Sends ticker messages via Panes scoped events

(function () {
  'use strict';

  var GENERATE_DOT_INTERVAL = 350;
  var FLASH_AUTOHIDE_MS = 1500;

  var DEFAULT_OLLAMA_API_URL = 'http://localhost:11434/api/generate';

  var MUSTACHE = /\{\{\s*(\w+)\s*\}\}/g;

  function notifyTicker(tickerId, text, ms, color, api) {
    if (!tickerId || !text) return;
    if (!api || !api.events || !api.events.emit) return;

    api.events.emit('ticker:temporary', {
      tickerId: tickerId,
      text: text,
      ms: ms,
      color: color
    });
  }

  function renderTemplate(str, ctx) {
    return String(str || '').replace(MUSTACHE, function (_, k) {
      return (k in ctx ? String(ctx[k]) : '');
    });
  }

  async function generateWithOllama(params) {
    var model = params.model;
    var options = params.options || { temperature: 0.3 };
    var prompt = params.prompt;
    var vars = params.vars || {};
    var apiUrl = params.apiUrl || DEFAULT_OLLAMA_API_URL;

    if (!model || !prompt) throw new Error('Ollama: missing model or prompt');

    var renderedPrompt = renderTemplate(prompt, vars);

    var body = {
      model: model,
      prompt: renderedPrompt,
      options: options,
      stream: true
    };

    var resp = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (!resp.ok) {
      var text = '';
      try { text = await resp.text(); } catch (e) {}
      throw new Error('Ollama HTTP ' + resp.status + ': ' + text);
    }

    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var out = '';

    /* eslint-disable no-constant-condition */
    while (true) {
      var step = await reader.read();
      if (step.done) break;
      var chunk = decoder.decode(step.value, { stream: true });

      chunk.split('\n').forEach(function (line) {
        if (!line.trim()) return;
        try {
          var obj = JSON.parse(line);
          if (obj.response) out += obj.response;
        } catch (e) { /* ignore */ }
      });
    }
    /* eslint-enable no-constant-condition */

    return out.trim();
  }

  function buildPrintHTML(text) {
    function esc(s) {
      return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    var body = esc(text).replace(/\r?\n/g, '<br>');

    return (
      '<!doctype html>' +
      '<html>' +
      '<head>' +
      '  <meta charset="utf-8">' +
      '  <title>Text – PDF Preview</title>' +
      '  <style>' +
      '    @page { margin: 20mm; }' +
      '    :root {' +
      '      --text: #111;' +
      '      --font: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Arial, sans-serif;' +
      '    }' +
      '    body {' +
      '      background: #fff;' +
      '      color: var(--text);' +
      '      font-family: var(--font);' +
      '      line-height: 1.5;' +
      '      font-size: 12pt;' +
      '      margin: 0;' +
      '      padding: 20mm;' +
      '    }' +
      '    .text {' +
      '      max-width: 800px;' +
      '      margin: 0 auto;' +
      '    }' +
      '  </style>' +
      '</head>' +
      '<body>' +
      '  <div class="text">' + body + '</div>' +
      '  <script>' +
      '    window.onload = function () {' +
      '      setTimeout(function () { window.print(); }, 250);' +
      '    };' +
      '  <\\/script>' +
      '</body>' +
      '</html>'
    );
  }

  function buildCtx(formSelector, checklistsSelector, snippetsSelector) {
    var ctx = {};

    if (formSelector) {
      var formContainer = document.querySelector(formSelector);
      if (formContainer) {
        var inputs = formContainer.querySelectorAll('input, textarea, select');
        Array.prototype.forEach.call(inputs, function (inp) {
          var key = inp.dataset.key;
          if (!key) return;
          ctx[key] = inp.value || '';
        });
      }
    }

    var optionsMap = {};

    if (checklistsSelector) {
      var optionsContainer = document.querySelector(checklistsSelector);
      if (optionsContainer) {
        var boxes = optionsContainer.querySelectorAll(
          'input[type="checkbox"][data-group][data-label]'
        );

        var grouped = {};
        Array.prototype.forEach.call(boxes, function (cb) {
          var g = cb.dataset.group;
          var label = cb.dataset.label || '';
          if (!grouped[g]) grouped[g] = [];
          if (cb.checked) grouped[g].push(label);
        });

        Object.keys(grouped).forEach(function (slug) {
          var joined = grouped[slug].join(', ');
          ctx[slug] = joined;
          optionsMap[slug] = joined;
        });
      }
    }

    ctx.options_json = JSON.stringify(optionsMap);

    // Snippets blocks (subject + example) selected for inclusion
    if (snippetsSelector) {
      var snippetsContainer = document.querySelector(snippetsSelector);
      if (snippetsContainer) {
        var cards = snippetsContainer.querySelectorAll('.snippet-card');
        var chosen = [];

        Array.prototype.forEach.call(cards, function (card) {
          var cb = card.querySelector('input[type="checkbox"][data-role="snippet-selected"][data-subject]');
          if (!cb || !cb.checked) return;

          var subj = cb.dataset.subject || '';
          var ta = card.querySelector('textarea[data-role="snippet-text"][data-subject]');
          var text = ta ? (ta.value || '') : '';

          subj = String(subj).trim();
          text = String(text).trim();
          if (!subj && !text) return;

          chosen.push({ subject: subj, text: text });
        });

        // Human-friendly text block for prompts/templates
        // (Your prompt/template can reference {{snippets}})
        ctx.snippets = chosen
          .map(function (s) {
            if (s.subject && s.text) return s.subject + ': ' + s.text;
            return (s.subject || s.text);
          })
          .join('\n');

        // Machine-friendly JSON for advanced prompts
        ctx.snippets_json = JSON.stringify(chosen);
      }
    }
    return ctx;
  }

  async function generateText(stateKey, apiUrl, formSelector, checklistsSelector, snippetsSelector, api) {
    var profile = api.state.get(stateKey) || {};
    var ctx = buildCtx(formSelector, checklistsSelector, snippetsSelector);

    var mode = profile.mode === 'llm' ? 'llm' : 'template';

    if (mode === 'llm' && profile.prompt && profile.ollama && profile.ollama.model) {
      return await generateWithOllama({
        model: profile.ollama.model,
        options: profile.ollama.options || { temperature: 0.3 },
        prompt: profile.prompt,
        vars: ctx,
        apiUrl: apiUrl
      });
    }

    if (typeof profile.template === 'string' && profile.template.trim()) {
      return renderTemplate(profile.template, ctx);
    }

    return '';
  }

  function initOne(container, api) {
    if (!api || !api.state || !api.events) {
      throw new Error('GeneratorPreviewPane: missing Panes api');
    }

    var ds = container.dataset || {};

    var tickerId = ds.tickerId || null;

    var tickerMsgGenerating = ds.tickerGenerating || 'Generating text...';
    var tickerMsgComplete = ds.tickerComplete || 'Text ready.';
    var tickerMsgError = ds.tickerError || 'Generation failed.';
    var tickerMsgBusy = ds.tickerBusy || 'Already generating…';

    var apiUrl = ds.ollamaUrl || ds.ollamaApi || DEFAULT_OLLAMA_API_URL;
    var formSelector = ds.formSelector || '[data-pane="generator-form"]';
    var checklistsSelector = ds.checklistsSelector || '[data-pane="generator-checklists"]';
    var snippetsSelector = ds.snippetsSelector || '[data-pane="generator-snippets"]';

    // only source of truth now
    var stateKey = ds.stateKey || 'TEXT_PROFILE';

    var textId = ds.textId || 'generator-text';

    var titleText = ds.title || 'Preview';
    var generateLabel = ds.generateLabel || 'Generate';
    var copyLabel = ds.copyLabel || 'Copy';
    var pdfLabel = ds.pdfLabel || 'Open PDF preview';

    container.innerHTML = '';

    var section = document.createElement('section');
    section.className = 'pane pane--generator-preview';

    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnGen = document.createElement('button');
    btnGen.className = 'primary';
    btnGen.type = 'button';
    btnGen.textContent = generateLabel;

    var btnCopy = document.createElement('button');
    btnCopy.type = 'button';
    btnCopy.textContent = copyLabel;

    var btnPdf = document.createElement('button');
    btnPdf.type = 'button';
    btnPdf.textContent = pdfLabel;

    actions.appendChild(btnGen);
    actions.appendChild(btnCopy);
    actions.appendChild(btnPdf);

    var flashDiv = document.createElement('div');
    flashDiv.id = 'preview-flash';

    var text = document.createElement('div');
    text.className = 'text';
    text.contentEditable = 'true';
    text.id = textId;

    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    section.appendChild(text);
    container.appendChild(section);

    // --- enable/disable generate button depending on whether profile exists ---
    function setGenerateEnabled() {
      // either is fine; has() is a tiny bit cleaner than get()
      btnGen.disabled = !api.state.has(stateKey);
    }
    setGenerateEnabled();

    var offEnable = api.events.on('state:changed:' + stateKey, function () {
      setGenerateEnabled();
    });

    var isGenerating = false;
    var dotTimer = null;
    var hideTimer = null;

    // If the profile changes, nuke the preview so you don't see stale output.
    function clearPreviewOnProfileChange() {
      if (isGenerating) return; // don't wipe mid-flight
      text.textContent = '';
    }

    var offState = api.events.on('state:changed:' + stateKey, function () {
      clearPreviewOnProfileChange();
    });

    function flash(msg, autoHide) {
      flashDiv.textContent = msg || '';
      flashDiv.classList.add('show');

      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }

      if (autoHide !== false) {
        hideTimer = setTimeout(function () {
          flashDiv.classList.remove('show');
          hideTimer = null;
        }, FLASH_AUTOHIDE_MS);
      }
    }

    function startDots() {
      var dots = 0;
      flash('Generating', false);

      if (dotTimer) { clearInterval(dotTimer); dotTimer = null; }
      dotTimer = setInterval(function () {
        dots = (dots + 1) % 4;
        flash('Generating' + '.'.repeat(dots), false);
      }, GENERATE_DOT_INTERVAL);
    }

    function stopDots(finalMsg) {
      if (dotTimer) { clearInterval(dotTimer); dotTimer = null; }
      flash(finalMsg || '', true);
    }

    function onGenerateClick() {
      if (!api.state.has(stateKey)) {
        flash('Load a profile first', true);
        notifyTicker(tickerId, 'Load a profile first', 2000, '#f97316', api);
        return;
      }

      if (isGenerating) {
        flash(tickerMsgBusy, true);
        notifyTicker(tickerId, tickerMsgBusy, 2000, '#f97316', api);
        return;
      }
      isGenerating = true;

      notifyTicker(tickerId, tickerMsgGenerating, 4000, 'var(--accent)', api);
      startDots();

      generateText(stateKey, apiUrl, formSelector, checklistsSelector, snippetsSelector, api)
        .then(function (txt) {
          text.textContent = txt || '';
          stopDots('Generation complete');
          notifyTicker(tickerId, tickerMsgComplete, 3000, 'var(--accent)', api);
        })
        .catch(function () {
          stopDots('Error during generation');
          notifyTicker(tickerId, tickerMsgError, 3500, '#f87171', api);
        })
        .finally(function () {
          isGenerating = false;
        });
    }

    function onCopyClick() {
      var txt = text.textContent || '';
      if (!txt) {
        flash('Nothing to copy', true);
        return;
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt)
          .then(function () { flash('Copied', true); })
          .catch(function () { flash('Clipboard error', true); });
      } else {
        flash('Clipboard not available', true);
      }
    }

    function onPdfClick() {
      var txt = text.textContent || '';
      var html = buildPrintHTML(txt);
      var blob = new Blob([html], { type: 'text/html' });
      var url = URL.createObjectURL(blob);

      var w = window.open(url, '_blank');
      if (!w) {
        flash('Popup blocked — allow popups', true);
        URL.revokeObjectURL(url);
        return;
      }

      setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
    }

    btnGen.addEventListener('click', onGenerateClick);
    btnCopy.addEventListener('click', onCopyClick);
    btnPdf.addEventListener('click', onPdfClick);

    return {
      destroy: function () {
        try {
          if (dotTimer) clearInterval(dotTimer);
          if (hideTimer) clearTimeout(hideTimer);
        } catch (e) {}

        if (offState) offState();
        if (offEnable) offEnable();

        btnGen.removeEventListener('click', onGenerateClick);
        btnCopy.removeEventListener('click', onCopyClick);
        btnPdf.removeEventListener('click', onPdfClick);
      }
    };
  }

  if (!window.Panes || !window.Panes.register) {
    throw new Error('GeneratorPreviewPane requires PanesCore (Panes.register not found).');
  }

  window.Panes.register('generator-preview', function (container, api) {
    container.classList.add('pane-generator-preview');
    return initOne(container, api);
  });
})();