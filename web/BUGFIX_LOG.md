# DAN Web 调试修复日志

> 本文档记录前端"运行优化"按钮从报错到修复的全过程。

---

## Bug 1: ModuleNotFoundError: No module named 'yaml'

**现象**：点击"运行优化"后，SSE 流输出 `ModuleNotFoundError: No module named 'yaml'`

**根因**：`dan/core.py` 中 `META._load_file()` 使用 `import yaml`，但 `yaml` 非 Python 标准库，需要额外安装。

**修复**：
- 将 `import yaml` + `yaml.safe_load()` 替换为内置 `json.load()`
- `META/task.yaml` → `META/task.json`（所有 demo）
- `.pyc` 缓存问题：删除所有 `__pycache__/` 后解决

**文件变更**：`dan/core.py`, `demo/*/META/task.yaml` → `task.json`

---

## Bug 2: META 文件名错误（task.yaml vs task.json）

**现象**：服务器写入 `META/task.yaml`，但框架已改为查找 `task.json`，导致 `FileNotFoundError`

**根因**：`web/server/index.js` 中写入文件名硬编码为 `task.yaml`

**修复**：`web/server/index.js` 中：
```javascript
// Before
fs.writeFileSync(path.join(mDir, 'task.yaml'), meta);
// After
fs.writeFileSync(path.join(mDir, 'task.json'), meta);
```

---

## Bug 3: PARAM 文件名错误（content vs demo.py）

**现象**：`indicator.py` 期望读取 `__eval_param__/demo.py`，但服务器写入 `PARAM/content`，导致评估失败

**根因**：服务器统一把 PARAM 内容写入 `PARAM/content`，不区分文件类型

**修复**：服务器端智能推断文件名：
```javascript
if (param.trimStart().startsWith('def ') || ...) {
    paramFile = 'demo.py';     // Python 代码
} else if (/^1\.\s*y\s*=/) {
    paramFile = 'func.md';     // 方程
} else {
    paramFile = 'content';
}
```

---

## Bug 4: `--quiet` 模式吞掉所有输出

**现象**：使用 `--quiet` 时，runner 的所有 `print()` 语句被 `verbose=False` 跳过，SSE 流几乎为空

**根因**：`verbose=False` 时整个 `_print_*` 方法都是空操作

**修复**：
- 新增 `--json` 标志，输出机器可读的 JSON Lines
- `JSONRunner` 类：每个事件（iteration_start, loss, param_update 等）都打印一行 JSON
- SSE 流解析 JSON Lines 并转为前端事件

```bash
python3 -m dan <task_dir> --json  # 用于 SSE 流
```

---

## Bug 5: CSV 检测正则表达式错误

**现象**：LinearFunFit 的 scatter.csv 首行是 `x,y`（标题行），不匹配数字正则，scatter.csv 被错写成 `target.md`，导致 MSE=Infinity

**根因**：
1. 服务器正则 `/^\d.../` 不匹配 `x,y`
2. `CSVLossEvaluator._to_python_expr()` 方程解析逻辑有缺陷

**修复**：

### 5a. 服务器 CSV 检测
```javascript
// Before: /^\d[\d,.\s-]+[,]\s*[\d]/.test(...) 
// After:
if (/^x,y$|^[\d-]/.test(loss.trim().split('\n')[0])) {
    fs.writeFileSync(path.join(lDir, 'scatter.csv'), loss);
}
```

### 5b. CSVLossEvaluator 方程解析完全重写

问题：`func.md` 中方程 `ax + b` → `ax` 被当成变量名，`eval('a*x+b')` 时 `a` 未定义 → NameError → Infinity

解决：字符扫描方式将数学表达式转换为合法 Python 表达式：

| 输入 | 输出 |
|------|------|
| `ax + b` | `a*x+b` |
| `ax^2 + bx + c` | `a*x**2+b*x+c` |
| `0.067x^2 + 0.67x + 0` | `0.067*x**2+0.67*x+0` |

### 5c. 系数提取逻辑修复

问题：`\b([a-z])\b` 无法匹配 `ax` 中的 `a`（`a` 后是 `x`，不是单词边界）

解决：逐字符扫描，识别独立的单字母系数名（排除 `x`, `y`）

---

## Bug 6: YAML HEURISTIC 解析残留

**现象**：`YAMLHeuristicStrategy` 中仍使用 `import yaml`，但 yaml 已从框架移除

**根因**：迁移时遗漏

**修复**：改为 `json.loads()`（HEURISTIC YAML 规则实际不需要，改用 JSON 格式更合理）

---

## 最终验证结果

| Demo | PARAM 文件 | LOSS 文件 | 指标 | 状态 |
|------|-----------|-----------|------|------|
| `01_LinearFunFit` | `func.md` | `scatter.csv` | `mse_eq1=136.06, mse_eq2=136.06` | ✅ |
| `02_CodeOptimize/01_loss1` | `demo.py` | `target.md` | `status=human_evaluated` | ✅ |
| `02_CodeOptimize/02_loss3` | `demo.py` | `indicator.py` | `loc=290, avg_cc=5.77, mi=32.7` | ✅ |

---

## 修改文件清单

| 文件 | 操作 |
|------|------|
| `dan/core.py` | 重构 META 加载、移除 yaml 依赖、重写 CSVLossEvaluator |
| `dan/runner.py` | 添加 JSONRunner 类和 `--json` 模式 |
| `dan/__main__.py` | 新增 `--json` CLI 标志 |
| `web/server/index.js` | 修复 task.json 写入、PARAM 文件名推断、CSV 检测正则 |
| `demo/*/META/task.yaml` | → `task.json`（迁移） |
| `ARCHITECTURE*.md` | 更新文档 |
