# DAN — Deep Agent Network 架构文档

> 广义的端到端学习框架，无需梯度。

---

## 核心类比：DAN ≋ 深度学习

| DAN 组件 | 深度学习对应 | 本质 |
|---------|------------|------|
| **META** | 超参（lr, batch_size, optimizer...） | 框架级配置，与具体任务无关，控制优化动力学 |
| **HEURISTIC** | 先验/归纳偏置（CNN/RNN/Attention 结构） | 结构假设——"用什么形状的函数去拟合"的先验选择 |
| **PARAM** | 权重参数 W | 广义的被优化变量——代码、系数、配置、任意可调数据 |
| **LOSS** | Loss Function | 可衡量的优化目标 |

类比的内核：

```
深度学习:                     DAN（广义化）:
────────────────────────────────────────────────────────
HEURISTIC  ── 架构设计 ──→    搜索空间结构（先验选择）
META       ── 超参数   ──→    优化动力学配置
PARAM      ── 权重 W   ──→    被优化的广义参数
LOSS       ── 损失    ──→    反馈信号
────────────────────────────────────────────────────────
训练循环:                     结构相同，无梯度
```

DAN 是深度学习的**无梯度版本**——同样的概念循环，不同的 PARAM 更新机制。

---

## 1. 四元核心组件

### 1.1 META — 框架配置（≈ 超参数）

与具体任务无关的设置，控制**如何**进行优化。

```
META = {
    "optimization_method": "manual",   # 搜索方式
    "max_iterations": 5,              # 停止条件
    "evaluation_metric": "multi_dim", # 损失类型
    ...
}
```

META 决定搜索的**行为方式**（如何搜），HEURISTIC 决定搜索**空间的结构**（搜什么形状）。

### 1.2 HEURISTIC — 结构先验（≈ 归纳偏置）

定义**归纳偏置**——关于在什么形状的解空间中搜索的结构性假设。

正如 CNN 编码空间局部性先验、RNN 编码时序依赖先验，DAN HEURISTIC 编码任务相关的结构知识：

```
HEURISTIC 编码的先验例如：
- "使用类封装"（先验：代码应该是面向对象的）
- "手动调参"（先验：人参与搜索过程）
- "最小化圈复杂度"（先验：更简单的控制流更好）
```

### 1.3 PARAM — 优化目标（≈ 权重 W）

**广义的被优化参数**——任何可以被修改并重新评估的实体。深度学习中 PARAM 只能是数值张量，而这里可以是：

```
PARAM ∈ { 代码, 系数, 配置文件, prompt, 超参数设置, ... }
```

### 1.4 LOSS — 目标函数（≈ Loss）

可量化的反馈信号，衡量当前状态距离 META 定义目标的距离。深度学习中 LOSS 驱动梯度计算，DAN 中 LOSS 驱动 HEURISTIC 引导的搜索。

```
LOSS: PARAM → ℝⁿ    (n维反馈向量)
```

---

## 2. 形式化定义

```
DAN Task := (META, HEURISTIC, PARAM₀, LOSS)

其中:
  META      : 框架配置（任务无关）
  HEURISTIC : 结构先验（决定搜索空间形状）
  PARAM₀    : 初始参数状态
  LOSS      : Param → ℝⁿ  (反馈信号)

第 i 次迭代:
  feedback  = LOSS(PARAMᵢ)
  PARAMᵢ₊₁ = HEURISTIC(PARAMᵢ, feedback, META)
  终止条件:  convergence(PARAMᵢ, PARAMᵢ₊₁, META)
            OR iteration_limit(META) reached
```

---

## 3. 闭环工作流

```
┌──────────────────────────────────────────────────────────────┐
│                      DAN 优化循环                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  META 包含: max_iterations, stopping_criteria 等           │
│  HEURISTIC 包含: 搜索规则、先验知识、约束条件               │
│                                                              │
│  1. READ HEURISTIC        加载结构先验与规则                 │
│          ↓                                                     │
│  2. READ META             加载框架配置                       │
│          ↓                                                     │
│  3. READ PARAMᵢ           加载当前参数状态                 │
│          ↓                                                     │
│  4. COMPUTE LOSS(PARAMᵢ)  计算反馈信号                     │
│          ↓                                                     │
│  5. APPLY HEURISTIC       根据先验决定调整策略              │
│          ↓                                                     │
│  6. UPDATE PARAM           修改 PARAM → PARAMᵢ₊₁           │
│          ↓                                                     │
│  7. CHECK META criteria    → 若未完成，返回步骤 4           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. 任务实例

### 4.1 01_LinearFunFit — 数值系数拟合

```
META:
  max_evaluations: 5
  optimization_method: manual
HEURISTIC:
  - "手动调整 a, b, c 系数"
  - "计算第二个式子时不允许参考第一个式子的结果"
PARAM:  y = ax + b ; y = ax² + bx + c  (系数 a, b, c)
LOSS:   Σ(y_pred - y_actual)²  (散点拟合误差)
```

### 4.2 02_CodeOptimize — 代码质量优化

```
META:
  max_loc_delta: 1000
  optimization_method: manual（禁止自动化脚本）
HEURISTIC:
  - "最小化圈复杂度"
  - "减少重复代码"
  - "优先使用封装而非全局状态"
PARAM:  Python 源代码（电商订单系统）
LOSS:   (cyclomatic_complexity, halstead_difficulty, mi, duplicate_rate)
```

---

## 5. 为什么是这个抽象？

| 性质 | DL 类比 | DAN 优势 |
|------|--------|---------|
| **无梯度** | — | 适用于不可导的 PARAM（代码、离散结构） |
| **可解释的先验** | 架构设计 | HEURISTIC 是显式的人类知识，不藏在超参数里 |
| **广义的 PARAM** | 权重 W | 可优化任意文件/数据，不只是数值张量 |
| **灵活的 LOSS** | 损失函数 | 任意可量化指标，单目标或多目标均可 |

---

*为 LLM Agent 打造的广义端到端学习框架——与神经网络训练结构相同，但无需梯度。*
