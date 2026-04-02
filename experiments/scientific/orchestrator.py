from __future__ import annotations

from dataclasses import dataclass, replace
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
from packages.db.models.experiment_suite import ExperimentSuite
from packages.db.models.experiment_suite_run import ExperimentSuiteRun
from packages.db.models.user import User
from packages.db.session import db_session
from services.agrocare_coverage.families import normalize_coverage_family, resolve_coverage_family_params


@dataclass(frozen=True, slots=True)
class SuiteRunHandle:
    run_id: int
    scenario_version_id: int
    scenario_family: str
    dataset_split: str
    method_code: str
    replicate_index: int
    role: str
    train_seed: int
    eval_seed: int
    group_key: str


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
            self._execute_suite(suite_id, config)
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

    def _execute_suite(self, suite_id: int, config: ScientificSuiteConfig) -> None:
        enabled_methods = [method for method in config.methods if method.enabled]
        expanded_scenarios = config.expanded_scenarios()
        for scenario_index, scenario in enumerate(expanded_scenarios):
            base_seed = self._scenario_seed_base(config, scenario_index, scenario)
            for item_index in range(scenario.effective_count):
                scenario_seed = base_seed + item_index
                generation_params = self._build_generation_params(
                    config=config,
                    scenario=scenario,
                    scenario_seed=scenario_seed,
                )

                base_session = self.dispatcher.generate_and_load(config.route_key, generation_params)
                scenario_version_id = int(base_session.scenario_version_id)
                primary_consumed = False

                try:
                    for method_index, method in enumerate(enabled_methods):
                        for replicate_index in range(1, method.effective_repeats + 1):
                            handle = self._build_suite_run_handle(
                                scenario=scenario,
                                scenario_seed=scenario_seed,
                                scenario_version_id=scenario_version_id,
                                method=method,
                                method_index=method_index,
                                replicate_index=replicate_index,
                            )
                            start_params = self._build_start_params(
                                scenario=scenario,
                                method=method,
                                train_seed=handle.train_seed,
                                eval_seed=handle.eval_seed,
                            )

                            if not primary_consumed:
                                session = base_session
                                primary_consumed = True
                            else:
                                session = self.dispatcher.load_scenario_version(
                                    config.route_key,
                                    scenario_version_id,
                                    start_params,
                                )

                            try:
                                self.dispatcher.start_run(session.run_id, start_params)
                                self.dispatcher.wait_run(
                                    session.run_id,
                                    poll_interval=self.poll_interval,
                                    timeout_sec=self.per_run_timeout_sec,
                                )
                                self.dispatcher.export_run_bundle(session.run_id)
                                self._attach_suite_run(
                                    suite_id,
                                    replace(handle, run_id=int(session.run_id)),
                                )
                            finally:
                                self.dispatcher.dispose_run(session.run_id)
                finally:
                    if not primary_consumed:
                        self.dispatcher.dispose_run(base_session.run_id)

    def _build_start_params(
        self,
        *,
        scenario: ScientificScenarioConfig,
        method: ScientificMethodConfig,
        train_seed: int,
        eval_seed: int,
    ) -> dict[str, Any]:
        params = dict(scenario.evaluation_params)
        params.update(method.effective_start_params)
        params["algorithm"] = method.effective_algorithm
        params.setdefault("seed", train_seed)
        params.setdefault("train_seed", train_seed)
        params.setdefault("eval_seed", eval_seed)
        return params

    def _build_suite_run_handle(
        self,
        *,
        scenario: ScientificScenarioConfig,
        scenario_seed: int,
        scenario_version_id: int,
        method: ScientificMethodConfig,
        method_index: int,
        replicate_index: int,
    ) -> SuiteRunHandle:
        train_seed = scenario_seed * 100 + method_index * 10 + replicate_index
        eval_seed = train_seed + 1_000_000
        group_key = (
            f"{scenario.family}:{scenario.effective_split}:sv{scenario_version_id}:{method.code}:r{replicate_index}"
        )
        return SuiteRunHandle(
            run_id=0,
            scenario_version_id=scenario_version_id,
            scenario_family=scenario.family,
            dataset_split=scenario.effective_split,
            method_code=method.code,
            replicate_index=replicate_index,
            role=method.effective_role,
            train_seed=train_seed,
            eval_seed=eval_seed,
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
