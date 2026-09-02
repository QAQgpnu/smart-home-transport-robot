from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import default_scenario
from .planner import simulate_navigation
from .render import render_svg, write_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic navigation reconstruction demo.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    args = parser.parse_args()
    root = args.root.resolve()
    result = simulate_navigation(default_scenario())
    write_data(result, root / "artifacts", root / "docs")
    render_svg(result, root / "figures" / "navigation-overview.svg")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))
    return 0 if result["metrics"]["reached_goal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
