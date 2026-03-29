from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np

from services.scenario_generator.models import (
    EnvironmentKind,
    GeneratedLayer,
    GeneratedScenario,
    GenerationRequest,
    TaskKind,
)


@dataclass(slots=True)
class StoredScenario:
    scenario: GeneratedScenario
    request: GenerationRequest
    runtime_config: dict[str, Any]
    manifest_path: Path
    preview_path: Path
    layer_paths: dict[str, Path]


def get_storage_root() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    root = repo_root / "data" / "scenarios" / "generated"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, np.ndarray):
        return np.asarray(value).tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def store_generated_scenario(
    scenario: GeneratedScenario,
    request: GenerationRequest,
    runtime_config: dict[str, Any],
    target_dir: Path,
) -> StoredScenario:
    target_dir.mkdir(parents=True, exist_ok=True)

    preview_path = target_dir / "preview.json"
    _write_json(
        preview_path,
        {
            "environment_kind": scenario.environment_kind.value,
            "task_kind": scenario.task_kind.value,
            "preview_payload": _to_jsonable(scenario.preview_payload),
            "validation_passed": scenario.validation_passed,
            "validation_messages": list(scenario.validation_messages),
        },
    )

    layer_paths: dict[str, Path] = {}
    layer_manifest: list[dict[str, Any]] = []
    for layer in scenario.layers.values():
        file_name = f"{layer.name}.{layer.file_format}"
        file_path = target_dir / file_name

        if layer.file_format == "npy":
            np.save(file_path, np.asarray(layer.data, dtype=np.float32))
        else:
            file_path.write_text(
                json.dumps(layer.to_serializable(), ensure_ascii=False),
                encoding="utf-8",
            )

        layer_paths[layer.name] = file_path
        layer_manifest.append(
            {
                "name": layer.name,
                "layer_type": layer.layer_type,
                "file_uri": str(file_path),
                "file_format": layer.file_format,
                "description": layer.description,
            }
        )

    manifest_path = target_dir / "scenario.json"
    _write_json(
        manifest_path,
        {
            "environment_kind": scenario.environment_kind.value,
            "task_kind": scenario.task_kind.value,
            "seed": scenario.seed,
            "generator_name": scenario.generator_name,
            "generator_version": scenario.generator_version,
            "effective_params": _to_jsonable(scenario.effective_params),
            "preview_payload": _to_jsonable(scenario.preview_payload),
            "runtime_context": _to_jsonable(scenario.runtime_context),
            "validation_messages": list(scenario.validation_messages),
            "validation_passed": scenario.validation_passed,
            "request": {
                "environment_kind": request.environment_kind.value,
                "task_kind": request.task_kind.value,
                "seed": request.seed,
                "terrain_params": _to_jsonable(request.terrain_params),
                "forest_params": _to_jsonable(request.forest_params),
                "task_params": _to_jsonable(request.task_params),
                "visualization_options": _to_jsonable(request.visualization_options),
                "metadata": _to_jsonable(request.metadata),
            },
            "runtime_config": _to_jsonable(runtime_config),
            "layers": layer_manifest,
            "preview_uri": str(preview_path),
        },
    )

    return StoredScenario(
        scenario=scenario,
        request=request,
        runtime_config=dict(runtime_config),
        manifest_path=manifest_path,
        preview_path=preview_path,
        layer_paths=layer_paths,
    )


def load_stored_scenario(manifest_path: str | Path) -> StoredScenario:
    manifest_path = Path(manifest_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    request_payload = payload["request"]
    request = GenerationRequest(
        environment_kind=EnvironmentKind(request_payload["environment_kind"]),
        task_kind=TaskKind(request_payload["task_kind"]),
        seed=request_payload.get("seed"),
        terrain_params=dict(request_payload.get("terrain_params") or {}),
        forest_params=dict(request_payload.get("forest_params") or {}),
        task_params=dict(request_payload.get("task_params") or {}),
        visualization_options=dict(request_payload.get("visualization_options") or {}),
        metadata=dict(request_payload.get("metadata") or {}),
    )

    scenario = GeneratedScenario(
        environment_kind=EnvironmentKind(payload["environment_kind"]),
        task_kind=TaskKind(payload["task_kind"]),
        seed=int(payload["seed"]),
        generator_name=str(payload["generator_name"]),
        generator_version=str(payload["generator_version"]),
        effective_params=dict(payload.get("effective_params") or {}),
        preview_payload=dict(payload.get("preview_payload") or {}),
        runtime_context=dict(payload.get("runtime_context") or {}),
        validation_messages=list(payload.get("validation_messages") or []),
        validation_passed=bool(payload.get("validation_passed", True)),
    )

    layer_paths: dict[str, Path] = {}
    for layer_meta in payload.get("layers", []):
        file_path = Path(layer_meta["file_uri"])
        file_format = layer_meta.get("file_format", "npy")
        if file_format == "npy":
            layer_data = np.load(file_path)
        else:
            layer_data = np.asarray(json.loads(file_path.read_text(encoding="utf-8")), dtype=np.float32)

        scenario.add_layer(
            GeneratedLayer(
                name=layer_meta["name"],
                layer_type=layer_meta["layer_type"],
                data=np.asarray(layer_data, dtype=np.float32),
                file_format=file_format,
                description=layer_meta.get("description"),
            )
        )
        layer_paths[layer_meta["name"]] = file_path

    preview_path = Path(payload.get("preview_uri", manifest_path.parent / "preview.json"))

    return StoredScenario(
        scenario=scenario,
        request=request,
        runtime_config=dict(payload.get("runtime_config") or {}),
        manifest_path=manifest_path,
        preview_path=preview_path,
        layer_paths=layer_paths,
    )
