"""
DAN Core Abstractions — META, HEURISTIC, PARAM, LOSS

Each task is a 4-tuple: (META, HEURISTIC, PARAM₀, LOSS)
The framework manages the loop; users only define the four components.
"""

import json
import re
import importlib.util
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────────────────────
# META — Task Configuration
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class META:
    """
    Task-agnostic configuration (≈ hyperparameters in DL).

    Defines how the optimization loop behaves:
    - max_iterations: stopping criterion
    - output_dir: where to write results
    - description: human-readable task description
    """
    name: str = ""
    description: str = ""
    max_iterations: int = 10
    output_dir: str = "results"
    stop_if: Optional[str] = None   # e.g. "loss < 0.01"

    @classmethod
    def load(cls, path: str | Path) -> "META":
        """Load META from a directory or JSON file."""
        p = Path(path)
        if p.is_file():
            return cls._load_file(p)
        # Directory-based: prefer JSON (stdlib), fall back to YAML
        for fname in ("task.json", "meta.json", "META.json"):
            fp = p / fname
            if fp.exists():
                return cls._load_file(fp)
        raise FileNotFoundError(f"META not found in {path}")

    @classmethod
    def _load_file(cls, fp: Path) -> "META":
        with open(fp) as f:
            data = json.load(f)
        return cls(
            name=data.get("name", fp.parent.name),
            description=data.get("description", ""),
            max_iterations=data.get("max_iterations", 10),
            output_dir=data.get("output_dir", "results"),
            stop_if=data.get("stop_if"),
        )


