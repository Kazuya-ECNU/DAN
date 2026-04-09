/**
 * DAN Web Server
 *
 * POST /api/run     → creates temp task dir, stores original content in memory
 * GET  /api/stream/:runId → SSE stream
 *   1. Echoes the four components received from frontend (META, HEURISTIC, PARAM, LOSS)
 *   2. Runs dan --json and forwards structured events
 */

const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3847;

app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, '../public')));

// In-memory store for run metadata
// runId → { tmpDir, meta, heuristic, param, loss }
const runs = new Map();

// ── helpers ─────────────────────────────────────────────────────────────────

function inferParamFile(content) {
  if (!content) return 'content';
  const first = content.trimStart().split('\n')[0];
  if (/^(def |class |import |from |#.*python|^\#\!\/)/.test(first)) return 'demo.py';
  if (/^(1\.\s*y\s*=|^y\s*=|^f\()/.test(first)) return 'func.md';
  return 'content';
}

function inferLossFile(content) {
  if (!content) return 'target.md';
  const first = content.trimStart().split('\n')[0];
  if (/^(def |class |import |from )/.test(first)) return 'indicator.py';
  if (/^x,y$|^[\d-]/.test(first)) return 'scatter.csv';
  return 'target.md';
}

function writeTaskFiles(tmpDir, { meta, heuristic, param, loss }) {
  const mDir = path.join(tmpDir, 'META');     fs.mkdirSync(mDir, { recursive: true });
  const hDir = path.join(tmpDir, 'HEURISTIC'); fs.mkdirSync(hDir, { recursive: true });
  const pDir = path.join(tmpDir, 'PARAM');    fs.mkdirSync(pDir, { recursive: true });
  const lDir = path.join(tmpDir, 'LOSS');     fs.mkdirSync(lDir, { recursive: true });

  if (meta)       fs.writeFileSync(path.join(mDir, 'task.json'), meta);
  if (heuristic)  fs.writeFileSync(path.join(hDir, 'rules.md'), heuristic);
  if (param)      fs.writeFileSync(path.join(pDir, inferParamFile(param)), param);
  if (loss)       fs.writeFileSync(path.join(lDir, inferLossFile(loss)), loss);
}

function sendSSE(res, event) {
  res.write(`data:${JSON.stringify(event)}\n\n`);
}

function runDanSSE(tmpDir, DAN_ROOT, res, cleanup) {
  // Run: python3 -m dan <tmpDir> --json
  const proc = spawn('python3', ['-m', 'dan', tmpDir, '--json'], {
    cwd: DAN_ROOT,
    env: { ...process.env, PYTHONPATH: DAN_ROOT }
  });

  proc.stdout.on('data', d => {
    const lines = d.toString().split('\n');
    for (const raw of lines) {
      const l = raw.trim();
      if (!l) continue;
      try {
        sendSSE(res, JSON.parse(l));
      } catch {
        sendSSE(res, { type: 'log', text: l });
      }
    }
  });

  proc.stderr.on('data', d => sendSSE(res, { type: 'error', text: d.toString() }));

  proc.on('close', code => {
    sendSSE(res, { type: 'done', code });
    res.end();
    cleanup();
  });
  proc.on('error', err => {
    sendSSE(res, { type: 'error', text: err.message });
    res.end();
    cleanup();
  });
  return proc;
}

// ── routes ───────────────────────────────────────────────────────────────────

app.get('/api/presets', (_req, res) => {
  res.json([
    { id: '02_loss3', name: '02_CodeOptimize — 代码质量优化' },
    { id: '01_loss1', name: '02_CodeOptimize — 低耦合高内聚' },
    { id: '01_LinearFunFit', name: '01_LinearFunFit — 数值拟合' },
  ]);
});

app.get('/api/preset/:id', (req, res) => {
  const map = { '02_loss3': '02_CodeOptimize/02_loss3', '01_loss1': '02_CodeOptimize/01_loss1', '01_LinearFunFit': '01_LinearFunFit' };
  const sub = map[req.params.id];
  if (!sub) return res.status(404).json({ error: 'Preset not found' });

  const taskDir = path.join(__dirname, '../../demo', sub);
  if (!fs.existsSync(taskDir)) return res.status(404).json({ error: 'Task dir not found' });

  function readDir(dir) {
    const r = {};
    if (!fs.existsSync(dir)) return r;
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name.startsWith('.')) continue;
      const full = path.join(dir, e.name);
      if (e.isDirectory()) { r[e.name] = readDir(full); }
      else try { r[e.name] = fs.readFileSync(full, 'utf-8'); } catch (_) {}
    }
    return r;
  }

  res.json({
    META: readDir(path.join(taskDir, 'META')),
    HEURISTIC: readDir(path.join(taskDir, 'HEURISTIC')),
    PARAM: readDir(path.join(taskDir, 'PARAM')),
    LOSS: readDir(path.join(taskDir, 'LOSS')),
  });
});

// ── POST /api/run ────────────────────────────────────────────────────────────
app.post('/api/run', (req, res) => {
  const { meta, heuristic, param, loss } = req.body;
  const runId = String(Date.now()) + Math.random().toString(36).slice(2);
  const tmpDir = path.join(__dirname, `../tmp_${runId}`);
  const DAN_ROOT = path.join(__dirname, '../..');

  try {
    writeTaskFiles(tmpDir, { meta, heuristic, param, loss });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }

  // Store BOTH the tmpDir AND the original content for echo
  runs.set(runId, { tmpDir, meta, heuristic, param, loss });
  res.json({ runId });
});

// ── GET /api/stream/:runId ──────────────────────────────────────────────────
app.get('/api/stream/:runId', (req, res) => {
  const run = runs.get(req.params.runId);
  if (!run) return res.status(404).json({ error: 'Run not found' });

  const { tmpDir, meta, heuristic, param, loss } = run;
  const DAN_ROOT = path.join(__dirname, '../..');
  let stopped = false;

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  res.flushHeaders();

  const cleanup = () => {
    stopped = true;
    runs.delete(req.params.runId);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
  };

  req.on('close', cleanup);

  // ── STEP 0: Echo what the frontend sent (directly readable in log) ──────
  sendSSE(res, { type: 'section', text: '📥 已接收的四元组内容' });
  sendSSE(res, { type: 'echo_banner', text: '═'.repeat(50) });

  if (meta) {
    sendSSE(res, { type: 'echo_banner', text: '📋 META' });
    for (const line of meta.split('\n').slice(0, 30)) {
      if (line.trim()) sendSSE(res, { type: 'echo', label: 'META', text: line });
    }
    if (meta.split('\n').length > 30) sendSSE(res, { type: 'echo', label: 'META', text: '... (truncated)' });
  } else {
    sendSSE(res, { type: 'echo', label: 'META', text: '(empty)' });
  }

  if (heuristic) {
    sendSSE(res, { type: 'echo_banner', text: '🧠 HEURISTIC' });
    for (const line of heuristic.split('\n').slice(0, 30)) {
      if (line.trim()) sendSSE(res, { type: 'echo', label: 'HEURISTIC', text: line });
    }
    if (heuristic.split('\n').length > 30) sendSSE(res, { type: 'echo', label: 'HEURISTIC', text: '... (truncated)' });
  } else {
    sendSSE(res, { type: 'echo', label: 'HEURISTIC', text: '(empty)' });
  }

  if (param) {
    sendSSE(res, { type: 'echo_banner', text: '⚙️  PARAM' });
    for (const line of param.split('\n').slice(0, 40)) {
      if (line.trim()) sendSSE(res, { type: 'echo', label: 'PARAM', text: line });
    }
    if (param.split('\n').length > 40) sendSSE(res, { type: 'echo', label: 'PARAM', text: '... (truncated)' });
  } else {
    sendSSE(res, { type: 'echo', label: 'PARAM', text: '(empty)' });
  }

  if (loss) {
    sendSSE(res, { type: 'echo_banner', text: '🎯 LOSS' });
    for (const line of loss.split('\n').slice(0, 40)) {
      if (line.trim()) sendSSE(res, { type: 'echo', label: 'LOSS', text: line });
    }
    if (loss.split('\n').length > 40) sendSSE(res, { type: 'echo', label: 'LOSS', text: '... (truncated)' });
  } else {
    sendSSE(res, { type: 'echo', label: 'LOSS', text: '(empty)' });
  }

  sendSSE(res, { type: 'echo_banner', text: '═'.repeat(50) });
  sendSSE(res, { type: 'section', text: '🚀 开始执行 DAN 优化循环' });

  // ── STEP 1: dan.show ────────────────────────────────────────────────────
  const show = spawn('python3', ['-m', 'dan.show', tmpDir], { cwd: DAN_ROOT, env: { ...process.env, PYTHONPATH: DAN_ROOT } });

  show.stdout.on('data', d => {
    if (!stopped) {
      const lines = d.toString().split('\n');
      for (const l of lines) {
        if (l.trim()) sendSSE(res, { type: 'show', text: l.trimEnd() });
      }
    }
  });
  show.stderr.on('data', d => { if (!stopped) sendSSE(res, { type: 'error', text: d.toString() }); });

  show.on('close', code => {
    if (stopped) return;
    if (code !== 0) sendSSE(res, { type: 'error', text: `dan.show exited ${code}` });

    // ── STEP 2: dan runner (JSON Lines for SSE) ───────────────────────────
    const proc = spawn('python3', ['-m', 'dan', tmpDir, '--json'], {
      cwd: DAN_ROOT,
      env: { ...process.env, PYTHONPATH: DAN_ROOT }
    });

    proc.stdout.on('data', d => {
      if (stopped) return;
      for (const raw of d.toString().split('\n')) {
        const l = raw.trim();
        if (!l) continue;
        try {
          sendSSE(res, JSON.parse(l));
        } catch {
          sendSSE(res, { type: 'log', text: l });
        }
      }
    });
    proc.stderr.on('data', d => { if (!stopped) sendSSE(res, { type: 'error', text: d.toString() }); });

    proc.on('close', code => {
      if (!stopped) {
        sendSSE(res, { type: 'done', code });
        res.end();
      }
      cleanup();
    });
    proc.on('error', err => {
      if (!stopped) { sendSSE(res, { type: 'error', text: err.message }); res.end(); }
      cleanup();
    });
  });

  show.on('error', err => {
    if (!stopped) { sendSSE(res, { type: 'error', text: err.message }); res.end(); }
    cleanup();
  });
});

app.listen(PORT, '0.0.0.0', () => {
  const addrs = Object.values(require('os').networkInterfaces())
    .flat()
    .filter(i => i.family === 'IPv4' && !i.internal)
    .map(i => i.address);
  console.log(`DAN Web → http://localhost:${PORT}`);
  if (addrs.length) console.log(`         LAN  → http://${addrs[0]}:${PORT}`);
});
