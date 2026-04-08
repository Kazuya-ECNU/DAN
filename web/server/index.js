/**
 * DAN Web Server — Split SSE design
 * POST /api/run → creates temp task, returns {runId}
 * GET  /api/stream/:runId → SSE stream
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
const runs = new Map();

app.get('/api/presets', (req, res) => {
  res.json([
    { id: '02_loss3', name: '02_CodeOptimize — 代码质量优化' },
    { id: '01_loss1', name: '02_CodeOptimize — 低耦合高内聚' },
    { id: '01_LinearFunFit', name: '01_LinearFunFit — 数值拟合' },
  ]);
});

app.get('/api/preset/:id', (req, res) => {
  const presetMap = { '02_loss3': '02_CodeOptimize/02_loss3', '01_loss1': '02_CodeOptimize/01_loss1', '01_LinearFunFit': '01_LinearFunFit' };
  const subPath = presetMap[req.params.id];
  if (!subPath) return res.status(404).json({ error: 'Preset not found' });

  const taskDir = path.join(__dirname, '../../demo', subPath);
  if (!fs.existsSync(taskDir)) return res.status(404).json({ error: 'Task dir not found' });

  function readDir(dir) {
    const result = {};
    if (!fs.existsSync(dir)) return result;
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name.startsWith('.')) continue;
      const full = path.join(dir, e.name);
      if (e.isDirectory()) result[e.name] = readDir(full);
      else try { result[e.name] = fs.readFileSync(full, 'utf-8'); } catch (_) {}
    }
    return result;
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

  // Write task files
  try {
    const mDir = path.join(tmpDir, 'META');    fs.mkdirSync(mDir, { recursive: true });
    const hDir = path.join(tmpDir, 'HEURISTIC'); fs.mkdirSync(hDir, { recursive: true });
    const pDir = path.join(tmpDir, 'PARAM');   fs.mkdirSync(pDir, { recursive: true });
    const lDir = path.join(tmpDir, 'LOSS');    fs.mkdirSync(lDir, { recursive: true });

    if (meta)        fs.writeFileSync(path.join(mDir, 'task.yaml'), meta);
    if (heuristic)   fs.writeFileSync(path.join(hDir, 'rules.md'), heuristic);
    if (param)       fs.writeFileSync(path.join(pDir, 'content'), param);
    if (loss) {
      if (loss.trimStart().startsWith('def ') || loss.trimStart().startsWith('import ')) {
        fs.writeFileSync(path.join(lDir, 'indicator.py'), loss);
      } else if (/^\d[\d,.\s-]+[,]\s*[\d]/.test(loss.trim())) {
        fs.writeFileSync(path.join(lDir, 'data.csv'), loss);
      } else {
        fs.writeFileSync(path.join(lDir, 'target.md'), loss);
      }
    }
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }

  runs.set(runId, { tmpDir, status: 'running' });
  res.json({ runId });
});

// ── GET /api/stream/:runId ──────────────────────────────────────────────────
app.get('/api/stream/:runId', (req, res) => {
  const run = runs.get(req.params.runId);
  if (!run) return res.status(404).json({ error: 'Run not found' });

  const { tmpDir } = run;
  const DAN_ROOT = path.join(__dirname, '../..');
  let stopped = false;

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  res.flushHeaders();

  const send = (type, text) => {
    if (!stopped) {
      res.write(`data:${JSON.stringify({ type, text })}\n\n`);
    }
  };

  const cleanup = () => {
    stopped = true;
    runs.delete(req.params.runId);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
  };

  req.on('close', cleanup);

  // Run: python3 -m dan.show <tmpDir>
  const show = spawn('python3', ['-m', 'dan.show', tmpDir], { cwd: DAN_ROOT, env: { ...process.env, PYTHONPATH: DAN_ROOT } });

  show.stdout.on('data', d => send('show', d.toString()));
  show.stderr.on('data', d => send('error', d.toString()));

  show.on('close', code => {
    if (stopped) return;
    if (code !== 0) send('error', `dan.show exited ${code}`);

    // Run: python3 -m dan <tmpDir> --quiet
    const runner = spawn('python3', ['-m', 'dan', tmpDir, '--quiet'], { cwd: DAN_ROOT, env: { ...process.env, PYTHONPATH: DAN_ROOT } });

    runner.stdout.on('data', d => {
      if (stopped) return;
      for (const l of d.toString().split('\n')) {
        if (l.trim()) send('log', l.trimEnd());
      }
    });
    runner.stderr.on('data', d => send('error', d.toString()));

    runner.on('close', code => {
      if (stopped) return;
      send('done', `执行完成，退出码: ${code}`);
      res.end();
      cleanup();
    });
    runner.on('error', err => { send('error', err.message); res.end(); cleanup(); });
  });

  show.on('error', err => { send('error', err.message); res.end(); cleanup(); });
});

app.listen(PORT, '0.0.0.0', () => {
  const interfaces = Object.values(require('os').networkInterfaces())
    .flat()
    .filter(i => i.family === 'IPv4' && !i.internal)
    .map(i => i.address);
  console.log(`DAN Web → http://localhost:${PORT}`);
  if (interfaces.length) console.log(`         → http://${interfaces[0]}:${PORT}`);
});
