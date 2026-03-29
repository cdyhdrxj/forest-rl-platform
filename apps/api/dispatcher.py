from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Any, Callable
import shutil

from sqlalchemy import func

from apps.api.runtime_monitor import RunObserver, write_service_log
from packages.db.models.algorithm import Algorithm
from packages.db.models.artifact import Artifact
from packages.db.models.project import Project
from packages.db.models.run import Run
from packages.db.models.scenario import Scenario
from packages.db.models.scenario_layer import ScenarioLayer
from packages.db.models.scenario_version import ScenarioVersion
from packages.db.models.user import User
from packages.db.models.enums import AlgorithmFamily, ArtifactType, ProjectMode, RunStatus
from packages.db.session import db_session
from services.patrol_planning.assets.envs.models import GridWorldConfig
from services.patrol_planning.service.service import GridWorldService
from services.reforestation_planting.models import PlantingEnvConfig
from services.reforestation_planting.service import SeedlingPlantingService
from services.scenario_generator import (
    apply_patrol_generation,
    build_continuous_trail_request,
    build_patrol_grid_request,
    build_reforestation_request,
    build_simulator_3d_request,
    extract_continuous_runtime_kwargs,
    extract_simulator_3d_runtime_config,
    get_default_environment_generation_service,
    merge_reports,
    validate_generation_request,
)
from services.scenario_generator.models import (
    EnvironmentKind,
    GeneratedScenario,
    GenerationRequest,
    TaskKind,
    ValidationReport,
)
from services.scenario_generator.storage import (
    StoredScenario,
    get_storage_root,
    load_stored_scenario,
    store_generated_scenario,
)
from services.scenario_generator.validation import report_for_runtime_validation
from services.simulator_3d import Simulator3DService
from services.trail_camar.service import CamarService


