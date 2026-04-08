"""
DAN CLI Entry Point

Usage:
    python -m dan demo/02_CodeOptimize/02_loss3
    python -m dan demo/01_LinearFunFit
"""

import sys
import argparse
from pathlib import Path

from dan.runner import Runner


def main():
    parser = argparse.ArgumentParser(description="DAN — Deep Agent Network Runner")
    parser.add_argument("task_dir", help="Path to the task demo directory")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress verbose output")
    parser.add_argument("--max-iter", type=int, default=None, help="Override max_iterations from META")
    args = parser.parse_args()

    task_path = Path(args.task_dir).resolve()
    if not task_path.exists():
        print(f"Error: Task directory not found: {task_path}")
        sys.exit(1)

    runner = Runner(task_path, verbose=not args.quiet)
    if args.max_iter is not None:
        runner.meta.max_iterations = args.max_iter

    result = runner.run()
    print(f"\n✅ Optimization complete. Reason: {result.stopping_reason}")


if __name__ == "__main__":
    main()
