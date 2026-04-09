from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from services.agrocare_coverage.families import normalize_coverage_family


class ScientificScenarioConfig(BaseModel):
    family: str = Field(..., min_length=1)
    split: str | None = Field(default=None)
    count: int | None = Field(default=None, ge=1)
    train_count: int = Field(default=0, ge=0)
    val_count: int = Field(default=0, ge=0)
    test_count: int = Field(default=0, ge=0)
    seed_start: int | None = None
    generation_params: dict[str, Any] = Field(default_factory=dict)
    evaluation_params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("family")
    @classmethod
    def validate_family(cls, value: str) -> str:
        return normalize_coverage_family(value)

    @field_validator("split")
    @classmethod
    def validate_split(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        return normalized

    @model_validator(mode="after")
    def validate_shape(self) -> "ScientificScenarioConfig":
        split_bundle_total = int(self.train_count) + int(self.val_count) + int(self.test_count)
        if self.count is not None and split_bundle_total > 0:
            raise ValueError("Scenario config cannot define both count and train/val/test counts")
        if split_bundle_total > 0 and self.split is not None:
            raise ValueError("Scenario config with train/val/test counts must not define split")
        return self

    @property
    def is_split_bundle(self) -> bool:
        return (int(self.train_count) + int(self.val_count) + int(self.test_count)) > 0

    @property
    def effective_split(self) -> str:
        return str(self.split or "test")

    @property
    def effective_count(self) -> int:
        return int(self.count or 1)

    def expand(self) -> list["ScientificScenarioConfig"]:
        if not self.is_split_bundle:
            return [
                self.model_copy(
                    update={
                        "split": self.effective_split,
                        "count": self.effective_count,
                        "train_count": 0,
                        "val_count": 0,
                        "test_count": 0,
                    }
                )
            ]

        expanded: list[ScientificScenarioConfig] = []
        next_seed = self.seed_start
        for split_name, split_count in (
            ("train", int(self.train_count)),
            ("val", int(self.val_count)),
            ("test", int(self.test_count)),
        ):
            if split_count <= 0:
                continue
            expanded.append(
                self.model_copy(
                    update={
                        "split": split_name,
                        "count": split_count,
                        "train_count": 0,
                        "val_count": 0,
                        "test_count": 0,
                        "seed_start": next_seed,
                    }
                )
            )
            if next_seed is not None:
                next_seed += split_count
        return expanded


class ScientificMethodConfig(BaseModel):
    code: str = Field(..., min_length=1)
    algorithm: str | None = None
    kind: str | None = None
    enabled: bool = True
    repeats: int | None = Field(default=None, ge=1)
    start_params: dict[str, Any] = Field(default_factory=dict)
    training: dict[str, Any] = Field(default_factory=dict)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    role: str | None = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @property
    def effective_algorithm(self) -> str:
        return str(self.algorithm or self.code).lower()

    @property
    def effective_repeats(self) -> int:
        if self.repeats is not None:
            return int(self.repeats)
        training_repeats = self.training.get("repeats")
        if training_repeats is None:
            return 1
        return max(1, int(training_repeats))

    @property
    def effective_role(self) -> str:
        if self.role:
            return str(self.role)
        if self.kind == "baseline":
            return "baseline"
        return "eval"

    @property
    def effective_start_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        params.update({k: v for k, v in self.training.items() if k != "repeats"})
        params.update(dict(self.evaluation))
        params.update(dict(self.start_params))
        return params


class ScientificReportConfig(BaseModel):
    formats: list[str] = Field(default_factory=lambda: ["json", "csv", "html"])
    representative_runs_per_method: int = Field(default=1, ge=0)
    save_trajectory_plots: bool = True
    save_distribution_plots: bool = True

    @field_validator("formats")
    @classmethod
    def validate_formats(cls, value: list[str]) -> list[str]:
        allowed = {"json", "csv", "html"}
        normalized = [str(item).lower() for item in value]
        unsupported = sorted({item for item in normalized if item not in allowed})
        if unsupported:
            raise ValueError(f"Unsupported report formats: {', '.join(unsupported)}")
        return normalized


class ScientificSuiteConfig(BaseModel):
    suite_code: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    route_key: str = Field(..., min_length=1)
    task_kind: str | None = None
    environment_kind: str | None = None
    report_dir: str = "data/scientific/suites"
    seed: int = 0
    scenarios: list[ScientificScenarioConfig]
    methods: list[ScientificMethodConfig]
    report: ScientificReportConfig = Field(default_factory=ScientificReportConfig)

    @field_validator("suite_code")
    @classmethod
    def validate_suite_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("suite_code must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_non_empty(self) -> "ScientificSuiteConfig":
        if not self.scenarios:
            raise ValueError("Scientific suite must contain at least one scenario definition")
        if not any(method.enabled for method in self.methods):
            raise ValueError("Scientific suite must contain at least one enabled method")
        return self

    def resolve_report_root(self, repo_root: Path) -> Path:
        root = Path(self.report_dir)
        if not root.is_absolute():
            root = repo_root / root
        return root / self.suite_code

    def expanded_scenarios(self) -> list[ScientificScenarioConfig]:
        expanded: list[ScientificScenarioConfig] = []
        for scenario in self.scenarios:
            expanded.extend(scenario.expand())
        return expanded
