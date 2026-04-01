from __future__ import annotations

import argparse
import json

from experiments.scientific.orchestrator import ExperimentSuiteOrchestrator
from experiments.scientific.suite_loader import load_suite_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a headless scientific experiment suite")
    parser.add_argument("--config", required=True, help="Path to the scientific suite config (.json/.yaml)")
    parser.add_argument("--timeout-sec", type=float, default=300.0, help="Per-run timeout in seconds")
    parser.add_argument("--poll-interval", type=float, default=0.1, help="Polling interval in seconds")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_suite_config(args.config)
    orchestrator = ExperimentSuiteOrchestrator(
        poll_interval=args.poll_interval,
        per_run_timeout_sec=args.timeout_sec,
    )
    result = orchestrator.run_suite(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

