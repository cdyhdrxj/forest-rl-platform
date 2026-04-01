from __future__ import annotations

from pathlib import Path

import pytest

from experiments.scientific.suite_loader import load_suite_config


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scientific_suite_config_loads_json_sample():
    config = load_suite_config(REPO_ROOT / "experiments" / "configs" / "scientific" / "trail_smoke.json")

    assert config.suite_code == "trail-smoke-suite"
    assert config.route_key == "threed/trail"
    assert len(config.scenarios) == 1
    assert len(config.methods) == 1
    assert config.report.formats == ["json", "csv", "html"]


def test_scientific_suite_config_requires_enabled_method(tmp_path):
    path = tmp_path / "suite.json"
    path.write_text(
        """
        {
          "suite_code": "invalid-suite",
          "title": "Invalid suite",
          "route_key": "threed/trail",
          "seed": 1,
          "scenarios": [{"family": "smoke"}],
          "methods": [{"code": "ppo", "enabled": false}],
          "report": {}
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_suite_config(path)

