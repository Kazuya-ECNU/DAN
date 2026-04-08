/**
 * DAN Web — Frontend App
 */

(function () {
  'use strict';

  let es = null;

  // ── Elements ────────────────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  const presetSelect = $('presetSelect');
  const runBtn = $('runBtn');
  const stopBtn = $('stopBtn');
  const runStatus = $('runStatus');
  const outputBody = $('outputBody');
  const clearBtn = $('clearOutput');

  // Textareas
  const metaInput = $('metaInput');
  const heuristicInput = $('heuristicInput');
  const paramInput = $('paramInput');
  const lossInput = $('lossInput');

  // ── Tab Switching ───────────────────────────────────────────────────────────
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.card-body');
      card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      card.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      card.querySelector('#' + btn.dataset.tab).classList.add('active');
    });
  });

  // ── Preset Loader ───────────────────────────────────────────────────────────
  presetSelect.addEventListener('change', async () => {
    const id = presetSelect.value;
    if (!id) return;
    setStatus('加载预设...');
    try {
      const res = await fetch(`/api/preset/${id}`);
      if (!res.ok) throw new Error(await res.text());
      const task = await res.json();

      const firstOf = obj => { const v = Object.values(obj || {})[0]; return v != null ? v : ''; };

      metaInput.value = firstOf(task.META);
      heuristicInput.value = firstOf(task.HEURISTIC);
      paramInput.value = firstOf(task.PARAM);

      const lossNames = Object.keys(task.LOSS || {});
      const lossVals = Object.values(task.LOSS || {});
      if (lossVals[0] !== undefined) {
        lossInput.value = lossVals[0];
        if (lossNames[0]) {
          const pv = $('lossPreview');
          if (pv) { pv.style.display = 'flex'; pv.querySelector('.file-preview-name').textContent = lossNames[0]; }
        }
      }

      setStatus('已加载: ' + presetSelect.options[presetSelect.selectedIndex].text);
    } catch (err) {
      setStatus('加载失败: ' + err.message);
    }
  });

  // ── Drag & Drop ─────────────────────────────────────────────────────────────
  ['meta', 'heuristic', 'param', 'loss'].forEach(name => {
    const drop = $(name + 'Drop');
    const fileInput = $(name + 'FileInput');
    const textarea = $(name + 'Input');
    const preview = $(name + 'Preview');
    if (!drop || !fileInput || !textarea) return;

    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag-over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('drag-over'));
    drop.addEventListener('drop', e => {
      e.preventDefault();
      drop.classList.remove('drag-over');
      if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0], textarea, preview, name);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) loadFile(fileInput.files[0], textarea, preview, name);
    });
    preview?.querySelector('.file-preview-clear')?.addEventListener('click', () => {
      textarea.value = '';
      preview.style.display = 'none';
    });
  });

  function loadFile(file, textarea, preview, _name) {
    const reader = new FileReader();
    reader.onload = e => {
      textarea.value = e.target.result;
      if (preview) { preview.style.display = 'flex'; preview.querySelector('.file-preview-name').textContent = file.name; }
    };
    reader.readAsText(file);
  }

  // ── Run / Stop ─────────────────────────────────────────────────────────────
  runBtn.addEventListener('click', runOptimization);
  stopBtn.addEventListener('click', stopOptimization);
  clearBtn.addEventListener('click', clearOutput);

  async function runOptimization() {
    if (isRunning()) return;
    const meta = metaInput.value.trim();
    const heuristic = heuristicInput.value.trim();
    const param = paramInput.value.trim();
    const loss = lossInput.value.trim();
    if (!meta && !heuristic && !param && !loss) { setStatus('请至少填写一个组件'); return; }

    setRunning(true);
    clearOutput();

    try {
      // POST to create task
      const createRes = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meta, heuristic, param, loss }),
      });
      if (!createRes.ok) throw new Error((await createRes.json()).error || 'Server error');
      const { runId } = await createRes.json();

      // Connect SSE stream
      es = new EventSource(`/api/stream/${runId}`);
      es.onmessage = e => {
        const event = JSON.parse(e.data);
        handleEvent(event);
      };
      es.onerror = () => {
        appendLine('error', '❌ 连接中断');
        setRunning(false);
        es.close();
      };

    } catch (err) {
      appendLine('error', '❌ ' + err.message);
      setRunning(false);
    }
  }

  function stopOptimization() {
    if (es) { es.close(); es = null; }
    appendLine('warn', '⛔ 已手动停止');
    setRunning(false);
  }

  function isRunning() { return es !== null && es.readyState === EventSource.OPEN; }

  function setRunning(running) {
    runBtn.disabled = running;
    runBtn.style.display = running ? 'none' : 'inline-flex';
    stopBtn.style.display = running ? 'inline-flex' : 'none';
    setStatus(running ? '运行中...' : '');
  }

  function handleEvent(event) {
    switch (event.type) {
      case 'show':  appendLine('show', event.text.trimEnd()); break;
      case 'log':   appendLine('log-info', event.text.trimEnd()); break;
      case 'error': appendLine('error', event.text.trimEnd()); break;
      case 'done':
        appendLine('done', '✅ ' + event.text);
        setRunning(false);
        if (es) { es.close(); es = null; }
        break;
    }
  }

  function clearOutput() {
    outputBody.innerHTML = `<div class="output-placeholder">
      <svg class="placeholder-icon" viewBox="0 0 64 64" fill="none">
        <circle cx="32" cy="32" r="28" stroke="#E5E5EA" stroke-width="2"/>
        <path d="M20 32L28 40L44 24" stroke="#E5E5EA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <p>填写上方四元组，点击「运行优化」开始</p>
    </div>`;
  }

  function appendLine(type, text) {
    const placeholder = outputBody.querySelector('.output-placeholder');
    if (placeholder) placeholder.remove();

    const shouldScroll = outputBody.scrollHeight - outputBody.scrollTop - outputBody.clientHeight < 80;

    const div = document.createElement('div');
    div.className = `log-line log-${type}`;
    div.textContent = text;
    outputBody.appendChild(div);

    if (shouldScroll) outputBody.scrollTop = outputBody.scrollHeight;
  }

  function setStatus(msg) { runStatus.textContent = msg; }

})();