RuntimeServiceFactory = Callable[[], Any]
RequestBuilder = Callable[[dict[str, Any]], GenerationRequest]
RuntimeConfigBuilder = Callable[[dict[str, Any], GeneratedScenario], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class RuntimeRoute:
    route_key: str
    environment_kind: EnvironmentKind
    task_kind: TaskKind
    project_mode: ProjectMode
    training_mode: str
    service_factory: RuntimeServiceFactory
    request_builder: RequestBuilder
    runtime_config_builder: RuntimeConfigBuilder
    default_algorithm: str = "ppo"


@dataclass(slots=True)
class RunSession:
    run_id: int
    scenario_version_id: int
    route: RuntimeRoute
    stored_scenario: StoredScenario
    service: Any
    training_params: dict[str, Any]
    observer: RunObserver | None = None
    validation_report: dict[str, Any] | None = None
    last_error: str | None = None


def _build_patrol_request(params: dict[str, Any]) -> GenerationRequest:
    source = params.get("grid_world_config", params)
    return build_patrol_grid_request(GridWorldConfig.model_validate(source))


def _build_patrol_runtime_config(params: dict[str, Any], scenario: GeneratedScenario) -> dict[str, Any]:
    source = params.get("grid_world_config", params)
    config = GridWorldConfig.model_validate(source)
    config, _ = apply_patrol_generation(config, scenario)
    return config.model_dump(mode="json")


def _build_reforestation_request(params: dict[str, Any]) -> GenerationRequest:
    return build_reforestation_request(PlantingEnvConfig.model_validate(params))


def _build_reforestation_runtime_config(params: dict[str, Any], _: GeneratedScenario) -> dict[str, Any]:
    return PlantingEnvConfig.model_validate(params).model_dump(mode="json")


def _build_continuous_request(params: dict[str, Any]) -> GenerationRequest:
    return build_continuous_trail_request(params)


def _build_continuous_runtime_config(_: dict[str, Any], scenario: GeneratedScenario) -> dict[str, Any]:
    return extract_continuous_runtime_kwargs(scenario)


def _build_3d_trail_request(params: dict[str, Any]) -> GenerationRequest:
    return build_simulator_3d_request(params, task_kind=TaskKind.TRAIL)


def _build_3d_patrol_request(params: dict[str, Any]) -> GenerationRequest:
    return build_simulator_3d_request(params, task_kind=TaskKind.PATROL)


def _build_3d_runtime_config(_: dict[str, Any], scenario: GeneratedScenario) -> dict[str, Any]:
    return extract_simulator_3d_runtime_config(scenario)


def _algorithm_family_for_key(algorithm_key: str) -> AlgorithmFamily:
    return AlgorithmFamily.actor_critic


def _task_display_name(task_kind: TaskKind) -> str:
    if task_kind is TaskKind.REFORESTATION:
        return "Reforestation"
    return task_kind.value.capitalize()


DEFAULT_ROUTES: dict[str, RuntimeRoute] = {
    "continuous/trail": RuntimeRoute(
        route_key="continuous/trail",
        environment_kind=EnvironmentKind.CONTINUOUS_2D,
        task_kind=TaskKind.TRAIL,
        project_mode=ProjectMode.trail,
        training_mode="trail",
        service_factory=CamarService,
        request_builder=_build_continuous_request,
        runtime_config_builder=_build_continuous_runtime_config,
    ),
    "discrete/patrol": RuntimeRoute(
        route_key="discrete/patrol",
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.PATROL,
        project_mode=ProjectMode.patrol,
        training_mode="patrol",
        service_factory=GridWorldService,
        request_builder=_build_patrol_request,
        runtime_config_builder=_build_patrol_runtime_config,
    ),
    "discrete/reforestation": RuntimeRoute(
        route_key="discrete/reforestation",
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.REFORESTATION,
        project_mode=ProjectMode.reforestation,
        training_mode="reforestation",
        service_factory=SeedlingPlantingService,
        request_builder=_build_reforestation_request,
        runtime_config_builder=_build_reforestation_runtime_config,
    ),
    "threed/trail": RuntimeRoute(
        route_key="threed/trail",
        environment_kind=EnvironmentKind.SIMULATOR_3D,
        task_kind=TaskKind.TRAIL,
        project_mode=ProjectMode.trail,
        training_mode="trail",
        service_factory=Simulator3DService,
        request_builder=_build_3d_trail_request,
        runtime_config_builder=_build_3d_runtime_config,
    ),
    "threed/patrol": RuntimeRoute(
        route_key="threed/patrol",
        environment_kind=EnvironmentKind.SIMULATOR_3D,
        task_kind=TaskKind.PATROL,
        project_mode=ProjectMode.patrol,
        training_mode="patrol",
        service_factory=Simulator3DService,
        request_builder=_build_3d_patrol_request,
        runtime_config_builder=_build_3d_runtime_config,
    ),
}


class ExperimentDispatcher:
    def __init__(
        self,
        routes: dict[str, RuntimeRoute] | None = None,
        *,
        generation_service=None,
        observer_poll_interval: float = 0.25,
    ):
        self.routes = routes or DEFAULT_ROUTES
        self.generation_service = generation_service or get_default_environment_generation_service()
        self.observer_poll_interval = float(observer_poll_interval)
        self._sessions: dict[int, RunSession] = {}
        self._lock = RLock()

    def generate_and_load(self, route_key: str, params: dict[str, Any]) -> RunSession:
        route = self._get_route(route_key)
        request = route.request_builder(params)
        request_report = validate_generation_request(self.generation_service.registry, request)
        if not request_report.passed:
            raise ValueError(self._format_validation_error(request_report))

        scenario = self.generation_service.generate(request)
        runtime_config = route.runtime_config_builder(params, scenario)
        runtime_service = route.service_factory()
        runtime_report = self._validate_runtime(runtime_service, scenario, runtime_config)
        combined_report = merge_reports(request_report, scenario.validation_report, runtime_report)
        scenario.apply_validation_report(combined_report)
        if not scenario.validation_passed:
            raise ValueError(self._format_validation_error(scenario.validation_report))

        with db_session() as db:
            user = self._ensure_system_user(db)
            project = self._ensure_project(db, route.project_mode, user.id)
            scenario_row = self._ensure_scenario(db, project.id, user.id, route)

            latest_version = (
                db.query(func.max(ScenarioVersion.version_no))
                .filter(ScenarioVersion.scenario_id == scenario_row.id)
                .scalar()
            ) or 0

            version = ScenarioVersion(
                scenario_id=scenario_row.id,
                version_no=int(latest_version) + 1,
                seed=scenario.seed,
                terrain_config_json=dict(request.terrain_params),
                obstacle_config_json=dict(request.forest_params),
                event_config_json={
                    "task_params": dict(request.task_params),
                    "metadata": dict(request.metadata),
                    "environment_kind": route.environment_kind.value,
                    "task_kind": route.task_kind.value,
                    "generator_name": scenario.generator_name,
                    "generator_version": scenario.generator_version,
                    "validation_messages": list(scenario.validation_messages),
                    "validation_report": scenario.validation_report.to_payload(),
                    "route_key": route.route_key,
                },
                sensor_config_json=dict(request.visualization_options),
                reward_config_json=dict(scenario.effective_params),
                is_active=True,
            )
            db.add(version)
            db.flush()

            algorithm_key = str(params.get("algorithm", route.default_algorithm)).lower()
            algorithm = self._ensure_algorithm(db, algorithm_key, route.project_mode)

            run = Run(
                project_id=project.id,
                scenario_version_id=version.id,
                algorithm_id=algorithm.id,
                created_by_user_id=user.id,
                mode=route.project_mode,
                status=RunStatus.created,
                title=params.get("title") or f"{_task_display_name(route.task_kind)} run #{version.version_no}",
                description=params.get("description"),
                seed=scenario.seed,
                config_json={
                    "route_key": route.route_key,
                    "training_params": dict(params),
                    "runtime_config": dict(runtime_config),
                    "validation_report": scenario.validation_report.to_payload(),
                },
            )
            db.add(run)
            db.flush()

            target_dir = (
                get_storage_root()
                / f"scenario_{scenario_row.id}"
                / f"version_{version.version_no}_run_{run.id}"
            )

            try:
                stored = store_generated_scenario(
                    scenario=scenario,
                    request=request,
                    runtime_config=runtime_config,
                    target_dir=target_dir,
                )
            except Exception:
                shutil.rmtree(target_dir, ignore_errors=True)
                raise

            version.world_file_uri = str(stored.manifest_path)
            version.preview_image_uri = str(stored.preview_path)

            self._attach_scenario_layers(db, version.id, stored)
            self._attach_run_artifacts(db, run.id, stored)

            run_id = int(run.id)
            scenario_version_id = int(version.id)

        runtime_service.load_scenario(stored.scenario, stored.runtime_config)
        session = RunSession(
            run_id=run_id,
            scenario_version_id=scenario_version_id,
            route=route,
            stored_scenario=stored,
            service=runtime_service,
            training_params=dict(params),
            validation_report=stored.scenario.validation_report.to_payload(),
        )
        self._store_session(session)
        write_service_log(
            run_id=run_id,
            service_name="experiment_dispatcher",
            level="info",
            message="Scenario generated and loaded",
            payload_json={
                "route_key": route.route_key,
                "scenario_version_id": scenario_version_id,
                "validation_report": stored.scenario.validation_report.to_payload(),
            },
        )
        return session

    def load_run(self, run_id: int) -> RunSession:
        with self._lock:
            existing = self._sessions.get(run_id)
        if existing is not None:
            return existing

        with db_session() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run is None:
                raise KeyError(f"Run '{run_id}' not found")

            route_key = str((run.config_json or {}).get("route_key") or "")
            route = self._get_route(route_key)
            version = db.query(ScenarioVersion).filter(ScenarioVersion.id == run.scenario_version_id).first()
            if version is None or not version.world_file_uri:
                raise KeyError(f"Scenario version for run '{run_id}' is not persisted")

            stored = load_stored_scenario(version.world_file_uri)
            training_params = dict((run.config_json or {}).get("training_params") or {})

        service = route.service_factory()
        runtime_report = self._validate_runtime(service, stored.scenario, stored.runtime_config)
        combined_report = merge_reports(stored.scenario.validation_report, runtime_report)
        stored.scenario.apply_validation_report(combined_report)
        if not combined_report.passed:
            raise ValueError(self._format_validation_error(combined_report))
        service.load_scenario(stored.scenario, stored.runtime_config)
        session = RunSession(
            run_id=int(run_id),
            scenario_version_id=int(run.scenario_version_id),
            route=route,
            stored_scenario=stored,
            service=service,
            training_params=training_params,
            validation_report=combined_report.to_payload(),
        )
        self._store_session(session)
        self._persist_run_validation_report(int(run_id), session.validation_report)
        write_service_log(
            run_id=int(run_id),
            service_name="experiment_dispatcher",
            level="info",
            message="Run session loaded from persisted scenario",
            payload_json={"route_key": route.route_key, "scenario_version_id": int(run.scenario_version_id)},
        )
        return session

    def load_scenario_version(
        self,
        route_key: str,
        scenario_version_id: int,
        params: dict[str, Any] | None = None,
    ) -> RunSession:
        route = self._get_route(route_key)
        params = dict(params or {})

        with db_session() as db:
            version = db.query(ScenarioVersion).filter(ScenarioVersion.id == scenario_version_id).first()
            if version is None or not version.world_file_uri:
                raise KeyError(f"Scenario version '{scenario_version_id}' not found")

            stored = load_stored_scenario(version.world_file_uri)
            service = route.service_factory()
            runtime_report = self._validate_runtime(service, stored.scenario, stored.runtime_config)
            combined_report = merge_reports(stored.scenario.validation_report, runtime_report)
            stored.scenario.apply_validation_report(combined_report)
            if not combined_report.passed:
                raise ValueError(self._format_validation_error(combined_report))

            algorithm_key = str(params.get("algorithm", route.default_algorithm)).lower()
            algorithm = self._ensure_algorithm(db, algorithm_key, route.project_mode)
            user = self._ensure_system_user(db)
            run = Run(
                project_id=version.scenario.project_id,
                scenario_version_id=version.id,
                algorithm_id=algorithm.id,
                created_by_user_id=user.id,
                mode=route.project_mode,
                status=RunStatus.created,
                title=params.get("title") or f"{_task_display_name(route.task_kind)} run from scenario {scenario_version_id}",
                description=params.get("description"),
                seed=version.seed,
                config_json={
                    "route_key": route.route_key,
                    "training_params": params,
                    "runtime_config": dict(stored.runtime_config),
                    "validation_report": combined_report.to_payload(),
                },
            )
            db.add(run)
            db.flush()
            self._attach_run_artifacts(db, int(run.id), stored)
            run_id = int(run.id)

        service.load_scenario(stored.scenario, stored.runtime_config)
        session = RunSession(
            run_id=run_id,
            scenario_version_id=int(scenario_version_id),
            route=route,
            stored_scenario=stored,
            service=service,
            training_params=params,
            validation_report=combined_report.to_payload(),
        )
        self._store_session(session)
        write_service_log(
            run_id=run_id,
            service_name="experiment_dispatcher",
            level="info",
            message="Scenario version loaded into a new run",
            payload_json={"route_key": route.route_key, "scenario_version_id": int(scenario_version_id)},
        )
        return session

    def start_run(self, run_id: int, params: dict[str, Any] | None = None) -> RunSession:
        session = self.load_run(run_id)
        start_params = dict(session.training_params)
        start_params.update(dict(params or {}))
        start_params["mode"] = session.route.training_mode
        if "algorithm" not in start_params:
            start_params["algorithm"] = session.route.default_algorithm

        if session.observer is not None:
            session.observer.stop()
        session.training_params = start_params
        session.service.start(start_params)
        session.observer = RunObserver(
            run_id=run_id,
            route_key=session.route.route_key,
            task_kind=session.route.task_kind,
            service=session.service,
            poll_interval=self.observer_poll_interval,
        )
        session.observer.start()

        self._update_run_status(
            run_id,
            status=RunStatus.running,
            algorithm_key=str(start_params.get("algorithm", session.route.default_algorithm)).lower(),
            project_mode=session.route.project_mode,
            config_json={
                "route_key": session.route.route_key,
                "training_params": start_params,
                "runtime_config": dict(session.stored_scenario.runtime_config),
                "validation_report": session.validation_report,
            },
            started_at=datetime.utcnow(),
            finished_at=None,
        )
        write_service_log(
            run_id=run_id,
            service_name="experiment_dispatcher",
            level="info",
            message="Run started",
            payload_json={"route_key": session.route.route_key, "training_params": start_params},
        )
        return session

    def stop_run(self, run_id: int) -> None:
        session = self.load_run(run_id)
        session.service.stop()
        if session.observer is not None:
            session.observer.stop(final_status=RunStatus.cancelled, message="Run stopped by dispatcher")
            session.observer = None
        else:
            self._update_run_status(run_id, status=RunStatus.cancelled, finished_at=datetime.utcnow())
        write_service_log(
            run_id=run_id,
            service_name="experiment_dispatcher",
            level="info",
            message="Run stopped",
            payload_json={"route_key": session.route.route_key},
        )

    def reset_run(self, run_id: int) -> RunSession:
        session = self.load_run(run_id)
        session.service.reset()
        if session.observer is not None:
            session.observer.stop(final_status=RunStatus.cancelled, message="Run reset by dispatcher")
            session.observer = None
        session.service.load_scenario(session.stored_scenario.scenario, session.stored_scenario.runtime_config)
        self._update_run_status(run_id, status=RunStatus.created, started_at=None, finished_at=None)
        write_service_log(
            run_id=run_id,
            service_name="experiment_dispatcher",
            level="info",
            message="Run reset",
            payload_json={"route_key": session.route.route_key},
        )
        return session

    def dispose_run(self, run_id: int) -> None:
        with self._lock:
            session = self._sessions.pop(run_id, None)
        if session is None:
            return
        if session.observer is not None:
            session.observer.stop(
                final_status=RunStatus.cancelled if session.service.get_state().get("running") else None,
                message="Run disposed by dispatcher",
            )
            session.observer = None
        if session.service.get_state().get("running"):
            session.service.stop()
            self._update_run_status(run_id, status=RunStatus.cancelled, finished_at=datetime.utcnow())
        write_service_log(
            run_id=run_id,
            service_name="experiment_dispatcher",
            level="info",
            message="Run disposed",
            payload_json={"route_key": session.route.route_key},
        )

    def get_state(self, route_key: str, run_id: int | None) -> dict[str, Any]:
        if run_id is None:
            route = self._get_route(route_key)
            return {
                "running": False,
                "route_key": route.route_key,
                "environment_kind": route.environment_kind.value,
                "task_kind": route.task_kind.value,
                "run_id": None,
                "scenario_version_id": None,
                "scenario_loaded": False,
                "scenario_generated": False,
                "execution_phase": "idle",
            }

        session = self.load_run(run_id)
        session.last_error = session.last_error or getattr(session.service, "last_error", None)
        state = dict(session.service.get_state())
        execution_phase = "running" if state.get("running") else "preview"
        if session.last_error:
            execution_phase = "failed"
        elif session.observer is not None and session.observer.final_status is not None:
            execution_phase = session.observer.final_status.value
        elif session.observer is not None and session.training_params and not state.get("running") and int(state.get("step") or 0) > 0:
            execution_phase = "finished"
        elif session.observer is None and session.training_params and not state.get("running") and int(state.get("step") or 0) > 0:
            execution_phase = "stopped"

        state.update(
            {
                "route_key": session.route.route_key,
                "environment_kind": session.route.environment_kind.value,
                "task_kind": session.route.task_kind.value,
                "run_id": session.run_id,
                "scenario_version_id": session.scenario_version_id,
                "scenario_loaded": True,
                "scenario_generated": True,
                "execution_phase": execution_phase,
                "world_file_uri": str(session.stored_scenario.manifest_path),
                "preview_uri": str(session.stored_scenario.preview_path),
                "validation_passed": session.stored_scenario.scenario.validation_passed,
                "validation_messages": list(session.stored_scenario.scenario.validation_messages),
                "validation_report": session.validation_report or session.stored_scenario.scenario.validation_report.to_payload(),
            }
        )
        if session.last_error:
            state["error"] = session.last_error
        return state

    def _get_route(self, route_key: str) -> RuntimeRoute:
        try:
            return self.routes[route_key]
        except KeyError as exc:
            raise KeyError(f"Unsupported route '{route_key}'") from exc

    def _store_session(self, session: RunSession) -> None:
        with self._lock:
            self._sessions[session.run_id] = session

    def _validate_runtime(
        self,
        runtime_service: Any,
        scenario: GeneratedScenario,
        runtime_config: dict[str, Any],
    ) -> ValidationReport:
        if not hasattr(runtime_service, "validate_scenario"):
            return ValidationReport()
        messages = list(runtime_service.validate_scenario(scenario, runtime_config) or [])
        return report_for_runtime_validation(scenario, messages)

    @staticmethod
    def _format_validation_error(report: ValidationReport) -> str:
        return "; ".join(report.messages) or "Scenario validation failed"

    def _persist_run_validation_report(self, run_id: int, validation_report: dict[str, Any] | None) -> None:
        with db_session() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run is None:
                return
            config_json = dict(run.config_json or {})
            config_json["validation_report"] = dict(validation_report or {})
            run.config_json = config_json

    def _ensure_system_user(self, db) -> User:
        user = db.query(User).filter(User.email == "system@forest.local").first()
        if user is None:
            user = User(full_name="System Dispatcher", email="system@forest.local", role="system")
            db.add(user)
            db.flush()
        return user

    def _ensure_project(self, db, project_mode: ProjectMode, owner_user_id: int) -> Project:
        code = f"default-{project_mode.value}"
        project = db.query(Project).filter(Project.code == code).first()
        if project is None:
            project = Project(
                code=code,
                name=f"Default {project_mode.value} project",
                description="Autogenerated project for dispatcher-managed runs",
                owner_user_id=owner_user_id,
            )
            db.add(project)
            db.flush()
        return project

    def _ensure_scenario(self, db, project_id: int, creator_user_id: int, route: RuntimeRoute) -> Scenario:
        code = f"generated-{route.environment_kind.value}-{route.task_kind.value}"
        scenario = (
            db.query(Scenario)
            .filter(Scenario.project_id == project_id, Scenario.code == code)
            .first()
        )
        if scenario is None:
            scenario = Scenario(
                project_id=project_id,
                code=code,
                name=f"Generated {_task_display_name(route.task_kind)} scenario",
                mode=route.project_mode,
                description="Scenario series managed by the experiment dispatcher",
                created_by_user_id=creator_user_id,
            )
            db.add(scenario)
            db.flush()
        return scenario

    def _ensure_algorithm(self, db, algorithm_key: str, project_mode: ProjectMode) -> Algorithm:
        code = f"{algorithm_key}_{project_mode.value}"
        algorithm = db.query(Algorithm).filter(Algorithm.code == code).first()
        if algorithm is None:
            algorithm = Algorithm(
                code=code,
                name=algorithm_key.upper(),
                family=_algorithm_family_for_key(algorithm_key),
                mode=project_mode,
                framework="stable_baselines3",
                description="Autogenerated algorithm entry for dispatcher-managed runs",
                default_config_json={"algorithm": algorithm_key},
            )
            db.add(algorithm)
            db.flush()
        return algorithm

    def _attach_scenario_layers(self, db, scenario_version_id: int, stored: StoredScenario) -> None:
        for layer in stored.scenario.layers.values():
            layer_path = stored.layer_paths[layer.name]
            db.add(
                ScenarioLayer(
                    scenario_version_id=scenario_version_id,
                    layer_type=layer.layer_type,
                    file_uri=str(layer_path),
                    file_format=layer.file_format,
                    description=layer.description,
                )
            )

    def _attach_run_artifacts(self, db, run_id: int, stored: StoredScenario) -> None:
        db.add(
            Artifact(
                run_id=run_id,
                artifact_type=ArtifactType.world_file,
                name="scenario.json",
                storage_uri=str(stored.manifest_path),
                mime_type="application/json",
                size_bytes=stored.manifest_path.stat().st_size,
            )
        )
        db.add(
            Artifact(
                run_id=run_id,
                artifact_type=ArtifactType.scenario_preview,
                name="preview.json",
                storage_uri=str(stored.preview_path),
                mime_type="application/json",
                size_bytes=stored.preview_path.stat().st_size,
            )
        )
        for layer in stored.scenario.layers.values():
            layer_path = stored.layer_paths[layer.name]
            db.add(
                Artifact(
                    run_id=run_id,
                    artifact_type=ArtifactType.map_layer,
                    name=layer.name,
                    storage_uri=str(layer_path),
                    mime_type="application/octet-stream",
                    size_bytes=layer_path.stat().st_size,
                )
            )

    def _update_run_status(
        self,
        run_id: int,
        *,
        status: RunStatus,
        algorithm_key: str | None = None,
        project_mode: ProjectMode | None = None,
        config_json: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        with db_session() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run is None:
                return

            run.status = status
            if config_json is not None:
                run.config_json = config_json
            if started_at is not None or status == RunStatus.created:
                run.started_at = started_at
            if finished_at is not None or status == RunStatus.created:
                run.finished_at = finished_at

            if algorithm_key is not None and project_mode is not None:
                algorithm = self._ensure_algorithm(db, algorithm_key, project_mode)
                run.algorithm_id = algorithm.id
