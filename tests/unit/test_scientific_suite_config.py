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
    expanded = config.expanded_scenarios()
    assert len(expanded) == 1
    assert expanded[0].effective_split == "test"
    assert expanded[0].effective_count == 1


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


def test_scientific_suite_config_expands_paper_style_split_bundle():
    config = load_suite_config(REPO_ROOT / "experiments" / "configs" / "scientific" / "agrocare_paper_v1.json")

    expanded = config.expanded_scenarios()
    methods = {method.code: method for method in config.methods}

    assert config.route_key == "continuous/coverage"
    assert [item.effective_split for item in expanded] == [
        "train",
        "val",
        "test",
        "train",
        "val",
        "test",
        "train",
        "val",
        "test",
        "train",
        "val",
        "test",
    ]
    assert expanded[0].effective_count == 300
    assert expanded[1].effective_count == 100
    assert expanded[2].effective_count == 150
    assert methods["greedy_nearest"].effective_role == "baseline"
    assert methods["greedy_nearest"].effective_repeats == 1
    assert methods["sac"].effective_repeats == 5
    assert methods["sac"].effective_start_params["total_timesteps"] == 500000
    assert methods["sac"].effective_start_params["deterministic"] is True
