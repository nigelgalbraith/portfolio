// js/GeneratorPreviewPane.js
//
// ===============================================
//  GENERATOR PREVIEW PANE — HOW TO USE
// ===============================================
//
// This pane handles everything on the generator page for:
//   • Showing the generated letter
//   • Calling Ollama (LLM) or template mode to generate text
//   • Copying the result to clipboard
//   • Opening a print-ready HTML page for PDF export
//
// It expects a profile object (usually in window.LETTER_PROFILE)
// with shape:
//
//   {
//     form: { ... },            // form values (optional)
//     options: [ ... ],         // checklist groups (optional)
//     styles: [ ... ],          // style labels (optional)
//     mode: "template" | "llm",
//     template: "Dear {{applicant}} ...",
//     prompt: "Write a letter using these fields: {{applicant}} ...",
//     ollama: {
//       model: "phi3",
//       options: { temperature: 0.3 }
//     }
//   }
//
// The context passed into template/prompt is built from:
//   • GeneratorFormPane inputs (via data-key)
//   • GeneratorChecklistPane checkboxes (via data-group + data-label)
//
// -----------------------------------------------
// 1) Add to HTML:
//
//   <div
//     data-pane="generator-preview"
//     data-ollama-url="http://localhost:11434/api/generate"
//     data-form-selector='[data-pane="generator-form"]'
//     data-checklists-selector='[data-pane="generator-checklists"]'
//     data-profile-global="LETTER_PROFILE"
//     data-letter-id="generator-letter"
//     data-title="Preview"
//     data-generate-label="Generate"
//     data-copy-label="Copy"
//     data-pdf-label="Open PDF preview"
//
//     data-ticker-id="profile-main"
//     data-ticker-generating="Generating your letter…"
//     data-ticker-complete="Letter ready to review."
//     data-ticker-error="Couldn’t generate letter — check Ollama."
//     data-ticker-busy="Already generating — please wait."
//   ></div>
//
//
// -----------------------------------------------
// 2) Modes:
//
//   mode === "llm"
//     - Uses profile.prompt + profile.ollama.model/options
//     - Prompt is rendered with {{var}} placeholders via renderTemplate
//     - Calls Ollama streaming API (POST /api/generate)
//
//   mode === "template" (or anything else)
//     - Uses profile.template as a Mustache-like template
//     - Replaces {{var}} using context from form + checklists
//
//
// -----------------------------------------------
// 3) data-* attributes:
//
//   data-ollama-url
//       URL for Ollama /api/generate endpoint.
//       Default: 'http://localhost:11434/api/generate'
//
//   data-form-selector
//       CSS selector for the generator form pane container.
//       The pane reads all input/textarea/select elements with data-key.
//       Default: '[data-pane="generator-form"]'
//
//   data-checklists-selector
//       CSS selector for generator checklist pane container.
//       The pane reads checkboxes with [data-group][data-label].
//       Default: '[data-pane="generator-checklists"]'
//
//   data-profile-global
//       Global variable where the profile is stored.
//       Default: 'LETTER_PROFILE'
//
//   data-letter-id
//       ID assigned to the preview element. Used by TTS (GeneratorPiperPane).
//       Default: 'generator-letter'
//
//   data-title
//       Pane title text. Default: 'Preview'
//
//   data-generate-label
//       Label for the "Generate" button. Default: 'Generate'
//
//   data-copy-label
//       Label for the "Copy" button. Default: 'Copy'
//
//   data-pdf-label
//       Label for the "Open PDF preview" button.
//       Default: 'Open PDF preview'
//
//   data-ticker-id              (optional)
//       ID of the StatusTickerPane to send temporary messages to.
//
//   data-ticker-generating      (optional)
//       Message sent to ticker when generation starts.
//       Default: 'Generating letter...'
//
//   data-ticker-complete        (optional)
//       Message sent to ticker when generation completes.
//       Default: 'Letter ready.'
//
//   data-ticker-error           (optional)
//       Message sent to ticker when generation fails.
//       Default: 'Generation failed.'
//
//   data-ticker-busy            (optional)
//       Message sent to ticker when user clicks Generate while busy.
//       Default: 'Already generating…'
//
//
// -----------------------------------------------
// 4) Buttons:
//
//   [Generate]
//       - Builds context from form + checklists
//       - Picks LLM or template based on profile.mode
//       - Streams from Ollama or renders template
//       - Fills the preview div (#generator-letter)
//       - Sends temporary messages to ticker (if configured)
//
//   [Copy]
//       - Copies preview textContent to clipboard
//
//   [Open PDF preview]
//       - Opens a print-friendly HTML page
//       - Calls window.print() in the new window
//
// ===============================================
//  IMPLEMENTATION
// ===============================================

