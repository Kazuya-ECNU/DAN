/**
 * DAN Web Server
 *
 * POST /api/run  → 写入临时目录，启动 SSE 流
 * GET  /api/stream/:id → SSE 事件流
 *
 * 文件名推断规则（简单启发式）：
 *   PARAM: 以 "y =" / "y=" / "f(" 开头 → func.md
 *          以 "def " / "class " / "import " 开头 → demo.py
 *          其余 → content
 *   LOSS:  以 "def " / "class " / "import " 开头 → indicator.py
 *          首行匹配 "x,y" 或 "-5.0" 数字模式 → scatter.csv
 *          其余 → target.md
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

const runs = new Map();

// ── 文件名推断 ────────────────────────────────────────────────────────────────
function firstLine(text) {
  return (text || '').trim().split('\n')[0];
}

function inferParamFile(text) {
  const line = firstLine(text);
  if (/^(def |class |import |from |#!)/.test(line)) return 'demo.py';
  if (/^(y\s*=|f\()/.test(line)) return 'func.md';
  return 'content';
}

function inferLossFile(text) {
  const line = firstLine(text);
  if (/^(def |class |import |from )/.test(line)) return 'indicator.py';
  if (/^x,y$|^[\d-]/.test(line)) return 'scatter.csv';
  return 'target.md';
}

// ── 写入临时目录 ─────────────────────────────────────────────────────────────
function writeTaskFiles(tmpDir, { meta, heuristic, param, loss }) {
  const dirs = {
    META:      path.join(tmpDir, 'META'),
    HEURISTIC: path.join(tmpDir, 'HEURISTIC'),
    PARAM:     path.join(tmpDir, 'PARAM'),
    LOSS:      path.join(tmpDir, 'LOSS'),
  };
  for (const d of Object.values(dirs)) fs.mkdirSync(d, { recursive: true });

  if (meta)       fs.writeFileSync(path.join(dirs.META,      'task.json'),   meta);
  if (heuristic)  fs.writeFileSync(path.join(dirs.HEURISTIC, 'rules.md'),  heuristic);
  if (param)      fs.writeFileSync(path.join(dirs.PARAM,     inferParamFile(param)), param);
  if (loss)       fs.writeFileSync(path.join(dirs.LOSS,      inferLossFile(loss)),  loss);
}

// ── SSE ──────────────────────────────────────────────────────────────────────
function send(res, event) {
  res.write(`data:${JSON.stringify(event)}\n\n`);
}

// ── 路由 ────────────────────────────────────────────────────────────────────

app.get('/api/presets', (_req, res) => {
  res.json([
    { id: '02_loss3',        name: '02_CodeOptimize — 代码质量优化' },
    { id: '01_loss1',        name: '02_CodeOptimize — 低耦合高内聚' },
    { id: '01_LinearFunFit', name: '01_LinearFunFit — 数值拟合' },
  ]);
});

app.get('/api/preset/:id', (req, res) => {
  const map = {
    '02_loss3':        '02_CodeOptimize/02_loss3',
    '01_loss1':        '02_CodeOptimize/01_loss1',
    '01_LinearFunFit': '01_LinearFunFit',
  };
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
      if (e.isDirectory()) r[e.name] = readDir(full);
      else try { r[e.name] = fs.readFileSync(full, 'utf-8'); } catch (_) {}
    }
    return r;
  }

  res.json({
    META:      readDir(path.join(taskDir, 'META')),
    HEURISTIC: readDir(path.join(taskDir, 'HEURISTIC')),
    PARAM:     readDir(path.join(taskDir, 'PARAM')),
    LOSS:      readDir(path.join(taskDir, 'LOSS')),
  });
});

app.post('/api/run', (req, res) => {
  const { meta, heuristic, param, loss } = req.body;
  const runId = String(Date.now()) + Math.random().toString(36).slice(2);
  const tmpDir = path.join(__dirname, '../tmp_' + runId);
  const DAN_ROOT = path.join(__dirname, '../..');

  try {
    writeTaskFiles(tmpDir, { meta, heuristic, param, loss });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }

  runs.set(runId, { tmpDir, meta, heuristic, param, loss });
  res.json({ runId });
});

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

  // ── 回显四元组 ─────────────────────────────────────────────────────────────
  send(res, { type: 'section', text: '📥 已接收的四元组内容' });
  send(res, { type: 'echo_banner', text: 'META ─────────────────────────────────────' });
  for (const line of (meta || '(空)').split('\n').slice(0, 30)) {
    if (line.trim()) send(res, { type: 'echo', label: 'META', text: line });
  }

  send(res, { type: 'echo_banner', text: 'HEURISTIC ─────────────────────────────────' });
  for (const line of (heuristic || '(空)').split('\n').slice(0, 30)) {
    if (line.trim()) send(res, { type: 'echo', label: 'HEURISTIC', text: line });
  }

  send(res, { type: 'echo_banner', text: 'PARAM ──────────────────────────────────────' });
  for (const line of (param || '(空)').split('\n').slice(0, 50)) {
    if (line.trim()) send(res, { type: 'echo', label: 'PARAM', text: line });
  }

  send(res, { type: 'echo_banner', text: 'LOSS ────────────────────────────────────────' });
  for (const line of (loss || '(空)').split('\n').slice(0, 50)) {
    if (line.trim()) send(res, { type: 'echo', label: 'LOSS', text: line });
  }

  send(res, { type: 'section', text: '🚀 开始执行 DAN 优化循环' });

  // ── dan.show ───────────────────────────────────────────────────────────────
  const show = spawn('python3', ['-m', 'dan.show', tmpDir], {
    cwd: DAN_ROOT,
    env: { ...process.env, PYTHONPATH: DAN_ROOT }
  });

  show.stdout.on('data', d => {
    if (!stopped) {
      for (const line of d.toString().split('\n')) {
        if (line.trim()) send(res, { type: 'show', text: line.trimEnd() });
      }
    }
  });
  show.stderr.on('data', d => { if (!stopped) send(res, { type: 'error', text: d.toString() }); });

  show.on('close', code => {
    if (stopped) return;
    if (code !== 0) send(res, { type: 'error', text: `dan.show 退出码 ${code}` });

    // ── dan --json ───────────────────────────────────────────────────────────
    const proc = spawn('python3', ['-m', 'dan', tmpDir, '--json'], {
      cwd: DAN_ROOT,
      env: { ...process.env, PYTHONPATH: DAN_ROOT }
    });

    proc.stdout.on('data', d => {
      if (stopped) return;
      for (const raw of d.toString().split('\n')) {
        const l = raw.trim();
        if (!l) continue;
        try { send(res, JSON.parse(l)); }
        catch { send(res, { type: 'log', text: l }); }
      }
    });
    proc.stderr.on('data', d => { if (!stopped) send(res, { type: 'error', text: d.toString() }); });

    proc.on('close', code => {
      if (!stopped) { send(res, { type: 'done', code }); res.end(); }
      cleanup();
    });
    proc.on('error', err => {
      if (!stopped) { send(res, { type: 'error', text: err.message }); res.end(); }
      cleanup();
    });
  });

  show.on('error', err => {
    if (!stopped) { send(res, { type: 'error', text: err.message }); res.end(); }
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
