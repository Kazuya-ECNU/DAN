/**
 * DAN Web — Frontend App
 */

(function () {
  'use strict';

  // ── Elements ────────────────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  const metaInput        = $('meta-input');
  const heuristicInput   = $('heuristic-input');
  const paramInput       = $('param-input');
  const lossInput        = $('loss-input');
  const runBtn           = $('run-btn');
  const stopBtn          = $('stop-btn');
  const clearBtn         = $('clear-btn');
  const copyBtn          = $('copy-output');
  const outputBody       = $('output-body');
  const outputPlaceholder = $('output-placeholder');
  const runStatus        = $('run-status');

  let es = null;
  let taskId = null;

  // ── Char count ──────────────────────────────────────────────────────────────
  function updateCount(id, input) {
    const el = $(id);
    el.textContent = input.value.length.toLocaleString() + ' chars';
  }
  [
    ['meta-count',        metaInput],
    ['heuristic-count',   heuristicInput],
    ['param-count',       paramInput],
    ['loss-count',        lossInput],
  ].forEach(([id, input]) => {
    input.addEventListener('input', () => updateCount(id, input));
    updateCount(id, input);
  });

  // ── Output helpers ──────────────────────────────────────────────────────────
  function clearOutput() {
    outputBody.innerHTML = '';
    outputBody.scrollTop = 0;
  }

  function removePlaceholder() {
    const ph = outputBody.querySelector('.output-placeholder');
    if (ph) ph.remove();
  }

  function appendLine(type, text) {
    removePlaceholder();
    const atBottom = outputBody.scrollHeight - outputBody.scrollTop - outputBody.clientHeight < 60;

    const div = document.createElement('div');
    div.className = `log-line log-${type}`;
    div.textContent = text;
    outputBody.appendChild(div);

    if (atBottom) outputBody.scrollTop = outputBody.scrollHeight;
  }

  function appendPlaceholder() {
    if (!outputBody.querySelector('.output-placeholder')) {
      outputBody.innerHTML = '';
      outputBody.appendChild(Object.assign(
        document.createElement('div'), {
          className: 'output-placeholder',
          innerHTML: `<svg class="placeholder-icon" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="#636366" stroke-width="1.5"/>
            <path d="M20 32L28 40L44 24" stroke="#636366" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg><p>填写上方四元组，点击「运行优化」开始</p>`
        }
      ));
    }
  }

  // ── UI state ───────────────────────────────────────────────────────────────
  function setRunning(running) {
    runBtn.disabled = running;
    runBtn.style.display = running ? 'none' : 'inline-flex';
    stopBtn.style.display = running ? 'inline-flex' : 'none';
    setStatus(running ? '运行中...' : '');
  }

  function setStatus(msg) { runStatus.textContent = msg; }

  // ── SSE handler ────────────────────────────────────────────────────────────
  function handleEvent(event) {
    switch (event.type) {
      case 'echo_banner':
        appendLine('echo-banner', event.text);
        break;
      case 'echo':
        appendLine('echo', (event.label ? `[${event.label}] ` : '') + event.text);
        break;
      case 'section':
        appendLine('section', event.text);
        break;
      case 'header':
        appendLine('header', `⚡ ${event.name}`);
        break;
      case 'loss':
        if (event.metrics) {
          appendLine('metric', '  📊 指标:');
          for (const [k, v] of Object.entries(event.metrics)) {
            const label = {
              loc: '代码行数', avg_cc: '平均圈复杂度',
              avg_func_loc: '平均函数行数', dup_rate: '重复代码率',
              halstead_diff: 'Halstead难度', mi: '可维护性指数',
              mse_eq1: '方程1 MSE', mse_eq2: '方程2 MSE',
            }[k] || k;
            appendLine('metric', `     ${label}: ${typeof v === 'number' ? v.toFixed(2) : v}`);
          }
        }
        break;
      case 'param_update':
        if (event.files && event.files.length) {
          appendLine('log', `  ⚙️  PARAM 更新: ${event.files.join(', ')}`);
        }
        break;
      case 'log':
        appendLine('log', '  ' + event.text);
        break;
      case 'done':
        appendLine('done', `✅ 执行完成 — ${event.reason || ''} (${event.iterations}次迭代)`);
        setRunning(false);
        closeES();
        break;
      case 'error':
        appendLine('error', '❌ ' + event.text);
        setRunning(false);
        closeES();
        break;
      default:
        if (event.text) appendLine('log', event.text);
    }
  }

  function closeES() {
    if (es) { es.close(); es = null; }
  }

  // ── Run / Stop ─────────────────────────────────────────────────────────────
  runBtn.addEventListener('click', runOptimization);
  stopBtn.addEventListener('click', stopOptimization);
  clearBtn.addEventListener('click', () => {
    clearOutput();
    appendPlaceholder();
    setStatus('');
  });
  copyBtn.addEventListener('click', () => {
    const text = Array.from(outputBody.querySelectorAll('.log-line'))
      .map(el => el.textContent)
      .join('\n');
    navigator.clipboard.writeText(text).then(() => {
      const orig = copyBtn.textContent;
      copyBtn.textContent = '已复制';
      setTimeout(() => { copyBtn.textContent = orig; }, 1500);
    });
  });

  async function runOptimization() {
    if (es) return;

    const meta = metaInput.value.trim();
    const heuristic = heuristicInput.value.trim();
    const param = paramInput.value.trim();
    const loss = lossInput.value.trim();

    if (!meta && !heuristic && !param && !loss) {
      setStatus('请至少填写一个组件');
      return;
    }

    setRunning(true);
    clearOutput();

    try {
      // Step 1: Register task
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meta, heuristic, param, loss }),
      });
      if (!res.ok) throw new Error((await res.json()).error || `HTTP ${res.status}`);
      const { task_id } = await res.json();
      taskId = task_id;

      // Step 2: Connect SSE stream
      es = new EventSource(`/api/stream/${task_id}`);
      es.onmessage = e => {
        try {
          const event = JSON.parse(e.data);
          handleEvent(event);
        } catch {
          appendLine('error', '解析失败: ' + e.data);
        }
      };
      es.onerror = () => {
        appendLine('error', '❌ SSE 连接中断');
        setRunning(false);
        closeES();
      };

    } catch (err) {
      appendLine('error', '❌ ' + err.message);
      setRunning(false);
    }
  }

  function stopOptimization() {
    closeES();
    appendLine('warn', '⛔ 已手动停止');
    setRunning(false);
  }

})();
