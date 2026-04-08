# DAN — Deep Agent Network 架构文档

> 基于 LLM Agent 的闭环优化框架

---

## 1. 框架哲学 | Framework Philosophy

DAN 将所有优化任务定义为一个**四元闭环系统**：

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   PARAM  ──(调整)──→  LOSS  ──(反馈)──→                │
│     ↑                                    HEURISTIC      │
│     │                                         │         │
│     └──(决策)───────────────────────────────┘         │
│                         ↑                               │
│                       META                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

循环迭代运行，直至收敛条件满足，**全程无梯度依赖**。

---

## 2. 四元核心组件 | Four Core Components

| 组件 | 职责 | 描述 |
|------|------|------|
| **META** | 目标定义 | 任务目标、背景、评估上下文 |
| **HEURISTIC** | 搜索策略 | 如何调整 PARAM、如何判断终止、如何评价进展 |
| **PARAM** | 优化主体 | 被调优的实体——代码、系数、权重、配置等 |
| **LOSS** | 反馈信号 | 衡量当前状态与 META 差距的定量指标 |

### 2.1 META — 目标定义层

定义任务**是什么**。通常为自然语言描述，存放于 `loss/target.md` 或类似元数据文件。

```
loss/
└── target.md          # 任务目标描述
    └── target/        #（可选）结构化数据资产（如散点数据 CSV）
```

### 2.2 HEURISTIC — 搜索策略层

定义任务**怎么做**。存放于 `heuristic/rule.md`——一组约束条件和策略规则，**任务相关且不可迁移**。

```
heuristic/
└── rule.md            # 搜索规则与约束条件
```

### 2.3 PARAM — 优化主体层

**被优化的实体**，每次迭代中实际被修改的部分。

```
param/
└── xxx                # 可为 .py 代码、.md 方程、.json 配置等任意形式
```

### 2.4 LOSS — 损失评估层

**目标函数**——产生驱动 HEURISTIC 决策的反馈信号。

```
loss/
├── indicator.py       # 评估脚本 / 指标计算
└── target.md          # 目标描述
```

---

## 3. 闭环工作流 | Closed-Loop Workflow

```
┌────────────────────────────────────────────────────────┐
│                      迭代循环                           │
├────────────────────────────────────────────────────────┤
│                                                        │
│  1. READ META          读取任务目标与约束               │
│          ↓                                               │
│  2. READ PARAM         加载当前参数状态                 │
│          ↓                                               │
│  3. CALCULATE LOSS     运行评估脚本获取反馈             │
│          ↓                                               │
│  4. APPLY HEURISTIC    根据规则决定如何调整             │
│          ↓                                               │
│  5. UPDATE PARAM       执行修改                         │
│          ↓                                               │
│  6. CHECK STOP CRITERIA  → 若未完成，返回步骤 3        │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 4. 任务实例 | Task Instances

### 4.1 01_LinearFunFit — 数值系数拟合

```
demo/01_LinearFunFit/
├── META/loss/target/my_scatter.csv    # 散点数据
├── HEURISTIC/heuristic/rule.md       # 手动调参，最多比较5次
├── PARAM/param/func.md               # y = ax + b ; y = ax² + bx + c
└── LOSS/ (散点对比误差)               # Loss = Σ(y_pred - y_actual)²
```

### 4.2 02_CodeOptimize — 代码质量优化

```
demo/02_CodeOptimize/
├── META/loss/target.md               # 目标：所有指标尽量低
├── HEURISTIC/heuristic/rule.md      # 禁止自动脚本，代码改动≤1000行
├── PARAM/param/demo.py               # 待优化的电商订单系统代码
└── LOSS/loss/indicator.py            # 圈复杂度、Halstead 复杂度、MI 等
```

---

## 5. 形式化定义 | Formal Specification

DAN 任务定义为一个四元组：

```
Task := (META, HEURISTIC, PARAM₀, LOSS)

其中:
  META      : 自然语言目标描述
  HEURISTIC : 约束条件 + 搜索规则集合
  PARAM₀    : 初始参数状态
  LOSS      : 函数 → ℝⁿ  (n维反馈向量)

第 i 次迭代:
  PARAMᵢ₊₁ = HEURISTIC(PARAMᵢ, LOSS(PARAMᵢ))
  终止条件:  LOSS(PARAMᵢ₊₁) 满足 META 标准
            或 达到迭代次数上限
```

---

## 6. 新建任务 | Creating a New Task

```bash
cp -r demo/02_CodeOptimize demo/03_YourTask
# 然后编辑:
#   - META:      demo/03_YourTask/loss/target.md
#   - HEURISTIC: demo/03_YourTask/heuristic/rule.md
#   - PARAM:     demo/03_YourTask/param/your_param
#   - LOSS:      demo/03_YourTask/loss/indicator.py（如有需要）
```

Agent 将遵循相同的 读取→评估→调整 循环，无需修改框架。

---

*为 LLM Agent 构建的结构化、可解释、无梯度优化框架。*
