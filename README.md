# DAN — Deep Agent Network

> A closed-loop optimization framework powered by LLM agents.

## Core Abstraction: META + HEURISTIC + PARAM + LOSS

```
PARAM ──(adjust)──→ LOSS ──(feedback)──→ HEURISTIC ──(decide)──→ PARAM
                          ↑
                          META
```

Every task is a **4-tuple**: `(META, HEURISTIC, PARAM₀, LOSS)`

| Component | Role | What it does |
|-----------|------|-------------|
| **META** | Goal definition | Defines *what* the task is |
| **HEURISTIC** | Search strategy | Defines *how* to search/adjust PARAM |
| **PARAM** | Optimization subject | The entity being tuned |
| **LOSS** | Feedback signal | Quantifies distance to META |

The loop runs iteratively — gradient-free, agent-native, fully interpretable.

## Documentation | 文档

- [ARCHITECTURE.md](ARCHITECTURE.md) — Framework specification (English)
- [ARCHITECTURE_ZH.md](ARCHITECTURE_ZH.md) — 框架形式化定义（中文）

## Task Instances | 任务示例

| Path | Task | PARAM | LOSS |
|------|------|-------|------|
| `demo/01_LinearFunFit/` | Numerical coefficient fitting | `y = ax + b`, `y = ax² + bx + c` | Scatter fitting error |
| `demo/02_CodeOptimize/` | Code quality optimization | Python source code | Cyclomatic complexity, Halstead, MI |

## Quick Start

```bash
# Copy a task template
cp -r demo/02_CodeOptimize demo/03_YourTask

# Edit the four components
#   META/HEURISTIC/PARAM/LOSS
```

See `ARCHITECTURE.md` for full specification.
