# DAN — Deep Agent Network

> A generalized end-to-end learning framework, without gradients.

---

## Core Analogy: DAN ≋ Deep Learning

| DAN Component | Deep Learning Equivalent | Nature |
|--------------|------------------------|--------|
| **META** | Hyperparameters (lr, batch_size, optimizer...) | Task-agnostic framework config; controls optimization dynamics |
| **HEURISTIC** | Priors / Inductive Biases (CNN/RNN/Attention) | Structural assumption — "what shape of function to use" |
| **PARAM** | Weights W | Generalized optimizable entity — code, coefficients, configs, any adjustable data |
| **LOSS** | Loss Function | Quantifiable optimization objective |

The analogy runs deeper than metaphor:

```
Deep Learning:                    DAN (Generalized):
─────────────────────────────────────────────────────
HEURISTIC   ── architecture ──→  search space structure
META        ── hyperparams   ──→  optimization dynamics
PARAM       ── weights W     ──→  the thing being fitted
LOSS        ── loss          ──→  feedback signal
─────────────────────────────────────────────────────
Training loop:                   Same structure, no gradient
```

DAN is to Deep Learning what **gradient-free optimization** is to **gradient-based learning** — same conceptual loop, different mechanism for updating PARAM.

---

## 1. Four Core Components

### 1.1 META — Framework Configuration (≈ Hyperparameters)

Task-agnostic settings that control **how** optimization proceeds, independent of the specific task.

```
META = {
    "optimization_method": "manual",   # how to search the space
    "max_iterations": 5,              # stopping criterion
    "evaluation_metric": "multi_dim", # scalar or vector loss
    ...
}
```

Unlike HEURISTIC which shapes *what* the search space looks like, META shapes *how* the search behaves.

### 1.2 HEURISTIC — Structural Prior (≈ Architecture)

Defines the **inductive bias** — the structural assumption about what kind of solution space to search in. Just as CNNs encode spatial locality priors and RNNs encode sequential dependence priors, DAN HEURISTIC encodes task-specific structural knowledge.

```
HEURISTIC encodes:
- "Use class-based encapsulation" (prior: code should be object-oriented)
- "Manually tune coefficients" (prior: human-in-the-loop search)
- "Minimize cyclomatic complexity" (prior: simpler control flow is better)
```

### 1.3 PARAM — Optimization Target (≈ Weights W)

The **generalized parameter** — any adjustable entity that can be modified and re-evaluated. Unlike DL where PARAM is always a numeric tensor, here it can be:

```
PARAM ∈ { code, coefficients, config files, prompts, hyperparameters, ... }
```

### 1.4 LOSS — Objective Function (≈ Loss)

Quantifiable feedback signal that measures distance from META-defined goal. In gradient-based DL, LOSS drives gradient computation. In DAN, LOSS drives HEURISTIC-guided search.

```
LOSS: PARAM → ℝⁿ    (n-dimensional feedback vector)
```

---

## 2. Formal Definition

```
DAN Task := (META, HEURISTIC, PARAM₀, LOSS)

Where:
  META      : Framework config (task-agnostic)
  HEURISTIC : Structural prior (shapes the search space)
  PARAM₀    : Initial parameter state
  LOSS      : Param → ℝⁿ  (feedback signal)

Iteration i:
  feedback  = LOSS(PARAMᵢ)
  PARAMᵢ₊₁ = HEURISTIC(PARAMᵢ, feedback, META)
  Stop if:  convergence(PARAMᵢ, PARAMᵢ₊₁, META)
            OR iteration_limit(META) reached
```

---

## 3. Closed-Loop Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                      DAN Optimization Loop                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  META contains: max_iterations, stopping_criteria, etc.     │
│  HEURISTIC contains: search rules, priors, constraints      │
│                                                              │
│  1. READ HEURISTIC        Load structural prior & rules    │
│          ↓                                                     │
│  2. READ META             Load framework config            │
│          ↓                                                     │
│  3. READ PARAMᵢ           Load current parameter state    │
│          ↓                                                     │
│  4. COMPUTE LOSS(PARAMᵢ)  Evaluate feedback signal        │
│          ↓                                                     │
│  5. APPLY HEURISTIC       Decide adjustment strategy      │
│          ↓                                                     │
│  6. UPDATE PARAM           Modify PARAM → PARAMᵢ₊₁         │
│          ↓                                                     │
│  7. CHECK META criteria    → if not done, back to step 4    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Task Instances

### 4.1 01_LinearFunFit

```
META:
  max_evaluations: 5
  optimization_method: manual
HEURISTIC:
  - "Manually tune a, b, c coefficients"
  - "Do not reference other equation's result"
PARAM:  y = ax + b ; y = ax² + bx + c  (coefficients a, b, c)
LOSS:   Σ(y_pred - y_actual)²  (scatter fitting error)
```

### 4.2 02_CodeOptimize

```
META:
  max_loc_delta: 1000
  optimization_method: manual (no auto-scripts)
HEURISTIC:
  - "Minimize cyclomatic complexity"
  - "Reduce duplicate code"
  - "Prefer encapsulation over global state"
PARAM:  Python source code (e-commerce order system)
LOSS:   (cyclomatic_complexity, halstead_difficulty, mi, duplicate_rate)
```

---

## 5. Why This Abstraction?

| Property | DL Analogy | DAN Benefit |
|----------|-----------|-------------|
| **Gradient-free** | N/A | Works on non-differentiable PARAM (code, discrete structures) |
| **Interpretable priors** | Architecture design | HEURISTIC is explicit human knowledge, not buried in hyperparameters |
| **Generalized PARAM** | Weights W | Can optimize any file/data, not just numeric tensors |
| **Flexible LOSS** | Loss functions | Any quantifiable metric, single or multi-objective |

---

*Generalized end-to-end learning for LLM agents — same loop as training a neural network, but without gradients.*
