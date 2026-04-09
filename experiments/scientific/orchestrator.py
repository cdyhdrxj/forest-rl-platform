from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.api.dispatcher import ExperimentDispatcher
from experiments.scientific.models import (
    ScientificMethodConfig,
    ScientificScenarioConfig,
    ScientificSuiteConfig,
)
from experiments.scientific.report_builder import build_suite_report
from packages.db.models.artifact import Artifact
from packages.db.models.experiment_suite import ExperimentSuite
from packages.db.models.experiment_suite_run import ExperimentSuiteRun
from packages.db.models.model import Model
from packages.db.models.user import User
from packages.db.models.enums import ArtifactType
from packages.db.session import db_session
from services.agrocare_coverage.families import normalize_coverage_family, resolve_coverage_family_params


@dataclass(frozen=True, slots=True)
class PreparedScenario:
    family: str
    split: str
    scenario_seed: int
    generation_params: dict[str, Any]
    evaluation_params: dict[str, Any]
    scenario_index: int
    item_index: int


@dataclass(frozen=True, slots=True)
class SuiteRunHandle:
    run_id: int
    scenario_family: str
    dataset_split: str
    method_code: str
    replicate_index: int
    role: str
    train_seed: int
    eval_seed: int
    group_key: str


@dataclass(frozen=True, slots=True)
class ExecutedRun:
    run_id: int
    scenario_version_id: int
    run_result: dict[str, Any]


