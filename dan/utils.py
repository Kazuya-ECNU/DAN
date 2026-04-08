"""DAN shared utilities."""

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def print_header(text: str, width: int = 60):
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def print_step(text: str, detail: str = ""):
    indent = "  ⚙️  "
    print(indent + text + (f" → {detail}" if detail else ""))


def print_metric(key: str, value, precision: int = 4):
    if isinstance(value, float):
        print(f"    {key}: {value:.{precision}f}")
    else:
        print(f"    {key}: {value}")
