from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.scientific.models import ScientificSuiteConfig


def load_suite_config(path: str | Path) -> ScientificSuiteConfig:
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Scientific suite config not found: {config_path}")

    suffix = config_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml_payload(config_path)
    else:
        raise ValueError(f"Unsupported suite config format '{suffix}'. Use .json, .yaml or .yml")

    return ScientificSuiteConfig.model_validate(payload)


def _load_yaml_payload(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "YAML config support requires PyYAML. Install it or use a JSON config."
        ) from exc

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping at root of suite config: {path}")
    return payload

