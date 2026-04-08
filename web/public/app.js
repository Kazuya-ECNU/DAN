/**
 * DAN Web — Frontend App
 * Handles SSE events from dan --json output
 */

(function () {
  'use strict';

  let es = null;

  const $ = id => document.getElementById(id);
  const presetSelect = $('presetSelect');
  const runBtn = $('runBtn');
  const stopBtn = $('stopBtn');
  const runStatus = $('runStatus');
  const outputBody = $('outputBody');
  const clearBtn = $('clearOutput');

  const metaInput = $('metaInput');
  const heuristicInput = $('heuristicInput');
  const paramInput = $('paramInput');
  const lossInput = $('lossInput');

  // ── Tab Switching ────────────────────────────────────────────────────────────
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

      const lossVals = Object.values(task.LOSS || {});
      const lossNames = Object.keys(task.LOSS || {});
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
      if (preview) preview.style.display = 'none';
    });
  });

  function loadFile(file, textarea, preview) {
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
    if (es) return;
    const meta = metaInput.value.trim();
    const heuristic = heuristicInput.value.trim();
    const param = paramInput.value.trim();
    const loss = lossInput.value.trim();
    if (!meta && !heuristic && !param && !loss) { setStatus('请至少填写一个组件'); return; }

    setRunning(true);
    clearOutput();

    try {
      const createRes = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meta, heuristic, param, loss }),
      });
      if (!createRes.ok) throw new Error((await createRes.json()).error || 'Server error ' + createRes.status);
      const { runId } = await createRes.json();

      es = new EventSource(`/api/stream/${runId}`);
      es.onmessage = e => {
        try {
          const event = JSON.parse(e.data);
          handleEvent(event);
        } catch (err) {
          appendLine('error', '❌ JSON解析失败: ' + e.data);
        }
      };
      es.onerror = () => {
        appendLine('error', '❌ SSE连接中断');
        setRunning(false);
        es.close();
        es = null;
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

  // ── Event Handlers ──────────────────────────────────────────────────────────
  function handleEvent(event) {
    switch (event.type) {
      case 'banner':
        appendLine('header', `⚡ ${event.name}`);
        break;

      case 'meta':
        appendLine('section', '📋 META — ' + (event.description || '').slice(0, 80));
        break;

      case 'loss_desc':
        appendLine('section', '🎯 LOSS — ' + (event.text || '').slice(0, 100));
        break;

      case 'heuristic':
        if (event.text) {
          appendLine('section', '🧠 HEURISTIC');
          for (const line of event.text.split('\n').slice(0, 10)) {
            if (line.trim()) appendLine('show', '   ' + line.trim());
          }
        } else if (event.note === 'human_in_the_loop') {
          appendLine('warn', '🧠 HEURISTIC: 人机协同模式，请参考上方规则手动调整PARAM');
        }
        break;

      case 'iteration_start':
        appendLine('section', `▓▓ Iteration ${event.iteration} ` + '▓'.repeat(30));
        break;

      case 'loss':
        if (event.metrics) {
          const entries = Object.entries(event.metrics);
          appendLine('metric', '  📊 指标:');
          for (const [k, v] of entries) {
            const label = { loc: '代码行数', avg_cc: '平均圈复杂度', avg_func_loc: '平均函数行数',
              dup_rate: '重复代码率', halstead_diff: 'Halstead难度', mi: '可维护性指数',
              mse_eq1: '方程1 MSE', mse_eq2: '方程2 MSE' }[k] || k;
            appendLine('metric', `     ${label}: ${typeof v === 'number' ? v.toFixed(2) : v}`);
          }
        }
        break;

      case 'param_update':
        if (event.files && event.files.length > 0) {
          appendLine('log', `  ⚙️  PARAM更新: ${event.files.join(', ')}`);
        } else {
          appendLine('log', '  ⚙️  PARAM: 无更新');
        }
        break;

      case 'stop':
        appendLine('done', `✅ 收敛停止: ${event.reason}`);
        setRunning(false);
        if (es) { es.close(); es = null; }
        break;

      case 'done':
        appendLine('done', `✅ 执行完成 — ${event.reason} (共${event.iterations}次迭代)`);
        setRunning(false);
        if (es) { es.close(); es = null; }
        break;

      case 'error':
        appendLine('error', '❌ ' + (event.text || event.message || ''));
        break;

      default:
        if (event.text) appendLine('log', String(event.text));
    }
  }

  // ── Output Helpers ──────────────────────────────────────────────────────────
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

    const atBottom = outputBody.scrollHeight - outputBody.scrollTop - outputBody.clientHeight < 80;

    const div = document.createElement('div');
    div.className = `log-line log-${type}`;
    div.textContent = text;
    outputBody.appendChild(div);

    if (atBottom) outputBody.scrollTop = outputBody.scrollHeight;
  }

  function setStatus(msg) { runStatus.textContent = msg; }

})();