(function () {
  var GENERATE_DOT_INTERVAL = 350;
  var FLASH_AUTOHIDE_MS = 1500;

  var DEFAULT_OLLAMA_API_URL = 'http://localhost:11434/api/generate';

  // Simple {{var}} matcher for template + prompt rendering
  var MUSTACHE = /\{\{\s*(\w+)\s*\}\}/g;

  // -------------------------------------------------------------------
  // Helper: ping the status ticker (StatusTickerPane.js)
  // -------------------------------------------------------------------
  function notifyTicker(tickerId, text, ms, color) {
    if (!tickerId || !text) return;
    var ev = new CustomEvent('ticker:temporary', {
      detail: {
        tickerId: tickerId,
        text: text,
        ms: ms,
        color: color
      }
    });
    window.dispatchEvent(ev);
  }

  // -------------------------------------------------------------------
  // Render a mustache-style template string using a context object.
  //   e.g. "Hello {{name}}" with { name: "Nigel" } → "Hello Nigel"
  // -------------------------------------------------------------------
  function renderTemplate(str, ctx) {
    return String(str || '').replace(MUSTACHE, function (_, k) {
      return (k in ctx ? String(ctx[k]) : '');
    });
  }

  // -------------------------------------------------------------------
  // Call Ollama's /api/generate streaming endpoint.
  //
  // params: {
  //   model:   string (required)
  //   options: { ... }  (optional)
  //   prompt:  string (required)
  //   vars:    object of substitutions for prompt template
  //   apiUrl:  string (optional, default DEFAULT_OLLAMA_API_URL)
  // }
  //
  // The prompt itself is first rendered via renderTemplate(prompt, vars).
  // -------------------------------------------------------------------
  async function generateWithOllama(params) {
    var model   = params.model;
    var options = params.options || { temperature: 0.3 };
    var prompt  = params.prompt;
    var vars    = params.vars || {};
    var apiUrl  = params.apiUrl || DEFAULT_OLLAMA_API_URL;

    if (!model || !prompt) throw new Error('Ollama: missing model or prompt');

    // Insert form/checklist values into the prompt
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

    // Stream chunks and concatenate obj.response fields
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
        } catch (e) {
          // ignore malformed lines
        }
      });
    }
    /* eslint-enable no-constant-condition */

    return out.trim();
  }

  // -------------------------------------------------------------------
  // Build a print-friendly HTML document for the letter text.
  // Used in the "Open PDF preview" button.
  // -------------------------------------------------------------------
  function buildPrintHTML(text) {
    function esc(s) {
      return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    // Escape HTML *then* turn real newlines into <br>
    var body = esc(text).replace(/\r?\n/g, '<br>');

    return (
      '<!doctype html>' +
      '<html>' +
      '<head>' +
      '  <meta charset="utf-8">' +
      '  <title>Letter – PDF Preview</title>' +
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
      '    .letter {' +
      '      max-width: 800px;' +
      '      margin: 0 auto;' +
      '    }' +
      '  </style>' +
      '</head>' +
      '<body>' +
      '  <div class="letter">' + body + '</div>' +
      '  <script>' +
      '    window.onload = function () {' +
      '      setTimeout(function () { window.print(); }, 250);' +
      '    };' +
      '  <\\/script>' +
      '</body>' +
      '</html>'
    );
  }

  // -------------------------------------------------------------------
  // Build context from:
  //   • GeneratorFormPane inputs (data-key)
  //   • GeneratorChecklistPane checkboxes (data-group, data-label)
  //
  // Returns an object, e.g.:
  //   {
  //     applicant: "Jane Doe",
  //     role: "Support Analyst",
  //     core_skills: "Leadership, Communication",
  //     options_json: "{ ... }"
  //   }
  //
  // core_skills/other slugs are derived from group.slug in generator-checklists.
  // -------------------------------------------------------------------
  function buildCtx(formSelector, checklistsSelector) {
    var ctx = {};

    // ---------- Form inputs (keyed by data-key) ----------
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

    // ---------- Checklist options ----------
    var optionsMap = {};

    if (checklistsSelector) {
      var optionsContainer = document.querySelector(checklistsSelector);
      if (optionsContainer) {
        var boxes = optionsContainer.querySelectorAll(
          'input[type="checkbox"][data-group][data-label]'
        );
        boxes = Array.prototype.slice.call(boxes);

        // Group checked labels by slug (data-group)
        var grouped = {};
        boxes.forEach(function (cb) {
          var g = cb.dataset.group;
          var label = cb.dataset.label || '';
          if (!grouped[g]) grouped[g] = [];
          if (cb.checked) grouped[g].push(label);
        });

        // Convert each group to a comma-separated string
        Object.keys(grouped).forEach(function (slug) {
          var joined = grouped[slug].join(', ');
          ctx[slug] = joined;
          optionsMap[slug] = joined;
        });
      }
    }

    // Extra JSON representation of the selected options
    ctx.options_json = JSON.stringify(optionsMap);

    return ctx;
  }

  // -------------------------------------------------------------------
  // High-level helper: generate the letter text based on profile mode.
  //
  // - Reads profile from window[profileGlobalName]
  // - Builds context from form + checklists
  // - If mode === 'llm', use Ollama
  // - Else fall back to template rendering
  // -------------------------------------------------------------------
  async function generateLetter(profileGlobalName, apiUrl, formSelector, checklistsSelector) {
    var profile = window[profileGlobalName] || {};
    var ctx = buildCtx(formSelector, checklistsSelector);

    var mode = profile.mode === 'llm' ? 'llm' : 'template';

    // LLM mode: use profile.prompt + profile.ollama
    if (mode === 'llm' && profile.prompt && profile.ollama && profile.ollama.model) {
      var txt = await generateWithOllama({
        model: profile.ollama.model,
        options: profile.ollama.options || { temperature: 0.3 },
        prompt: profile.prompt,
        vars: ctx,
        apiUrl: apiUrl
      });
      return txt;
    }

    // Template mode: render profile.template with context
    if (typeof profile.template === 'string' && profile.template.trim()) {
      return renderTemplate(profile.template, ctx);
    }

    // Fallback: nothing
    return '';
  }

  // -------------------------------------------------------------------
  // Initialize a single preview pane (buttons + preview box).
  // -------------------------------------------------------------------
  function initOne(container) {
    var ds = container.dataset || {};

    // Optional: link to a status ticker pane
    var tickerId = ds.tickerId || null;

    // Optional ticker messages (configurable via HTML)
    var tickerMsgGenerating = ds.tickerGenerating || 'Generating letter...';
    var tickerMsgComplete   = ds.tickerComplete   || 'Letter ready.';
    var tickerMsgError      = ds.tickerError      || 'Generation failed.';
    var tickerMsgBusy       = ds.tickerBusy       || 'Already generating…';

    // Dynamic config via data-*
    var apiUrl            = ds.ollamaUrl || ds.ollamaApi || DEFAULT_OLLAMA_API_URL;
    var formSelector      = ds.formSelector || '[data-pane="generator-form"]';
    var checklistsSelector= ds.checklistsSelector || '[data-pane="generator-checklists"]';
    var profileGlobalName = ds.profileGlobal || 'LETTER_PROFILE';
    var letterId          = ds.letterId || 'generator-letter';

    var titleText         = ds.title || 'Preview';
    var generateLabel     = ds.generateLabel || 'Generate';
    var copyLabel         = ds.copyLabel || 'Copy';
    var pdfLabel          = ds.pdfLabel || 'Open PDF preview';

    // Reset container
    container.innerHTML = '';

    // Pane wrapper
    var section = document.createElement('section');
    section.className = 'pane';

    // Title
    var h2 = document.createElement('h2');
    h2.className = 'pane-title';
    h2.textContent = titleText;

    // Top button row
    var actions = document.createElement('div');
    actions.className = 'actions';

    var btnGen = document.createElement('button');
    btnGen.className = 'primary';
    btnGen.textContent = generateLabel;

    var btnCopy = document.createElement('button');
    btnCopy.textContent = copyLabel;

    var btnPdf = document.createElement('button');
    btnPdf.textContent = pdfLabel;

    actions.appendChild(btnGen);
    actions.appendChild(btnCopy);
    actions.appendChild(btnPdf);

    // Status / flash area
    var flashDiv = document.createElement('div');
    flashDiv.id = 'preview-flash';

    // The letter preview itself
    var letter = document.createElement('div');
    letter.className = 'letter';
    letter.contentEditable = 'true';
    letter.id = letterId; // so Piper or others can target it

    section.appendChild(h2);
    section.appendChild(actions);
    section.appendChild(flashDiv);
    section.appendChild(letter);
    container.appendChild(section);

    var isGenerating = false;

    // Simple flash helper with auto-hide
    function flash(msg) {
      flashDiv.textContent = msg || '';
      flashDiv.classList.add('show');
      setTimeout(function () {
        flashDiv.classList.remove('show');
      }, FLASH_AUTOHIDE_MS);
    }

    // -------------------------------------------------------------
    // Generate button: build ctx, call generateLetter, update preview
    // -------------------------------------------------------------
    btnGen.addEventListener('click', function () {
      if (isGenerating) {
        flash(tickerMsgBusy);
        notifyTicker(tickerId, tickerMsgBusy, 2000, '#f97316'); // orange-ish
        return;
      }
      isGenerating = true;

      // Tell ticker we're starting generation
      notifyTicker(tickerId, tickerMsgGenerating, 4000, 'var(--accent)');

      // Animated "Generating..." dots
      var dots = 0;
      flash('Generating');
      var timer = setInterval(function () {
        dots = (dots + 1) % 4;
        flash('Generating' + '.'.repeat(dots));
      }, GENERATE_DOT_INTERVAL);

      generateLetter(profileGlobalName, apiUrl, formSelector, checklistsSelector)
        .then(function (txt) {
          letter.textContent = txt || '';
          clearInterval(timer);
          flash('Generation complete');
          notifyTicker(tickerId, tickerMsgComplete, 3000, 'var(--accent)');
        })
        .catch(function () {
          clearInterval(timer);
          flash('Error during generation');
          notifyTicker(tickerId, tickerMsgError, 3500, '#f87171');
        })
        .finally(function () {
          isGenerating = false;
        });
    });

    // -------------------------------------------------------------
    // Copy button: copy preview text to clipboard
    // -------------------------------------------------------------
    btnCopy.addEventListener('click', function () {
      var txt = letter.textContent || '';
      if (!txt) {
        flash('Nothing to copy');
        return;
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt)
          .then(function () {
            flash('Copied');
          })
          .catch(function () {
            flash('Clipboard error');
          });
      } else {
        flash('Clipboard not available');
      }
    });

    // -------------------------------------------------------------
    // PDF button: open print-friendly HTML in new window
    // -------------------------------------------------------------
    btnPdf.addEventListener('click', function () {
      var txt = letter.textContent || '';
      var html = buildPrintHTML(txt);
      var blob = new Blob([html], { type: 'text/html' });
      var url = URL.createObjectURL(blob);

      var w = window.open(url, '_blank');
      if (!w) {
        flash('Popup blocked — allow popups');
      }
    });
  }

  // -------------------------------------------------------------------
  // Auto-init all [data-pane="generator-preview"] panes on DOM ready.
  // -------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    var containers = document.querySelectorAll('[data-pane="generator-preview"]');
    Array.prototype.forEach.call(containers, initOne);
  });
})();
