# DAN — Deep Agent Network

> A generalized end-to-end learning framework without gradients, powered by LLM agents.

---

## 核心类比 | Core Analogy

DAN 的结构与**端到端深度学习**完全对应，只是把梯度去掉，换成了更广义的优化手段：

| DAN 组件 | 深度学习对应 | 本质 |
|---------|------------|------|
| **META** | 超参（lr, batch_size, optimizer...） | 框架级配置，与具体任务无关，控制**优化动力学** |
| **HEURISTIC** | 先验 / 归纳偏置（CNN、RNN、Attention 都是先验的具体形式） | **结构假设**——用什么形状的函数去拟合解空间 |
| **PARAM** | 权重参数 W | **广义的被优化变量**——可以是代码、系数、配置、任意可调数据 |
| **LOSS** | Loss Function | 可衡量的优化目标 |

所以 DAN 本质上就是：

> **给定一个 HEURISTIC（先验）和 META（超参），通过调整 PARAM 来最小化 LOSS**

这和训练神经网络完全同构——HEURISTIC 决定搜索空间的形状（比如 CNN=局部连接先验），META 决定在这个空间里怎么搜（学习率等），PARAM 是被拟合的对象，LOSS 是反馈来源。区别只在于这里没有梯度，需要用 HEURISTIC 来引导搜索。

---

## 为什么需要 DAN？

深度学习能端到端优化，是因为**梯度**可以反向传播。但在很多场景下：

- PARAM 不可导（代码、离散结构、自然语言）
- 没有梯度信号
- 需要人类知识/规则引导

DAN 就是为了解决这些问题——保留端到端学习的框架结构，但用 **HEURISTIC（先验）** 替代梯度来引导搜索。

---

## 闭环工作流 | Closed Loop

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  PARAM ──(调整)──→  LOSS ──(反馈)──→  HEURISTIC        │
│    ↑                                      │              │
│    │                                      ↓              │
│    └──(决策)────────────────────────── 回到 PARAM         │
│                           ↑                              │
│                          META                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

迭代运行，直至满足 META 中定义的终止条件。

---

## 四元组定义 | Formal Definition

```
DAN Task := (META, HEURISTIC, PARAM₀, LOSS)

其中:
  META      : 框架配置（任务无关的优化动力学参数）
  HEURISTIC : 结构先验（决定搜索空间的形状）
  PARAM₀    : 初始状态
  LOSS      : PARAM → ℝⁿ  (反馈信号)

第 i 次迭代:
  feedback   = LOSS(PARAMᵢ)
  PARAMᵢ₊₁ = HEURISTIC(PARAMᵢ, feedback, META)
  终止:      convergence(PARAMᵢ, PARAMᵢ₊₁, META)
             OR iteration_limit(META) reached
```

---

## 任务示例 | Task Instances

| 任务 | META | HEURISTIC | PARAM | LOSS |
|------|------|-----------|-------|------|
| 数值拟合 | max_evals=5, manual | 手动调参，不跨方程参考 | `a, b, c` 系数 | 散点 MSE |
| 代码优化 | max_loc=1000, 禁止自动化脚本 | 最小化圈复杂度，优先封装 | Python 源代码 | 圈复杂度、Halstead、MI |

---

## 文档 | Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — 完整框架规范（English）
- [ARCHITECTURE_ZH.md](ARCHITECTURE_ZH.md) — 框架形式化定义（中文）

---

## 快速开始 | Quick Start

```bash
cp -r demo/02_CodeOptimize demo/03_YourTask
# 编辑四个组件:
#   META/HEURISTIC/PARAM/LOSS
```
