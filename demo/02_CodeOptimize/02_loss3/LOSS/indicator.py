import ast
import re
import math

# 给AST节点添加父节点引用，用于全局变量识别
class ParentNodeVisitor(ast.NodeVisitor):
    def visit(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node
            self.visit(child)

# 1. 圈复杂度（McCabe 业界标准）
def calculate_cyclomatic_complexity(func_node):
    cc = 1  # 基础值
    for node in ast.walk(func_node):
        # 所有分支点都会增加复杂度
        if isinstance(node, (ast.If, ast.While, ast.For, ast.And, ast.Or)):
            cc += 1
        elif isinstance(node, ast.Try):
            cc += 1
        elif isinstance(node, ast.ExceptHandler):
            cc += 1
    return cc

# 2. Halstead 复杂度（软件科学通用指标）
def calculate_halstead(code_str):
    operators = set()
    operands = set()
    op_count = 0
    operand_count = 0

    tree = ast.parse(code_str)
    for node in ast.walk(tree):
        # 统计运算符
        if isinstance(node, ast.operator):
            op_type = type(node).__name__
            operators.add(op_type)
            op_count += 1
        # 统计操作数
        elif isinstance(node, ast.Constant):
            operands.add(repr(node.value))
            operand_count += 1
        elif isinstance(node, ast.Name):
            operands.add(node.id)
            operand_count += 1

    n1 = len(operators)  # 唯一运算符数量
    n2 = len(operands)   # 唯一操作数数量
    N1 = op_count        # 运算符总次数
    N2 = operand_count   # 操作数总次数

    if N1 + N2 == 0:
        return 0, 0, 0
    
    # Halstead 核心指标
    volume = (N1 + N2) * math.log2(n1 + n2)  # 程序体积
    difficulty = (n1 / 2) * (N2 / n2) if n2 != 0 else 0  # 难度
    effort = difficulty * volume  # 实现工作量
    return volume, difficulty, effort

# 3. 可维护性指数 MI（微软/ISO 9126 标准）
def calculate_maintainability_index(halstead_volume, avg_cc, loc):
    if loc <= 0 or halstead_volume <= 0:
        return 100.0
    # 标准公式：MI = 171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC)
    mi = 171 
    mi -= 5.2 * math.log(halstead_volume)
    mi -= 0.23 * avg_cc
    mi -= 16.2 * math.log(loc)
    return max(0, min(100, mi))  # 归一化到0-100

# 4. 重复代码率
def calculate_duplicate_rate(lines):
    line_samples = {}
    duplicate_lines = 0
    for line in lines:
        stripped = line.strip()
        if len(stripped) < 8:  # 忽略空行/短行
            continue
        if stripped in line_samples:
            duplicate_lines += 1
        else:
            line_samples[stripped] = 1
    return (duplicate_lines / len(lines)) * 100 if lines else 0

# 主分析函数
def analyze_code_quality(file_path="../param/demo.py"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}，请确保烂代码文件在当前目录")
        return

    # 预处理
    lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
    loc = len(lines)  # 有效代码行数

    # 解析AST
    tree = ast.parse(code)
    ParentNodeVisitor().visit(tree)  # 绑定父节点

    # 收集函数指标
    func_cc_list = []
    func_loc_list = []
    global_var_names = set()

    # 识别全局变量
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.parent, ast.Module):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    global_var_names.add(t.id)

    # 遍历所有函数
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # 函数行数
            f_loc = node.end_lineno - node.lineno + 1
            func_loc_list.append(f_loc)
            # 圈复杂度
            cc = calculate_cyclomatic_complexity(node)
            func_cc_list.append(cc)

    # 计算汇总指标
    avg_cc = sum(func_cc_list)/len(func_cc_list) if func_cc_list else 0
    avg_func_loc = sum(func_loc_list)/len(func_loc_list) if func_loc_list else 0
    dup_rate = calculate_duplicate_rate(lines)
    halstead_vol, halstead_diff, halstead_effort = calculate_halstead(code)
    mi = calculate_maintainability_index(halstead_vol, avg_cc, loc)

    # 输出报告
    print("="*65)
    print("          业界通用代码质量分析报告")
    print("="*65)
    print(f"📄 有效代码行数 LOC: {loc}")
    print(f"📊 平均函数行数: {avg_func_loc:.1f} 行")
    print(f"   └─ 标准: <15 优秀, 15-30 中等, >30 差")
    print(f"🔍 平均圈复杂度: {avg_cc:.1f}")
    print(f"   └─ 标准: <5 优秀, 5-10 中等, >10 高风险")
    print(f"♻️  重复代码率: {dup_rate:.1f}%")
    print(f"   └─ 标准: <5% 优秀, 5-10% 中等, >10% 差")
    print(f"🧠 Halstead 难度: {halstead_diff:.1f}")
    print(f"   └─ 标准: <10 简单, 10-20 中等, >20 困难")
    print(f"✅ 可维护性指数 MI: {mi:.1f}")
    print(f"   └─ 标准: ≥80 优秀, 65-79 中等, <65 差")
    print("="*65)
    
    # 结论
    if mi < 65:
        print("🔥 结论：该代码可维护性极差，属于典型的「隐性烂代码」")
    elif mi < 80:
        print("⚠️  结论：该代码可维护性一般，有优化空间")
    else:
        print("✅ 结论：该代码质量良好")


if __name__ == "__main__":
    import sys, json
    # Support framework invocation: python indicator.py /path/to/param_dir
    path = sys.argv[1] + "/demo.py" if len(sys.argv) > 1 else "../param/demo.py"
    result = analyze_code_quality(path)
    # Print machine-readable JSON summary at the end (for framework parsing)
    # Re-parse to get numeric values for JSON output
    try:
        with open(path) as f:
            code = f.read()
        lines = [l for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
        loc = len(lines)
        tree = ast.parse(code)
        ParentNodeVisitor().visit(tree)
        func_cc_list, func_loc_list = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_loc_list.append(node.end_lineno - node.lineno + 1)
                func_cc_list.append(calculate_cyclomatic_complexity(node))
        avg_cc = sum(func_cc_list)/len(func_cc_list) if func_cc_list else 0
        avg_func_loc = sum(func_loc_list)/len(func_loc_list) if func_loc_list else 0
        dup_rate = calculate_duplicate_rate(lines)
        halstead_vol, halstead_diff, _ = calculate_halstead(code)
        mi = calculate_maintainability_index(halstead_vol, avg_cc, loc)
        json_output = {
            "loc": loc,
            "avg_cc": round(avg_cc, 2),
            "avg_func_loc": round(avg_func_loc, 1),
            "dup_rate": round(dup_rate, 1),
            "halstead_diff": round(halstead_diff, 1),
            "mi": round(mi, 1)
        }
        print(json.dumps({"metrics": json_output}))
    except Exception:
        pass