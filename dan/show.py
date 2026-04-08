"""
DAN Show — Display task context for LLM agents

Usage:
    python -m dan.show demo/02_CodeOptimize/02_loss3
"""

import sys
from pathlib import Path


def show_task(task_dir: str | Path):
    from dan.core import META, HEURISTIC, PARAM, LOSS

    task_dir = Path(task_dir)

    print("=" * 60)
    print(f"  DAN Task: {task_dir}")
    print("=" * 60)

    # META
    try:
        meta = META.load(task_dir / "META")
        print(f"\n📋 META")
        print(f"   name: {meta.name}")
        print(f"   description: {meta.description}")
        print(f"   max_iterations: {meta.max_iterations}")
        print(f"   output_dir: {meta.output_dir}")
        if meta.stop_if:
            print(f"   stop_if: {meta.stop_if}")
    except Exception as e:
        print(f"\n⚠️  META: {e}")

    # LOSS
    try:
        loss = LOSS(root=task_dir / "LOSS")
        desc = loss.get_description()
        items = loss.load()
        print(f"\n🎯 LOSS")
        if desc:
            for line in desc.strip().splitlines()[:10]:
                print(f"   {line.strip()}")
        print(f"   resources: {[i['name'] + i['type'] for i in items]}")
        evaluator = loss.get_evaluator()
        print(f"   evaluator: {type(evaluator).__name__}")
    except Exception as e:
        print(f"\n⚠️  LOSS: {e}")

    # HEURISTIC
    try:
        heuristic = HEURISTIC(root=task_dir / "HEURISTIC")
        rules = heuristic.load()
        rules_text = heuristic.get_human_rules()
        print(f"\n🧠 HEURISTIC")
        print(f"   files: {[r['name'] + r['type'] for r in rules]}")
        strategy = heuristic.get_strategy()
        print(f"   strategy: {type(strategy).__name__}")
        if rules_text:
            print(f"   rules preview:")
            for line in rules_text.strip().splitlines()[:15]:
                print(f"      {line.strip()}")
    except Exception as e:
        print(f"\n⚠️  HEURISTIC: {e}")

    # PARAM
    try:
        param = PARAM(root=task_dir / "PARAM")
        content = param.load()
        print(f"\n⚙️  PARAM")
        print(f"   files: {list(content.keys())}")
        total_chars = sum(len(v) for v in content.values())
        print(f"   total: {total_chars} chars")
        for fname, ftext in content.items():
            lines = ftext.strip().splitlines()
            print(f"\n   --- {fname} ({len(lines)} lines) ---")
            for line in lines[:20]:
                print(f"   {line}")
            if len(lines) > 20:
                print(f"   ... ({len(lines)-20} more lines)")
    except Exception as e:
        print(f"\n⚠️  PARAM: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m dan.show <task_dir>")
        sys.exit(1)
    show_task(sys.argv[1])