class ExperimentSuiteOrchestrator:
    def __init__(
        self,
        dispatcher: ExperimentDispatcher | None = None,
        *,
        poll_interval: float = 0.1,
        per_run_timeout_sec: float = 300.0,
    ):
        self.dispatcher = dispatcher or ExperimentDispatcher(observer_poll_interval=min(poll_interval, 0.1))
        self.poll_interval = float(poll_interval)
        self.per_run_timeout_sec = float(per_run_timeout_sec)

    def run_suite(self, config: ScientificSuiteConfig) -> dict[str, Any]:
        suite_id = self._create_suite(config)
        repo_root = Path(__file__).resolve().parents[2]
        report_dir = config.resolve_report_root(repo_root)

        self._update_suite_status(suite_id, status="running", started_at=datetime.utcnow())
        try:
            self._execute_suite(suite_id, config, report_dir)
            finished_at = datetime.utcnow()
            report = build_suite_report(
                suite_id,
                config,
                report_dir,
                suite_status="finished",
                suite_finished_at=finished_at,
            )
            self._update_suite_status(
                suite_id,
                status="finished",
                finished_at=finished_at,
                summary_json=report.get("summary"),
                manifest_uri=report.get("manifest_path"),
            )
            return {
                "suite_id": int(suite_id),
                "suite_code": config.suite_code,
                "status": "finished",
                **report,
            }
        except Exception as exc:
            self._update_suite_status(
                suite_id,
                status="failed",
                finished_at=datetime.utcnow(),
                summary_json={"error": str(exc)},
            )
            raise

    def _execute_suite(self, suite_id: int, config: ScientificSuiteConfig, report_dir: Path) -> None:
        prepared = self._materialize_scenarios(config)
        enabled_methods = [method for method in config.methods if method.enabled]

        for method_index, method in enumerate(enabled_methods):
            if self._is_baseline_method(method):
                self._execute_independent_method(
                    suite_id=suite_id,
                    config=config,
                    method=method,
                    method_index=method_index,
                    prepared_scenarios=prepared,
                )
                continue
            self._execute_rl_method(
                suite_id=suite_id,
                config=config,
                method=method,
                method_index=method_index,
                prepared_scenarios=prepared,
                report_dir=report_dir,
            )

    def _execute_independent_method(
        self,
        *,
        suite_id: int,
        config: ScientificSuiteConfig,
        method: ScientificMethodConfig,
        method_index: int,
        prepared_scenarios: list[PreparedScenario],
        role_override: str | None = None,
        protocol_phase: str | None = None,
    ) -> None:
        effective_role = str(role_override or method.effective_role or "eval")
        phase_name = protocol_phase or ("baseline_eval" if effective_role == "baseline" else f"standalone_{effective_role}")
        for prepared in prepared_scenarios:
            for replicate_index in range(1, method.effective_repeats + 1):
                train_seed, eval_seed = self._compute_run_seeds(
                    scenario_seed=prepared.scenario_seed,
                    method_index=method_index,
                    replicate_index=replicate_index,
                    phase_nonce=0,
                )
                start_params = self._build_start_params(
                    evaluation_params=prepared.evaluation_params,
                    method=method,
                    train_seed=train_seed,
                    eval_seed=eval_seed,
                    overrides={
                        "execution_role": effective_role,
                        "protocol_phase": phase_name,
                    },
                )
                executed = self._run_generated_scenario(
                    config.route_key,
                    prepared.generation_params,
                    start_params,
                )
                handle = self._build_suite_run_handle(
                    run_id=executed.run_id,
                    scenario_family=prepared.family,
                    dataset_split=prepared.split,
                    method=method,
                    replicate_index=replicate_index,
                    role=effective_role,
                    train_seed=train_seed,
                    eval_seed=eval_seed,
                    group_key=self._build_group_key(
                        family=prepared.family,
                        split=prepared.split,
                        role=effective_role,
                        method_code=method.code,
                        replicate_index=replicate_index,
                        scenario_seed=prepared.scenario_seed,
                        phase_nonce=0,
                    ),
                )
                self._attach_suite_run(suite_id, handle)

    def _execute_rl_method(
        self,
        *,
        suite_id: int,
        config: ScientificSuiteConfig,
        method: ScientificMethodConfig,
        method_index: int,
        prepared_scenarios: list[PreparedScenario],
        report_dir: Path,
    ) -> None:
        by_family: dict[str, list[PreparedScenario]] = defaultdict(list)
        for item in prepared_scenarios:
            by_family[item.family].append(item)

        for family_index, family in enumerate(sorted(by_family.keys()), start=1):
            family_items = by_family[family]
            split_map: dict[str, list[PreparedScenario]] = defaultdict(list)
            for item in family_items:
                split_map[item.split].append(item)

            train_items = split_map.get("train", [])
            val_items = split_map.get("val", [])
            test_items = split_map.get("test", [])
            if method.kind != "rl" or not train_items:
                self._execute_independent_method(
                    suite_id=suite_id,
                    config=config,
                    method=method,
                    method_index=method_index,
                    prepared_scenarios=family_items,
                )
                continue

            for replicate_index in range(1, method.effective_repeats + 1):
                self._execute_rl_family_replicate(
                    suite_id=suite_id,
                    config=config,
                    method=method,
                    method_index=method_index,
                    family=family,
                    family_index=family_index,
                    replicate_index=replicate_index,
                    train_items=train_items,
                    val_items=val_items,
                    test_items=test_items,
                    report_dir=report_dir,
                )

    def _execute_rl_family_replicate(
        self,
        *,
        suite_id: int,
        config: ScientificSuiteConfig,
        method: ScientificMethodConfig,
        method_index: int,
        family: str,
        family_index: int,
        replicate_index: int,
        train_items: list[PreparedScenario],
        val_items: list[PreparedScenario],
        test_items: list[PreparedScenario],
        report_dir: Path,
    ) -> None:
        plan = self._build_rl_training_plan(method, len(train_items))
        current_checkpoint: str | None = None
        best_checkpoint: str | None = None
        best_score: float | None = None
        best_source_train_run_id: int | None = None
        last_train_run_id: int | None = None
        validation_round = 0
        no_improvement_rounds = 0

        for train_position, item in enumerate(train_items, start=1):
            checkpoint_path = self._checkpoint_path(
                report_dir=report_dir,
                family=family,
                method_code=method.code,
                replicate_index=replicate_index,
                train_position=train_position,
            )
            train_seed, eval_seed = self._compute_run_seeds(
                scenario_seed=item.scenario_seed,
                method_index=method_index,
                replicate_index=replicate_index,
                phase_nonce=train_position + family_index * 100,
            )
            start_params = self._build_start_params(
                evaluation_params=item.evaluation_params,
                method=method,
                train_seed=train_seed,
                eval_seed=eval_seed,
                overrides={
                    "execution_role": "train",
                    "protocol_phase": "train",
                    "total_timesteps": plan["timesteps_per_train_run"],
                    "load_checkpoint_path": current_checkpoint,
                    "save_checkpoint_path": str(checkpoint_path),
                    "reset_num_timesteps": train_position == 1,
                    "deterministic": False,
                    "suite_family": family,
                    "suite_replicate": replicate_index,
                },
            )
            executed = self._run_generated_scenario(config.route_key, item.generation_params, start_params)
            last_train_run_id = executed.run_id
            self._attach_suite_run(
                suite_id,
                self._build_suite_run_handle(
                    run_id=executed.run_id,
                    scenario_family=family,
                    dataset_split="train",
                    method=method,
                    replicate_index=replicate_index,
                    role="train",
                    train_seed=train_seed,
                    eval_seed=eval_seed,
                    group_key=self._build_group_key(
                        family=family,
                        split="train",
                        role="train",
                        method_code=method.code,
                        replicate_index=replicate_index,
                        scenario_seed=item.scenario_seed,
                        phase_nonce=train_position,
                    ),
                ),
            )

            checkpoint_saved = checkpoint_path if checkpoint_path.exists() else None
            if checkpoint_saved is not None:
                current_checkpoint = str(checkpoint_saved)
                self._register_checkpoint_artifact(
                    run_id=executed.run_id,
                    checkpoint_path=checkpoint_saved,
                    checkpoint_epoch=train_position,
                    is_best=False,
                    metrics_json={
                        "coverage_ratio_mean": executed.run_result.get("coverage_ratio_mean"),
                        "episode_reward_mean": executed.run_result.get("episode_reward_mean"),
                        "episode_success_rate": executed.run_result.get("episode_success_rate"),
                    },
                )

            should_validate = bool(val_items) and (
                train_position % plan["validation_interval_runs"] == 0
                or train_position == len(train_items)
            )
            if current_checkpoint is not None and should_validate:
                validation_round += 1
                validation_score = self._evaluate_checkpoint_on_split(
                    suite_id=suite_id,
                    config=config,
                    method=method,
                    method_index=method_index,
                    family=family,
                    replicate_index=replicate_index,
                    split="val",
                    items=val_items,
                    checkpoint_path=current_checkpoint,
                    source_train_run_id=executed.run_id,
                    validation_round=validation_round,
                )
                if self._is_better_score(validation_score, best_score):
                    best_score = validation_score
                    best_checkpoint = current_checkpoint
                    best_source_train_run_id = executed.run_id
                    no_improvement_rounds = 0
                    self._mark_best_checkpoint(
                        run_id=executed.run_id,
                        checkpoint_path=Path(current_checkpoint),
                        selection_score=validation_score,
                    )
                else:
                    no_improvement_rounds += 1

                patience = int(plan["early_stop_patience"] or 0)
                if patience > 0 and no_improvement_rounds >= patience:
                    break

        selected_checkpoint = best_checkpoint or current_checkpoint
        selected_source_run_id = best_source_train_run_id or last_train_run_id
        if selected_checkpoint is None:
            raise RuntimeError(
                f"RL method '{method.code}' did not produce any checkpoint for family '{family}' replicate {replicate_index}"
            )

        if test_items:
            self._evaluate_checkpoint_on_split(
                suite_id=suite_id,
                config=config,
                method=method,
                method_index=method_index,
                family=family,
                replicate_index=replicate_index,
                split="test",
                items=test_items,
                checkpoint_path=selected_checkpoint,
                source_train_run_id=selected_source_run_id,
                validation_round=validation_round + 1,
            )

    def _evaluate_checkpoint_on_split(
        self,
        *,
        suite_id: int,
        config: ScientificSuiteConfig,
        method: ScientificMethodConfig,
        method_index: int,
        family: str,
        replicate_index: int,
        split: str,
        items: list[PreparedScenario],
        checkpoint_path: str,
        source_train_run_id: int | None,
        validation_round: int,
    ) -> float | None:
        scores: list[float] = []
        for item_position, item in enumerate(items, start=1):
            train_seed, eval_seed = self._compute_run_seeds(
                scenario_seed=item.scenario_seed,
                method_index=method_index,
                replicate_index=replicate_index,
                phase_nonce=validation_round * 1_000 + item_position,
            )
            start_params = self._build_start_params(
                evaluation_params=item.evaluation_params,
                method=method,
                train_seed=train_seed,
                eval_seed=eval_seed,
                overrides={
                    "execution_role": "eval",
                    "protocol_phase": f"{split}_eval",
                    "deterministic": bool(method.evaluation.get("deterministic", True)),
                    "eval_episodes": int(method.evaluation.get("eval_episodes") or 1),
                    "load_checkpoint_path": checkpoint_path,
                    "source_train_run_id": source_train_run_id,
                    "selection_metric": method.evaluation.get("selection_metric", "coverage_ratio_mean"),
                    "selection_mode": method.evaluation.get("selection_mode", "max"),
                    "suite_family": family,
                    "suite_replicate": replicate_index,
                },
            )
            executed = self._run_generated_scenario(config.route_key, item.generation_params, start_params)
            self._attach_suite_run(
                suite_id,
                self._build_suite_run_handle(
                    run_id=executed.run_id,
                    scenario_family=family,
                    dataset_split=split,
                    method=method,
                    replicate_index=replicate_index,
                    role="eval",
                    train_seed=train_seed,
                    eval_seed=eval_seed,
                    group_key=self._build_group_key(
                        family=family,
                        split=split,
                        role="eval",
                        method_code=method.code,
                        replicate_index=replicate_index,
                        scenario_seed=item.scenario_seed,
                        phase_nonce=validation_round * 1_000 + item_position,
                    ),
                ),
            )
            score = self._score_run_result(
                executed.run_result,
                metric=str(method.evaluation.get("selection_metric", "coverage_ratio_mean")),
                mode=str(method.evaluation.get("selection_mode", "max")),
            )
            if score is not None:
                scores.append(score)

        if not scores:
            return None
        return sum(scores) / len(scores)

    def _run_generated_scenario(
        self,
        route_key: str,
        generation_params: dict[str, Any],
        start_params: dict[str, Any],
    ) -> ExecutedRun:
        session = self.dispatcher.generate_and_load(route_key, generation_params)
        try:
            self.dispatcher.start_run(session.run_id, start_params)
            self.dispatcher.wait_run(
                session.run_id,
                poll_interval=self.poll_interval,
                timeout_sec=self.per_run_timeout_sec,
            )
            self.dispatcher.export_run_bundle(session.run_id)
            run_result = self.dispatcher.get_run_result(session.run_id)
            return ExecutedRun(
                run_id=int(session.run_id),
                scenario_version_id=int(session.scenario_version_id),
                run_result=run_result,
            )
        finally:
            self.dispatcher.dispose_run(session.run_id)

    def _build_start_params(
        self,
        *,
        evaluation_params: dict[str, Any],
        method: ScientificMethodConfig,
        train_seed: int,
        eval_seed: int,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = dict(evaluation_params)
        params.update(method.effective_start_params)
        params.update(dict(overrides or {}))
        params["algorithm"] = method.effective_algorithm
        params.setdefault("seed", train_seed)
        params.setdefault("train_seed", train_seed)
        params.setdefault("eval_seed", eval_seed)
        return params

    def _materialize_scenarios(self, config: ScientificSuiteConfig) -> list[PreparedScenario]:
        prepared: list[PreparedScenario] = []
        expanded_scenarios = config.expanded_scenarios()
        for scenario_index, scenario in enumerate(expanded_scenarios):
            base_seed = self._scenario_seed_base(config, scenario_index, scenario)
            for item_index in range(scenario.effective_count):
                scenario_seed = base_seed + item_index
                prepared.append(
                    PreparedScenario(
                        family=scenario.family,
                        split=scenario.effective_split,
                        scenario_seed=scenario_seed,
                        generation_params=self._build_generation_params(
                            config=config,
                            scenario=scenario,
                            scenario_seed=scenario_seed,
                        ),
                        evaluation_params=dict(scenario.evaluation_params),
                        scenario_index=scenario_index,
                        item_index=item_index,
                    )
                )
        return prepared

    @staticmethod
    def _is_baseline_method(method: ScientificMethodConfig) -> bool:
        if method.kind == "baseline":
            return True
        return method.effective_algorithm in {"greedy_nearest", "greedy_two_step"}

    @staticmethod
    def _build_rl_training_plan(method: ScientificMethodConfig, train_item_count: int) -> dict[str, int]:
        total_timesteps = max(1, int(method.training.get("total_timesteps") or 10_000))
        timesteps_per_train_run = max(1, int(math.ceil(total_timesteps / max(1, train_item_count))))
        eval_every_steps = method.training.get("eval_every_steps")
        if eval_every_steps is None:
            validation_interval_runs = 1
        else:
            validation_interval_runs = max(1, int(math.ceil(int(eval_every_steps) / timesteps_per_train_run)))
        return {
            "timesteps_per_train_run": timesteps_per_train_run,
            "validation_interval_runs": validation_interval_runs,
            "early_stop_patience": max(0, int(method.training.get("early_stop_patience") or 0)),
        }

    @staticmethod
    def _compute_run_seeds(
        *,
        scenario_seed: int,
        method_index: int,
        replicate_index: int,
        phase_nonce: int,
    ) -> tuple[int, int]:
        train_seed = int(scenario_seed) * 10_000 + int(method_index) * 100 + int(replicate_index) * 10 + int(phase_nonce)
        eval_seed = train_seed + 1_000_000
        return train_seed, eval_seed

    @staticmethod
    def _score_run_result(run_result: dict[str, Any], *, metric: str, mode: str) -> float | None:
        raw_value = run_result.get(metric)
        if raw_value is None and metric == "coverage_ratio_mean":
            raw_value = run_result.get("coverage_ratio_mean")
        if raw_value is None and metric == "success":
            raw_value = run_result.get("success")
        if raw_value is None:
            return None
        try:
            numeric = float(bool(raw_value)) if isinstance(raw_value, bool) else float(raw_value)
        except (TypeError, ValueError):
            return None
        if str(mode).lower() == "min":
            return -numeric
        return numeric

    @staticmethod
    def _is_better_score(candidate: float | None, current: float | None) -> bool:
        if candidate is None:
            return False
        if current is None:
            return True
        return candidate > current

    @staticmethod
    def _checkpoint_path(
        *,
        report_dir: Path,
        family: str,
        method_code: str,
        replicate_index: int,
        train_position: int,
    ) -> Path:
        checkpoint_dir = (
            report_dir
            / "checkpoints"
            / normalize_coverage_family(family)
            / method_code
            / f"replicate_{replicate_index}"
        )
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir / f"train_step_{train_position:04d}.zip"

    @staticmethod
    def _build_group_key(
        *,
        family: str,
        split: str,
        role: str,
        method_code: str,
        replicate_index: int,
        scenario_seed: int,
        phase_nonce: int,
    ) -> str:
        return (
            f"{normalize_coverage_family(family)}:{split}:{role}:{method_code}:"
            f"r{replicate_index}:seed{scenario_seed}:p{phase_nonce}"
        )

    @staticmethod
    def _build_suite_run_handle(
        *,
        run_id: int,
        scenario_family: str,
        dataset_split: str,
        method: ScientificMethodConfig,
        replicate_index: int,
        role: str,
        train_seed: int,
        eval_seed: int,
        group_key: str,
    ) -> SuiteRunHandle:
        return SuiteRunHandle(
            run_id=int(run_id),
            scenario_family=normalize_coverage_family(scenario_family),
            dataset_split=str(dataset_split),
            method_code=method.code,
            replicate_index=int(replicate_index),
            role=str(role),
            train_seed=int(train_seed),
            eval_seed=int(eval_seed),
            group_key=group_key,
        )

    @staticmethod
    def _scenario_seed_base(
        config: ScientificSuiteConfig,
        scenario_index: int,
        scenario: ScientificScenarioConfig,
    ) -> int:
        if scenario.seed_start is not None:
            return int(scenario.seed_start)
        return int(config.seed) + scenario_index * 10_000

    @staticmethod
    def _build_generation_params(
        *,
        config: ScientificSuiteConfig,
        scenario: ScientificScenarioConfig,
        scenario_seed: int,
    ) -> dict[str, Any]:
        params = dict(scenario.generation_params)
        if config.route_key == "continuous/coverage":
            params = resolve_coverage_family_params(scenario.family, params)
        params.setdefault("family", normalize_coverage_family(scenario.family))
        params.setdefault("split", scenario.effective_split)
        params.setdefault("seed", scenario_seed)
        return params

    def _register_checkpoint_artifact(
        self,
        *,
        run_id: int,
        checkpoint_path: Path,
        checkpoint_epoch: int,
        is_best: bool,
        metrics_json: dict[str, Any] | None = None,
    ) -> None:
        if not checkpoint_path.exists():
            return

        with db_session() as db:
            model = (
                db.query(Model)
                .filter(Model.run_id == int(run_id), Model.storage_uri == str(checkpoint_path))
                .first()
            )
            if model is None:
                model = Model(
                    run_id=int(run_id),
                    name=checkpoint_path.name,
                    framework="stable_baselines3",
                    storage_uri=str(checkpoint_path),
                    checkpoint_epoch=int(checkpoint_epoch),
                    is_best=bool(is_best),
                    metrics_json=dict(metrics_json or {}) or None,
                )
                db.add(model)
                db.flush()
            else:
                model.checkpoint_epoch = int(checkpoint_epoch)
                model.is_best = bool(is_best)
                model.metrics_json = dict(metrics_json or {}) or None

            artifact = (
                db.query(Artifact)
                .filter(Artifact.run_id == int(run_id), Artifact.storage_uri == str(checkpoint_path))
                .first()
            )
            if artifact is None:
                db.add(
                    Artifact(
                        run_id=int(run_id),
                        model_id=int(model.id),
                        artifact_type=ArtifactType.model_checkpoint,
                        name=checkpoint_path.name,
                        storage_uri=str(checkpoint_path),
                        mime_type="application/zip",
                        size_bytes=checkpoint_path.stat().st_size,
                    )
                )
            else:
                artifact.model_id = int(model.id)
                artifact.artifact_type = ArtifactType.model_checkpoint
                artifact.name = checkpoint_path.name
                artifact.mime_type = "application/zip"
                artifact.size_bytes = checkpoint_path.stat().st_size

    def _mark_best_checkpoint(
        self,
        *,
        run_id: int,
        checkpoint_path: Path,
        selection_score: float | None,
    ) -> None:
        if not checkpoint_path.exists():
            return
        with db_session() as db:
            model = (
                db.query(Model)
                .filter(Model.run_id == int(run_id), Model.storage_uri == str(checkpoint_path))
                .first()
            )
            if model is None:
                self._register_checkpoint_artifact(
                    run_id=run_id,
                    checkpoint_path=checkpoint_path,
                    checkpoint_epoch=0,
                    is_best=True,
                    metrics_json={"validation_score": selection_score},
                )
                return
            model.is_best = True
            metrics = dict(model.metrics_json or {})
            metrics["validation_score"] = selection_score
            model.metrics_json = metrics

    def _create_suite(self, config: ScientificSuiteConfig) -> int:
        route = self.dispatcher.routes.get(config.route_key)
        if route is None:
            raise KeyError(f"Unsupported route '{config.route_key}'")

        with db_session() as db:
            user = self._ensure_system_user(db)
            suite = ExperimentSuite(
                code=config.suite_code,
                title=config.title,
                route_key=config.route_key,
                mode=route.project_mode.value,
                status="created",
                config_json=config.model_dump(mode="json"),
                created_by_user_id=int(user.id),
            )
            db.add(suite)
            db.flush()
            return int(suite.id)

    def _attach_suite_run(self, suite_id: int, handle: SuiteRunHandle) -> None:
        with db_session() as db:
            db.add(
                ExperimentSuiteRun(
                    suite_id=int(suite_id),
                    run_id=int(handle.run_id),
                    scenario_family=handle.scenario_family,
                    dataset_split=handle.dataset_split,
                    method_code=handle.method_code,
                    replicate_index=handle.replicate_index,
                    role=handle.role,
                    train_seed=handle.train_seed,
                    eval_seed=handle.eval_seed,
                    group_key=handle.group_key,
                )
            )

    def _update_suite_status(
        self,
        suite_id: int,
        *,
        status: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        summary_json: dict[str, Any] | None = None,
        manifest_uri: str | None = None,
    ) -> None:
        with db_session() as db:
            suite = db.query(ExperimentSuite).filter(ExperimentSuite.id == int(suite_id)).first()
            if suite is None:
                return
            suite.status = status
            if started_at is not None or status == "created":
                suite.started_at = started_at
            if finished_at is not None or status == "created":
                suite.finished_at = finished_at
            if summary_json is not None:
                suite.summary_json = summary_json
            if manifest_uri is not None:
                suite.manifest_uri = manifest_uri

    @staticmethod
    def _ensure_system_user(db) -> User:
        user = db.query(User).filter(User.email == "system@forest.local").first()
        if user is None:
            user = User(full_name="System Dispatcher", email="system@forest.local", role="system")
            db.add(user)
            db.flush()
        return user