# ──────────────────────────────────────────────────────────────────────────────
# PARAM — The Optimizable Entity
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PARAM:
    """
    The generalized optimizable entity (≈ weights W in DL).

    Can be: code files, coefficient files, configs, prompts, etc.
    The framework loads, saves, and updates PARAM on each iteration.
    """
    root: Path = field(default_factory=Path)

    def load(self, subpath: str = "") -> Dict[str, Any]:
        """Load all PARAM content from the param/ directory."""
        param_dir = self.root / subpath
        if not param_dir.exists():
            return {}
        result = {}
        for f in sorted(param_dir.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(param_dir)
                result[str(rel)] = f.read_text(encoding="utf-8")
        return result

    def save(self, content: Dict[str, str], subpath: str = "", output_dir: str = "results") -> Path:
        """Save PARAM content to output directory."""
        out = self.root / output_dir
        out.mkdir(parents=True, exist_ok=True)
        for rel_path, text in content.items():
            fp = out / rel_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(text, encoding="utf-8")
        return out


# ──────────────────────────────────────────────────────────────────────────────
# HEURISTIC — Search Strategy / Prior
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class HEURISTIC:
    """
    Search strategy and structural prior (≈ architecture / inductive bias in DL).

    Defines how PARAM is adjusted given LOSS feedback.
    Can be:
    - Python file: fully programmable strategy
    - YAML file: declarative rules
    - Markdown file: human-readable guidelines (for human-in-the-loop)

    Each demo's HEURISTIC is task-specific and non-transferable.
    """
    root: Path = field(default_factory=Path)

    def load(self) -> List[Dict]:
        """
        Load HEURISTIC rules from the heuristic/ directory.
        Returns a list of rule dicts with keys: type, path, content
        """
        h_dir = self.root
        rules = []
        if not h_dir.exists():
            return rules
        for f in sorted(h_dir.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                rules.append({
                    "type": f.suffix,      # .py, .yaml, .md
                    "path": f,
                    "name": f.stem,
                    "content": f.read_text(encoding="utf-8"),
                })
        return rules

    def get_strategy(self) -> "HeuristicStrategy":
        """
        Build the appropriate strategy object based on heuristic files present.
        Priority: .py > .yaml > .md
        """
        rules = self.load()
        if not rules:
            return NoHeuristicStrategy()

        # Prefer Python (full programmability)
        py_rules = [r for r in rules if r["type"] == ".py"]
        if py_rules:
            return PythonHeuristicStrategy(py_rules)

        yaml_rules = [r for r in rules if r["type"] in (".yaml", ".yml")]
        if yaml_rules:
            return YAMLHeuristicStrategy(yaml_rules)

        md_rules = [r for r in rules if r["type"] == ".md"]
        if md_rules:
            return MarkdownHeuristicStrategy(md_rules)

        return NoHeuristicStrategy()

    def get_human_rules(self) -> str:
        """Get human-readable rules (for manual optimization tasks)."""
        rules = self.load()
        md_rules = [r for r in rules if r["type"] == ".md"]
        if md_rules:
            return md_rules[0]["content"]
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# HEURISTIC Strategy Implementations
# ──────────────────────────────────────────────────────────────────────────────

class HeuristicStrategy:
    """Base class for heuristic strategies."""
    def decide(self, iteration: int, param_snapshot: Dict, loss_result: Dict) -> Dict[str, str]:
        """
        Given current iteration, PARAM snapshot, and LOSS result,
        return a dict of {filename: new_content} for PARAM updates.
        """
        raise NotImplementedError


class NoHeuristicStrategy(HeuristicStrategy):
    def decide(self, iteration, param_snapshot, loss_result) -> Dict:
        return {}


class PythonHeuristicStrategy(HeuristicStrategy):
    """
    Fully programmable heuristic via Python file.
    The file must define a `decide(iteration, param_snapshot, loss_result)` function
    that returns {filename: new_content} dict.
    """
    def __init__(self, rules: List[Dict]):
        self.rules = rules
        self._module = None

    def decide(self, iteration: int, param_snapshot: Dict, loss_result: Dict) -> Dict[str, str]:
        for rule in self.rules:
            spec = importlib.util.spec_from_file_location("heuristic", rule["path"])
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "decide"):
                return mod.decide(iteration, param_snapshot, loss_result)
        return {}


class YAMLHeuristicStrategy(HeuristicStrategy):
    """
    Declarative heuristic via YAML rules.
    Rules specify: condition → action (what to change in PARAM).
    """
    def __init__(self, rules: List[Dict]):
        self.rules = []
        for r in rules:
            data = json.loads(r["content"]) if r["content"].strip().startswith("{") else {}
            if isinstance(data, list):
                self.rules.extend(data)
            elif isinstance(data, dict):
                self.rules.append(data)

    def decide(self, iteration: int, param_snapshot: Dict, loss_result: Dict) -> Dict[str, str]:
        updates = {}
        for rule in self.rules:
            condition = rule.get("if", {})
            action = rule.get("then", {})
            if self._check_condition(condition, loss_result, iteration):
                for fname, edit in action.items():
                    if fname in param_snapshot:
                        updates[fname] = self._apply_edit(param_snapshot[fname], edit)
        return updates

    def _check_condition(self, cond: Dict, loss: Dict, iteration: int) -> bool:
        if "iteration_lt" in cond and iteration >= cond["iteration_lt"]:
            return False
        if "iteration_gte" in cond and iteration < cond["iteration_gte"]:
            return False
        for key, op in cond.items():
            if key.startswith("loss."):
                metric = key[5:]
                val = loss.get(metric)
                if val is None:
                    continue
                if isinstance(op, dict):
                    if "lt" in op and not (val < op["lt"]):
                        return False
                    if "lte" in op and not (val <= op["lte"]):
                        return False
                    if "gt" in op and not (val > op["gt"]):
                        return False
        return True

    def _apply_edit(self, text: str, edit: Dict) -> str:
        # Simple text replacement: {old: ..., new: ...}
        if "replace" in edit:
            return text.replace(edit["replace"]["old"], edit["replace"]["new"], 1)
        return text


class MarkdownHeuristicStrategy(HeuristicStrategy):
    """
    Human-in-the-loop heuristic.
    Returns the markdown content so the human agent can read and act on it.
    """
    def __init__(self, rules: List[Dict]):
        self.rules = rules

    def decide(self, iteration: int, param_snapshot: Dict, loss_result: Dict) -> Dict[str, str]:
        # No automatic updates; human follows the .md rules
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# LOSS — Feedback Signal
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LOSS:
    """
    Objective function (≈ Loss Function in DL).
    Produces a feedback signal that drives HEURISTIC decisions.
    """
    root: Path = field(default_factory=Path)

    def load(self) -> List[Dict]:
        """Load all LOSS resources from the loss/ directory."""
        l_dir = self.root
        items = []
        if not l_dir.exists():
            return items
        for f in sorted(l_dir.rglob("*")):
            if f.is_file() and not f.name.startswith(".") and f.suffix != ".pyc":
                items.append({
                    "type": f.suffix,
                    "path": f,
                    "name": f.stem,
                    "content": f.read_text(encoding="utf-8") if f.suffix in (".py", ".md", ".txt", ".yaml", ".yml") else None,
                })
        return items

    def get_evaluator(self) -> "LossEvaluator":
        """
        Build the appropriate evaluator based on loss/ files present.
        Priority: Python content > .csv > .md > .yaml
        Detection is content-based (not just extension), so any file
        whose content starts with def/import is treated as a Python indicator.
        """
        items = self.load()

        # Python: either .py file OR content starts with def / import
        py_items = [i for i in items if i["type"] == ".py" and i["name"] not in ("__init__",)]
        if not py_items:
            py_items = [i for i in items if i["content"] and
                        i["content"].lstrip().startswith(("def ", "import ", "from "))]
        if py_items:
            return PythonLossEvaluator(py_items)

        # CSV data: either .csv file OR content matches x,y / digit pattern
        csv_items = [i for i in items if i["type"] == ".csv"]
        if not csv_items:
            csv_items = [i for i in items if i["content"] and
                        re.match(r'^x,y$|^[\d-]', i["content"].strip().split('\n')[0])]
        if csv_items:
            return CSVLossEvaluator(csv_items)

        # YAML
        yaml_items = [i for i in items if i["type"] in (".yaml", ".yml")]
        if yaml_items:
            return YAMLLossEvaluator(yaml_items)

        # Markdown / text
        md_items = [i for i in items if i["type"] == ".md"]
        if md_items:
            return TextLossEvaluator(md_items)

        return NoLossEvaluator()

    def get_description(self) -> str:
        """Get the task description from target.md or equivalent."""
        items = self.load()
        md_items = [i for i in items if i["type"] == ".md"]
        if md_items:
            return md_items[0]["content"]
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# LOSS Evaluator Implementations
# ──────────────────────────────────────────────────────────────────────────────

class LossEvaluator:
    """Base class for loss evaluators."""
    def evaluate(self, param_content: Dict[str, str], work_dir: Path) -> Dict[str, float]:
        """Run evaluation and return a dict of metric_name -> value."""
        raise NotImplementedError

    def format_summary(self, result: Dict[str, float]) -> str:
        """Human-readable summary of loss result."""
        return "\n".join(f"  {k}: {v}" for k, v in result.items())


class NoLossEvaluator(LossEvaluator):
    def evaluate(self, param_content, work_dir) -> Dict:
        return {}


class PythonLossEvaluator(LossEvaluator):
    """
    Runs a Python indicator script that returns metrics.
    The script should define `analyze(param_path: str) -> Dict[str, float]`
    or print a JSON dict to stdout.
    """
    def __init__(self, items: List[Dict]):
        self.items = items
        # Primary indicator is the one named "indicator"
        self.indicator = next((i for i in items if i["name"] == "indicator"), items[0])

    def evaluate(self, param_content: Dict[str, str], work_dir: Path) -> Dict[str, float]:
        import json
        import subprocess

        # Write PARAM files to a temp evaluation dir
        eval_dir = work_dir / "__eval_param__"
        eval_dir.mkdir(exist_ok=True)
        for fname, text in param_content.items():
            (eval_dir / fname).write_text(text, encoding="utf-8")

        # Run the indicator script
        result_file = work_dir / "__loss_result__.json"
        try:
            result = subprocess.run(
                ["python3", str(self.indicator["path"]), str(eval_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Try parsing last JSON line
            for line in reversed(result.stdout.strip().splitlines()):
                try:
                    parsed = json.loads(line)
                    # Unwrap {"metrics": {...}} if present
                    if isinstance(parsed, dict) and "metrics" in parsed:
                        return parsed["metrics"]
                    return parsed
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            return {"error": float(str(e))}

        return {}


class YAMLLossEvaluator(LossEvaluator):
    """YAML-based loss: defines metrics and comparison logic."""
    def __init__(self, items: List[Dict]):
        self.config = json.loads(items[0]["content"]) if items else {}

    def evaluate(self, param_content: Dict[str, str], work_dir: Path) -> Dict[str, float]:
        return {}


class CSVLossEvaluator(LossEvaluator):
    """CSV-based loss: for data fitting tasks (e.g., scatter data)."""
    def __init__(self, items: List[Dict]):
        self.csv_path = items[0]["path"]

    def evaluate(self, param_content: Dict[str, str], work_dir: Path) -> Dict[str, float]:
        """
        Evaluate: given func.md equations and scatter.csv data, compute MSE.
        Handles: y = ax + b  (linear) and y = ax^2 + bx + c (quadratic).
        Coefficients default to 0.0 — the agent must update them in PARAM.
        """
        # Parse scatter data (skip header row if present)
        scatter = []
        with open(self.csv_path) as f:
            first = f.readline().strip()
            if not re.match(r'^[\d.-]+,[\d.-]+$', first):
                # Header row: skip it
                pass
            else:
                parts = first.split(',')
                try:
                    scatter.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    pass
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    try:
                        scatter.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        continue

        if not scatter:
            return {"mse_eq1": float('inf'), "mse_eq2": float('inf')}

        # Parse equations from func.md
        func_text = param_content.get("func.md", "")
        equations = re.findall(r'y\s*=\s*([^,\n]+)', func_text)

        results = {}
        for i, eq in enumerate(equations[:2], 1):
            mse = self._compute_mse(eq.strip(), scatter)
            results[f"mse_eq{i}"] = mse

        return results


    def _to_python_expr(self, eq: str) -> str:
        """
        Convert mathematical equation to valid Python expression.
        Handles: ax, ax^2, 0.67x, 0.067x^2, a*x, etc.
        Input:  'ax + b' or 'ax^2 + bx + c'
        Output: 'a*x + b' or 'a*x**2 + b*x + c'
        """
        eq = eq.strip().replace('^', '**')
        result = []
        i = 0
        while i < len(eq):
            ch = eq[i]
            if ch.isspace():
                i += 1; continue
            if ch in '+-':
                result.append(ch); i += 1; continue
            if ch == '*':
                result.append('*'); i += 1; continue
            # Scan term
            j = i
            while j < len(eq) and eq[j] not in '+-* ':
                j += 1
            term = eq[i:j]
            i = j
            if not term:
                continue
            if '*' in term or '/' in term or '**' in term:
                result.append(term); continue
            # Implicit multiplication: ax, ax^2, 0.67x, bx
            m = re.match(r'^([a-z][a-z0-9]*)(x(?:\*\*\d+)?)$', term)
            if m:
                result.append(f'{m.group(1)}*{m.group(2) or "x"}'); continue
            m2 = re.match(r'^([0-9]+(?:\.[0-9]+)?)(x(?:\*\*\d+)?)$', term)
            if m2:
                result.append(f'{m2.group(1)}*{m2.group(2) or "x"}'); continue
            result.append(term)
        return ''.join(result)

    def _extract_coeffs(self, eq: str) -> set:
        """Extract coefficient names from equation (single lowercase letters, not x/y)."""
        eq_clean = re.sub(r'^y\s*=', '', eq)
        names = set()
        i = 0
        while i < len(eq_clean):
            ch = eq_clean[i]
            if ch.isalpha() and ch not in 'xy':
                before = eq_clean[i-1] if i > 0 else ' '
                after = eq_clean[i+1] if i < len(eq_clean) - 1 else ' '
                if not (before.isalpha() or before.isdigit()):
                    names.add(ch)
            i += 1
        return names

    def _compute_mse(self, eq: str, scatter: list) -> float:
        """Compute MSE for an equation against scatter data."""
        names = self._extract_coeffs(eq)
        coeffs = {n: 0.0 for n in names}
        try:
            eq_py = self._to_python_expr(eq)
        except Exception:
            return float('inf')
        total = 0.0
        for x, y_actual in scatter:
            try:
                y_pred = eval(eq_py, {'x': x, **coeffs})
                total += (y_pred - y_actual) ** 2
            except Exception:
                return float('inf')
        return total / len(scatter) if scatter else 0.0

class TextLossEvaluator(LossEvaluator):
    """Text-based loss: returns 0 (human evaluates manually)."""
    def __init__(self, items: List[Dict]):
        self.description = items[0]["content"]

    def evaluate(self, param_content: Dict[str, str], work_dir: Path) -> Dict[str, float]:
        return {"status": "human_evaluated"}


# ──────────────────────────────────────────────────────────────────────────────
# Iteration State
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class IterationState:
    """Immutable snapshot of one iteration."""
    iteration: int
    param_snapshot: Dict[str, str]
    loss_result: Dict[str, float]
    param_updates: Dict[str, str]
    timestamp: str = ""


@dataclass
class OptimizationResult:
    """Final result of the optimization run."""
    meta: META
    iterations: List[IterationState] = field(default_factory=list)
    final_loss: Dict[str, float] = field(default_factory=dict)
    converged: bool = False
    stopping_reason: str = ""

    def save(self, output_dir: Path):
        """Save optimization trace to output_dir."""
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "optimization_trace.md").write_text(self._format_trace(), encoding="utf-8")

    def _format_trace(self) -> str:
        lines = ["# Optimization Trace\n"]
        for s in self.iterations:
            lines.append(f"## Iteration {s.iteration}\n")
            if s.loss_result:
                lines.append("**Loss:** " + ", ".join(f"{k}={v}" for k, v in s.loss_result.items()) + "\n")
            if s.param_updates:
                lines.append("**Updates:** " + ", ".join(s.param_updates.keys()) + "\n")
            lines.append("---\n")
        return "".join(lines)
