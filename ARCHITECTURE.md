# DAN — Deep Agent Network

> A closed-loop optimization framework powered by LLM agents.

---

## 1. Framework Philosophy | 框架哲学

DAN defines all optimization tasks as a **four-element closed-loop system**:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   PARAM  ──(adjust)──→  LOSS  ──(feedback)──→           │
│     ↑                                    HEURISTIC      │
│     │                                         │         │
│     └──(decision)────────────────────────────┘         │
│                         ↑                               │
│                       META                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

The loop runs iteratively until convergence criteria are met, **without relying on gradient-based methods**.

---

## 2. Four Core Components | 四元核心组件

| Component | Role | Description |
|-----------|------|-------------|
| **META** | Goal definition | Target description, evaluation context, task background |
| **HEURISTIC** | Search strategy | Rules governing how PARAM is adjusted, when to stop, how to evaluate progress |
| **PARAM** | Optimization subject | The entity being tuned — code, numerical coefficients, model weights, etc. |
| **LOSS** | Feedback signal | Quantitative metric(s) measuring distance from META |

### 2.1 META

Defines **what** the task is. Typically a natural language description stored in `loss/target.md` or similar metadata files.

```
loss/
└── target.md          # Task goal description
    └── target/         # (optional) Structured data assets (e.g., scatter.csv)
```

### 2.2 HEURISTIC

Defines **how** to search. Stored in `heuristic/rule.md` — a set of constraints and strategies the agent must follow. Heuristics are **task-specific** and **non-transferable**.

```
heuristic/
└── rule.md            # Search rules & constraints
```

### 2.3 PARAM

The **optimization target** — the "payload" that gets modified on each iteration.

```
param/
└── xxx                # Could be .py code, .md equations, .json config, etc.
```

### 2.4 LOSS

The **objective function** — produces feedback signals that drive HEURISTIC decisions.

```
loss/
├── indicator.py       # Evaluation script / metrics computation
└── target.md          # Goal description
```

---

## 3. Closed-Loop Workflow | 闭环工作流

```
┌────────────────────────────────────────────────────────┐
│                      Iteration Loop                     │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. READ META          Read task goal & constraints    │
│          ↓                                               │
│  2. READ PARAM         Load current parameter state    │
│          ↓                                               │
│  3. CALCULATE LOSS     Run indicator to get feedback   │
│          ↓                                               │
│  4. APPLY HEURISTIC    Decide what to adjust & how     │
│          ↓                                               │
│  5. UPDATE PARAM       Apply modifications              │
│          ↓                                               │
│  6. CHECK STOP CRITERIA  → if not done, back to step 3 │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 4. Task Instances | 任务实例

### 4.1 01_LinearFunFit — Numerical Coefficient Fitting

```
demo/01_LinearFunFit/
├── META/loss/target/my_scatter.csv    # Scatter data points
├── HEURISTIC/heuristic/rule.md       # "Manual tuning, ≤5 evaluations"
├── PARAM/param/func.md                # y = ax + b ; y = ax² + bx + c
└── LOSS/ (scatter comparison)          # Loss = sum((y_pred - y_actual)²)
```

### 4.2 02_CodeOptimize — Code Quality Optimization

```
demo/02_CodeOptimize/
├── META/loss/target.md               # "Minimize all metrics"
├── HEURISTIC/heuristic/rule.md       # "No auto-scripts, ≤1000 LOC delta"
├── PARAM/param/demo.py               # Source code to optimize
└── LOSS/loss/indicator.py            # Cyclomatic complexity, Halstead, MI...
```

---

## 5. Why This Structure? | 为什么是这个结构？

| Property | Benefit |
|----------|---------|
| **Gradient-free** | Works for non-differentiable targets (code, discrete structures) |
| **Agent-native** | Each component maps directly to LLM capabilities (read/write/reason) |
| **Reproducible** | Every task is self-contained in its `demo/{name}/` folder |
| **Composable** | New tasks inherit the same structure — only PARAM & LOSS change |
| **Interpretable** | HEURISTIC is explicit human knowledge, not hidden in prompt engineering |

---

## 6. Creating a New Task | 新建任务

```bash
cp -r demo/02_CodeOptimize demo/03_YourTask
# Then edit:
#   - META:      demo/03_YourTask/loss/target.md
#   - HEURISTIC: demo/03_YourTask/heuristic/rule.md
#   - PARAM:     demo/03_YourTask/param/your_param
#   - LOSS:      demo/03_YourTask/loss/indicator.py (if applicable)
```

The agent will follow the same read→evaluate→adjust loop without any framework changes.

---

## 7. Formal Specification | 形式化定义

A DAN task is a 4-tuple:

```
Task := (META, HEURISTIC, PARAM₀, LOSS)

Where:
  META      : Human-readable goal description
  HEURISTIC : Set of constraints + search rules
  PARAM₀    : Initial parameter state
  LOSS      : Function → ℝⁿ  (n-dimensional feedback vector)

Iteration i:
  PARAMᵢ₊₁ = HEURISTIC(PARAMᵢ, LOSS(PARAMᵢ))
  Stop if:  LOSS(PARAMᵢ₊₁) satisfies META criteria
            OR iteration limit reached
```

---

*Built for LLM agents to perform structured, interpretable, non-gradient optimization.*
