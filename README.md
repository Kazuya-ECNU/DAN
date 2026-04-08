# DAN — Deep Agent Network

> A generalized end-to-end learning framework without gradients, powered by LLM agents.

---

## Core Abstraction: META + HEURISTIC + PARAM + LOSS

Mirrors the structure of deep learning, but generalizes every component:

| Component | DL Equivalent | Nature |
|-----------|--------------|--------|
| **META** | Hyperparameters | Task-agnostic config controlling optimization dynamics |
| **HEURISTIC** | Priors / Architecture | Structural assumption — shapes the search space |
| **PARAM** | Weights W | Generalized optimizable entity (code, coefficients, configs...) |
| **LOSS** | Loss Function | Quantifiable objective |

**DAN = Deep Learning without gradients.**

---

## Quick Start

### For LLM agents (recommended):

```bash
# 1. View task context
python -m dan.show demo/02_CodeOptimize/02_loss3

# 2. Run optimization loop
python -m dan demo/02_CodeOptimize/02_loss3
```

### Directory structure per task:

```
demo/XX/
├── META/task.yaml         # Task config (name, max_iterations, stop_if)
├── HEURISTIC/rules.md     # Search strategy (human-readable or Python)
├── PARAM/                 # Optimizable entity (code, config, equations...)
└── LOSS/                  # Evaluation (indicator.py, CSV, or text)
```

---

## CLI Tools

| Command | Purpose |
|---------|---------|
| `python -m dan.show <task_dir>` | Display full task context (META/HEURISTIC/PARAM/LOSS) |
| `python -m dan <task_dir>` | Run automated optimization loop |

---

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full framework specification
- [ARCHITECTURE_ZH.md](ARCHITECTURE_ZH.md) — 框架形式化定义（中文）

## Task Instances

| Task | META | HEURISTIC | PARAM | LOSS |
|------|------|-----------|-------|------|
| [01_LinearFunFit](demo/01_LinearFunFit/) | max_evals=5, stop_if | Manual tuning, ≤5 rounds | `y=ax+b`, `y=ax²+bx+c` | Scatter MSE |
| [02_CodeOptimize/01_loss1](demo/02_CodeOptimize/01_loss1/) | max_evals=10 | High cohesion, low coupling | Python code | Human eval |
| [02_CodeOptimize/02_loss3](demo/02_CodeOptimize/02_loss3/) | max_evals=10 | Minimize complexity metrics | Python code | Cyclomatic, Halstead, MI |
