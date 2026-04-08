# DAN Web Interface

> Browser-based UI for the META + HEURISTIC + PARAM + LOSS optimization framework.

## Quick Start

```bash
cd web
npm install
npm start
```

Then open **http://localhost:3847**

## Features

- **Four input panels** for META, HEURISTIC, PARAM, LOSS — each with text editor and file upload
- **Preset loader** — load existing demos (LinearFunFit, CodeOptimize) with one click
- **Live log streaming** — see agent output in real-time via Server-Sent Events
- **Apple-style design** — Inter font, frosted glass header, subtle shadows, dark terminal output

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/presets` | GET | List available demo presets |
| `/api/preset/:id` | GET | Get full task content for a preset |
| `/api/run` | POST | Start optimization, returns `{runId}` |
| `/api/stream/:runId` | GET | SSE stream of log output |
