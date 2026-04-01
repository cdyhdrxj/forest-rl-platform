from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ScientificScenarioConfig(BaseModel):
    family: str = Field(..., min_length=1)
    split: str = Field(default="test", min_length=1)
    count: int = Field(default=1, ge=1)
    seed_start: int | None = None
    generation_params: dict[str, Any] = Field(default_factory=dict)
    evaluation_params: dict[str, Any] = Field(default_factory=dict)


class ScientificMethodConfig(BaseModel):
    code: str = Field(..., min_length=1)
    algorithm: str | None = None
    enabled: bool = True
    repeats: int = Field(default=1, ge=1)
    start_params: dict[str, Any] = Field(default_factory=dict)
    role: str = Field(default="eval", min_length=1)

    @property
    def effective_algorithm(self) -> str:
        return str(self.algorithm or self.code).lower()


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

