from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.api.run_render import render_run_svg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render offline trajectory for a completed run")
    parser.add_argument("--run-id", type=int, required=True, help="Run identifier")
    parser.add_argument("--output-dir", help="Optional output directory for trajectory.svg")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    output_path = render_run_svg(args.run_id, output_dir=output_dir)
    print(json.dumps({"run_id": args.run_id, "trajectory_path": str(output_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

