# DAN — Deep Agent Network

> A generalized end-to-end learning framework, without gradients.

## Core Abstraction: META + HEURISTIC + PARAM + LOSS

DAN mirrors the structure of deep learning, but generalizes every component:

```
PARAM ──(adjust)──→ LOSS ──(feedback)──→ HEURISTIC ──(decide)──→ PARAM
                          ↑
                         META
```

| Component | DL Equivalent | Nature |
|-----------|--------------|--------|
| **META** | Hyperparameters | Task-agnostic config controlling optimization dynamics |
| **HEURISTIC** | Priors / Architecture | Structural assumption — shapes the search space |
| **PARAM** | Weights W | Generalized optimizable entity (code, coefficients, configs...) |
| **LOSS** | Loss Function | Quantifiable objective |

**DAN is to Deep Learning what gradient-free optimization is to gradient-based learning** — same conceptual loop, no gradients required.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Framework specification (English)
- [ARCHITECTURE_ZH.md](ARCHITECTURE_ZH.md) — 框架形式化定义（中文）

## Task Instances

| Path | Task | META | HEURISTIC | PARAM | LOSS |
|------|------|------|-----------|-------|------|
| `demo/01_LinearFunFit/` | Numerical fitting | max_evals=5, manual | "human-in-loop tuning, no cross-reference" | `a, b, c` coefficients | Scatter MSE |
| `demo/02_CodeOptimize/` | Code quality opt | max_loc=1000, no auto-scripts | "minimize complexity, prefer encapsulation" | Python source code | Cyclomatic complexity, Halstead, MI |

## Quick Start

```bash
cp -r demo/02_CodeOptimize demo/03_YourTask
# Edit: META / HEURISTIC / PARAM / LOSS
```

See `ARCHITECTURE.md` for full specification.
