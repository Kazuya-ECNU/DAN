# DAN — Deep Agent Network 架构文档

> 框架版本 0.1 | 为 LLM Agent 打造的广义端到端优化框架。

---

## 核心类比：DAN ≋ 深度学习

| DAN 组件 | 深度学习对应 | 本质 |
|---------|------------|------|
| **META** | 超参 | 框架级配置，与任务无关，控制**优化动力学** |
| **HEURISTIC** | 先验 / 架构 | 结构假设——决定搜索空间的形状 |
| **PARAM** | 权重 W | 广义的被优化变量——代码、系数、配置、任意可调数据 |
| **LOSS** | Loss Function | 可衡量的优化目标 |

**DAN = 深度学习的无梯度版本。**

---

## 项目结构

```
DAN/
├── dan/                           # 框架包（可 pip install）
│   ├── __init__.py               # 公共 API
│   ├── __main__.py               # CLI: python -m dan <task_dir>
│   ├── show.py                   # 查看任务上下文: python -m dan.show <task_dir>
│   ├── core.py                   # 核心抽象类
│   └── runner.py                 # 主循环引擎
│
├── demo/                          # 任务实例
│   ├── 01_LinearFunFit/
│   │   ├── META/task.json
│   │   ├── HEURISTIC/rules.md
│   │   ├── PARAM/func.md
│   │   ├── LOSS/scatter.csv
│   │   └── results/
│   └── 02_CodeOptimize/
│       ├── 01_loss1/
│       └── 02_loss3/
│           ├── META/task.json
│           ├── HEURISTIC/rules.md
│           ├── PARAM/demo.py
│           ├── LOSS/
│           │   ├── indicator.py
│           │   └── target.md
│           └── results/
```

---

## 四元组件详解

### META — 任务配置

```yaml
# demo/XX/META/task.json
name: CodeOptimize-02_loss3
description: 根据代码质量指标优化代码
max_iterations: 10
output_dir: results
stop_if: "loss.mi >= 65"   # 可选：早停条件
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 任务名称 |
| `description` | string | 任务描述 |
| `max_iterations` | int | 迭代上限 |
| `output_dir` | string | 结果输出目录 |
| `stop_if` | string | 可选，表达式如 `"loss.mi >= 65"` |

### HEURISTIC — 搜索策略

支持三种格式（优先级：Python > YAML > Markdown）：

| 格式 | 文件类型 | 策略类型 | 适用场景 |
|------|---------|---------|---------|
| Python | `.py` | `decide(iteration, param_snapshot, loss_result) → {f: c}` | 完全可编程 |
| YAML | `.json` | 声明式 `if → then` 规则 | 结构化策略 |
| Markdown | `.md` | 人类可读指南 | 人机协同任务 |

### PARAM — 优化主体

`PARAM/` 目录下的所有文件都会被加载为 `{文件名: 内容}` 字典，框架负责保存更新。

### LOSS — 损失评估

| 评估器 | 触发条件 | 输出 |
|-------|---------|------|
| `PythonLossEvaluator` | `LOSS/indicator.py` 存在 | JSON 度量指标 |
| `CSVLossEvaluator` | `LOSS/*.csv` 存在 | MSE 拟合误差 |
| `TextLossEvaluator` | `LOSS/*.md` 存在 | 需人工评估 |
| `NoLossEvaluator` | 无 LOSS 文件 | 无自动评估 |

---

## CLI 工具

```bash
# 查看任务上下文（LLM Agent 推荐使用）
python -m dan.show demo/02_CodeOptimize/02_loss3

# 运行自动化优化循环
python -m dan demo/02_CodeOptimize/02_loss3 [--quiet] [--max-iter N]
```

---

## 新建任务

```bash
cp -r demo/02_CodeOptimize/02_loss3 demo/03_YourTask
# 编辑:
#   META/task.json      ← 任务配置
#   HEURISTIC/rules.md  ← 搜索策略
#   PARAM/              ← 待优化文件
#   LOSS/               ← 评估逻辑
```

---

## 形式化定义

```
DAN Task := (META, HEURISTIC, PARAM₀, LOSS)

第 i 次迭代:
  param_snapshot = PARAM_i
  loss_result   = LOSS(PARAM_i)
  param_update  = HEURISTIC(PARAM_i, loss_result, META)
  PARAM_{i+1}   = apply(PARAM_i, param_update)
  终止条件:      META.stop_if(loss_result) OR i >= META.max_iterations
```
