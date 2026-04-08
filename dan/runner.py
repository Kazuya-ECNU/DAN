"""
DAN Runner — Main Optimization Loop

Manages the closed-loop iteration:
    PARAM ──(adjust)──→ LOSS ──(feedback)──→ HEURISTIC ──(decide)──→ PARAM

Usage:
    runner = Runner(demo_path="demo/02_CodeOptimize/02_loss3")
    result = runner.run()
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dan.core import (
    META, HEURISTIC, PARAM, LOSS,
    OptimizationResult, IterationState,
    PythonHeuristicStrategy, YAMLHeuristicStrategy, MarkdownHeuristicStrategy,
    PythonLossEvaluator, CSVLossEvaluator,
)


class Runner:
    """
    Main optimization loop runner.

    Usage:
        runner = Runner(task_dir="demo/02_CodeOptimize/02_loss3")
        result = runner.run()
    """

    def __init__(
        self,
        task_dir: str | Path,
        verbose: bool = True,
    ):
        self.task_dir = Path(task_dir)
        self.verbose = verbose

        # Load the four components
        self.meta = META.load(self.task_dir / "META")
        self.heuristic = HEURISTIC(root=self.task_dir / "HEURISTIC")
        self.param = PARAM(root=self.task_dir / "PARAM")
        self.loss = LOSS(root=self.task_dir / "LOSS")

        self.output_dir = self.task_dir / self.meta.output_dir
        self.result: Optional[OptimizationResult] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> OptimizationResult:
        """
        Execute the full optimization loop.
        Returns an OptimizationResult with full iteration trace.
        """
        self._print_banner()

        # Build strategy and evaluator
        strategy = self.heuristic.get_strategy()
        evaluator = self.loss.get_evaluator()

        # Load initial PARAM
        param_content = self.param.load()
        if not param_content:
            print("⚠️  PARAM directory is empty — nothing to optimize.")
            return OptimizationResult(meta=self.meta)

        # Load task description
        loss_desc = self.loss.get_description()
        heuristic_rules = self.heuristic.get_human_rules()

        # Print context
        self._print_meta()
        if loss_desc:
            self._print_section("LOSS", loss_desc[:300])
        if heuristic_rules:
            self._print_section("HEURISTIC", heuristic_rules[:300])

        # Main loop
        state = IterationState(iteration=0, param_snapshot=param_content,
                              loss_result={}, param_updates={})
        result = OptimizationResult(meta=self.meta)

        for i in range(1, self.meta.max_iterations + 1):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._print_iteration_header(i, ts)

            # Step 1: Evaluate LOSS
            self._print_step("Compute LOSS", "Running evaluation...")
            loss_result = evaluator.evaluate(param_content, self.task_dir)
            self._print_loss_result(loss_result)

            # Check stop condition
            stop, reason = self._check_stop(loss_result, i)
            if stop:
                self._print_section("STOP", reason)
                result.converged = True
                result.stopping_reason = reason
                result.final_loss = loss_result
                break

            # Step 2: Apply HEURISTIC
            self._print_step("Apply HEURISTIC", f"Strategy: {type(strategy).__name__}")
            if isinstance(strategy, (PythonHeuristicStrategy, YAMLHeuristicStrategy)):
                updates = strategy.decide(i, param_content, loss_result)
            elif isinstance(strategy, MarkdownHeuristicStrategy):
                # Human-in-the-loop: read rules, wait for manual update
                self._print_step("HEURISTIC (Human-in-the-loop)",
                                 "See rules above. Apply changes manually, then continue.")
                updates = {}
            else:
                updates = {}

            # Step 3: Update PARAM
            if updates:
                self._print_step("Update PARAM", f"Files: {', '.join(updates.keys())}")
                param_content = self._apply_updates(param_content, updates)
                self.param.save(param_content, output_dir=str(self.meta.output_dir))
            else:
                self._print_step("Update PARAM", "No changes (or human-in-the-loop)")

            # Record state
            state = IterationState(
                iteration=i,
                param_snapshot=param_content.copy(),
                loss_result=loss_result.copy(),
                param_updates=updates,
                timestamp=ts,
            )
            result.iterations.append(state)

        if not result.converged:
            result.stopping_reason = f"Max iterations ({self.meta.max_iterations}) reached"
            result.final_loss = result.iterations[-1].loss_result if result.iterations else {}

        # Save trace
        result.save(self.output_dir)
        self._print_section("Done", f"Saved trace to {self.output_dir}/optimization_trace.md")

        self.result = result
        return result

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _apply_updates(self, current: dict, updates: dict) -> dict:
        """Apply PARAM updates and return new content dict."""
        new_content = current.copy()
        for fname, new_text in updates.items():
            new_content[fname] = new_text
        return new_content

    def _check_stop(self, loss_result: dict, iteration: int) -> tuple[bool, str]:
        """Check if stop condition is met."""
        if not loss_result:
            return False, ""
        if self.meta.stop_if:
            # Simple expression: "loss.mse < 0.01"
            import re
            m = re.match(r"loss\.(\w+)\s*(<|<=|>|>=)\s*([\d.]+)", self.meta.stop_if.strip())
            if m:
                metric, op, threshold = m.group(1), m.group(2), float(m.group(3))
                val = loss_result.get(metric)
                if val is not None:
                    if op == "<" and val < threshold:
                        return True, f"loss.{metric} = {val} < {threshold}"
                    if op == "<=" and val <= threshold:
                        return True, f"loss.{metric} = {val} <= {threshold}"
                    if op == ">" and val > threshold:
                        return True, f"loss.{metric} = {val} > {threshold}"
                    if op == ">=" and val >= threshold:
                        return True, f"loss.{metric} = {val} >= {threshold}"
        return False, ""

    # ── Formatting Helpers ───────────────────────────────────────────────────

    def _print_banner(self):
        if not self.verbose:
            return
        print("=" * 60)
        print(f"  DAN — {self.meta.name or self.task_dir.name}")
        print("=" * 60)

    def _print_meta(self):
        if not self.verbose:
            return
        print(f"\n📋 META: {self.meta.description or self.meta.name}")
        print(f"   max_iterations: {self.meta.max_iterations}")
        print(f"   output_dir: {self.meta.output_dir}")

    def _print_section(self, title: str, content: str):
        if not self.verbose:
            return
        lines = content.strip().splitlines()
        print(f"\n{'─' * 40}")
        print(f"  {title}")
        print(f"{'─' * 40}")
        for line in lines[:20]:
            print(f"  {line.strip()}")
        if len(lines) > 20:
            print(f"  ... ({len(lines) - 20} more lines)")

    def _print_iteration_header(self, i: int, ts: str):
        if not self.verbose:
            return
        print(f"\n{'▓' * 60}")
        print(f"  Iteration {i}  [{ts}]")
        print(f"{'▓' * 60}")

    def _print_step(self, title: str, detail: str = ""):
        if not self.verbose:
            return
        print(f"  ⚙️  {title}" + (f" → {detail}" if detail else ""))

    def _print_loss_result(self, result: dict):
        if not self.verbose:
            return
        if not result:
            print("    (no metrics returned)")
            return
        for k, v in result.items():
            if isinstance(v, float):
                print(f"    {k}: {v:.4f}")
            else:
                print(f"    {k}: {v}")


# ── JSON Runner (for SSE streaming) ────────────────────────────────────────────

def _jl(event_type: str, **data):
    """Print a JSON Line to stdout for SSE streaming."""
    print(json.dumps({"type": event_type, **data}, ensure_ascii=False), flush=True)


class JSONRunner(Runner):
    """
    JSON-line output runner for SSE/web streaming.
    Every event is printed as a separate JSON Line.
    """
    def run(self) -> OptimizationResult:
        strategy = self.heuristic.get_strategy()
        evaluator = self.loss.get_evaluator()
        param_content = self.param.load()

        if not param_content:
            _jl("error", text="PARAM directory is empty")
            return OptimizationResult(meta=self.meta)

        _jl("banner", name=self.meta.name or self.task_dir.name)
        _jl("meta", description=self.meta.description,
            max_iterations=self.meta.max_iterations,
            output_dir=self.meta.output_dir)

        loss_desc = self.loss.get_description()
        if loss_desc:
            _jl("loss_desc", text=loss_desc)

        heuristic_rules = self.heuristic.get_human_rules()
        if heuristic_rules:
            _jl("heuristic", text=heuristic_rules)

        result = OptimizationResult(meta=self.meta)

        for i in range(1, self.meta.max_iterations + 1):
            _jl("iteration_start", iteration=i)
            loss_result = evaluator.evaluate(param_content, self.task_dir)
            _jl("loss", metrics=loss_result)

            stop, reason = self._check_stop(loss_result, i)
            if stop:
                _jl("stop", reason=reason, converged=True)
                result.converged = True
                result.stopping_reason = reason
                result.final_loss = loss_result
                break

            strategy_type = type(strategy).__name__
            if isinstance(strategy, (PythonHeuristicStrategy, YAMLHeuristicStrategy)):
                updates = strategy.decide(i, param_content, loss_result)
            elif isinstance(strategy, MarkdownHeuristicStrategy):
                updates = {}
                _jl("heuristic", strategy=strategy_type, note="human_in_the_loop")
            else:
                updates = {}

            if updates:
                _jl("param_update", files=list(updates.keys()))
                param_content = self._apply_updates(param_content, updates)
                self.param.save(param_content, output_dir=str(self.meta.output_dir))
            else:
                _jl("param_update", files=[], note="no_changes_or_human_loop")

            result.iterations.append(IterationState(
                iteration=i,
                param_snapshot=param_content.copy(),
                loss_result=loss_result.copy(),
                param_updates=updates,
            ))

        if not result.converged:
            result.stopping_reason = f"Max iterations ({self.meta.max_iterations}) reached"
            result.final_loss = result.iterations[-1].loss_result if result.iterations else {}

        _jl("done", reason=result.stopping_reason, iterations=len(result.iterations))
        result.save(self.output_dir)

        self.result = result
        return result
