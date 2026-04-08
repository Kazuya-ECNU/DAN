# DAN — Deep Agent Network Architecture

> Framework version 0.1 | For LLM agents performing generalized end-to-end optimization.

---

## 1. Conceptual Analogy: DAN ≋ Deep Learning

| DAN Component | DL Equivalent | Role |
|--------------|--------------|------|
| **META** | Hyperparameters | Task-agnostic config controlling optimization dynamics |
| **HEURISTIC** | Priors / Architecture | Structural assumption — shapes the search space |
| **PARAM** | Weights W | Generalized optimizable entity (code, coefficients, configs...) |
| **LOSS** | Loss Function | Quantifiable objective |

**DAN = Deep Learning without gradients.**

---

## 2. Project Structure

```
DAN/
├── dan/                           # Framework package
│   ├── __init__.py               # Public API: META, HEURISTIC, PARAM, LOSS, Runner
│   ├── __main__.py               # CLI: python -m dan <task_dir>
│   ├── show.py                   # Show task context: python -m dan.show <task_dir>
│   ├── core.py                   # Component abstractions + evaluators
│   └── runner.py                 # Main optimization loop
│
├── demo/                         # Task instances
│   ├── 01_LinearFunFit/
│   │   ├── META/task.json        # max_iterations, stop_if, output_dir
│   │   ├── HEURISTIC/rules.md    # Human-readable search strategy
│   │   ├── PARAM/func.md         # Equations to fit: y=ax+b, y=ax²+bx+c
│   │   ├── LOSS/scatter.csv      # Target data
│   │   └── results/              # Output (existing results preserved)
│   │
│   └── 02_CodeOptimize/
│       ├── 01_loss1/
│       │   ├── META/task.json
│       │   ├── HEURISTIC/rules.md
│       │   ├── PARAM/demo.py
│       │   └── results/
│       └── 02_loss3/
│           ├── META/task.json
│           ├── HEURISTIC/rules.md
│           ├── PARAM/demo.py     # E-commerce order system (to optimize)
│           ├── LOSS/
│           │   ├── indicator.py  # Metrics: cyclomatic complexity, Halstead, MI
│           │   └── target.md
│           └── results/          # Output
│
├── ARCHITECTURE.md               # This file
└── ARCHITECTURE_ZH.md           # 中文版
```

---

## 3. The Four Components

### 3.1 META — Task Configuration

```yaml
# demo/XX/META/task.json
name: CodeOptimize-02_loss3
description: >
  Optimize Python code quality metrics.
max_iterations: 10
output_dir: results
stop_if: "loss.mi >= 65"   # Optional: early stopping expression
```

Fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable task name |
| `description` | string | What the task is about |
| `max_iterations` | int | Hard stop after N iterations |
| `output_dir` | string | Where to write optimization trace |
| `stop_if` | string | Optional expression like `"loss.mi >= 65"` |

### 3.2 HEURISTIC — Search Strategy

Stored in `HEURISTIC/` directory. Supported formats (priority order):

| Format | File | Strategy | Use Case |
|--------|------|----------|----------|
| Python | `.py` | `decide(iteration, param_snapshot, loss_result) → {filename: new_content}` | Full programmability |
| YAML | `.json` | Declarative `if → then` rules | Structured strategies |
| Markdown | `.md` | Human-readable guidelines | Human-in-the-loop tasks |

```python
# HEURISTIC/decide.py (Python strategy example)
def decide(iteration, param_snapshot, loss_result):
    # iteration: current iteration number
    # param_snapshot: dict of {filename: content}
    # loss_result: dict of {metric_name: value}
    # Return: dict of {filename: new_content} to update PARAM
    code = param_snapshot["demo.py"]
    if loss_result.get("avg_cc", 0) > 5:
        code = code.replace("for p in product_db:", "for p in self.products:")
        return {"demo.py": code}
    return {}
```

### 3.3 PARAM — Optimization Target

Everything the agent is allowed to modify. Stored as plain files in `PARAM/`:

```
PARAM/
├── demo.py        # Code to optimize
├── config.json    # Configuration to tune
├── func.md        # Equations with tunable coefficients
└── ...
```

The framework loads all files in `PARAM/` as a `dict[str, str]` (filename → content).

### 3.4 LOSS — Feedback Signal

Stored in `LOSS/` directory. Supported evaluator types:

| Evaluator | Trigger | Output |
|-----------|---------|--------|
| `PythonLossEvaluator` | `LOSS/indicator.py` exists | Metrics dict via JSON stdout |
| `CSVLossEvaluator` | `LOSS/*.csv` exists | MSE against data points |
| `TextLossEvaluator` | `LOSS/*.md` exists | Human evaluation needed |
| `NoLossEvaluator` | No loss files | No automatic evaluation |

**PythonLossEvaluator contract:**
The `.py` script must accept a directory path as argument and print a JSON dict to stdout:
```bash
python3 LOSS/indicator.py /path/to/eval_param_dir
# Should print: {"loc": 259, "avg_cc": 2.9, "mi": 35.5, ...}
```

---

## 4. CLI Tools

### 4.1 Show Task Context (for LLM agents)

```bash
python -m dan.show demo/02_CodeOptimize/02_loss3
```

Reads META/HEURISTIC/PARAM/LOSS and prints a formatted summary — exactly what an LLM agent needs to understand the task in one shot.

### 4.2 Run Optimization

```bash
python -m dan demo/02_CodeOptimize/02_loss3 [--quiet] [--max-iter N]
```

Runs the full iteration loop (for fully automated tasks where HEURISTIC is a `.py` file).

---

## 5. How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Agent runs: python -m dan.show <task_dir>                  │
│                                                             │
│  → Reads META/task.json       → Understands goal + config  │
│  → Reads HEURISTIC/rules.md   → Understands how to search  │
│  → Reads PARAM/*              → Sees the thing to optimize  │
│  → Reads LOSS/*               → Understands how to measure  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Agent manually iterates:                                   │
│                                                             │
│  1. Read PARAM current state                                │
│  2. Run LOSS evaluation                                     │
│  3. Consult HEURISTIC rules                                 │
│  4. Apply modification to PARAM                              │
│  5. Check META stop_if condition                            │
│  6. Repeat until satisfied                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Write results/result.md and results/optimized.py          │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Adding a New Task

```bash
cp -r demo/02_CodeOptimize/02_loss3 demo/03_YourTask
```

Then edit the four components:

```
demo/03_YourTask/
├── META/task.json         ← Task name, max_iterations, stop_if
├── HEURISTIC/rules.md     ← Search strategy
├── PARAM/                 ← Your optimizable files
└── LOSS/                  ← Your evaluation logic
```

That's all. No framework code changes needed.

---

## 7. Formal Definition

```
DAN Task := (META, HEURISTIC, PARAM₀, LOSS)

Iteration i:
  param_snapshot = PARAM_i
  loss_result   = LOSS(PARAM_i)
  param_update  = HEURISTIC(PARAM_i, loss_result, META)
  PARAM_{i+1}   = apply(PARAM_i, param_update)
  stop if:      META.stop_if(loss_result) OR i >= META.max_iterations
```
