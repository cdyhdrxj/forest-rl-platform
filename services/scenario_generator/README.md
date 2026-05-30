# Генератор сценариев

Общий модуль генерации среды для платформы. Это уже не заглушка: через него backend строит `GeneratedScenario`, preview, runtime context и файлы сценария для текущих runtime routes.

Source of truth по коду:

- `models.py` - `GenerationRequest`, `GeneratedScenario`, `GeneratedLayer`;
- `defaults.py` - регистрация встроенных family generators, task overlays и validator;
- `builtin.py` - встроенные генераторы/overlays для `grid`, `continuous_2d`, `simulator_3d`;
- `adapters.py` - адаптеры между dispatcher/runtime-сервисами и общим форматом генерации;
- `storage.py` - сохранение `scenario.json`, `preview.json` и layer files.

## Зоны ответственности

- принимать единый запрос на генерацию;
- выбирать семейство генераторов по типу среды;
- применять расширения, зависящие от задачи;
- валидировать сгенерированный сценарий;
- возвращать канонический объект сценария для runtime-адаптеров.

## Основная точка входа

- `get_default_environment_generation_service()`

## Встроенная поддержка

- `grid`
- `continuous_2d`
- `simulator_3d`

Task overlays:

- `patrol`
- `reforestation`
- `trail`
- `coverage`

## Текущие интеграции

- `apps/api/dispatcher.py`
- `services/patrol_planning`
- `services/reforestation_planting`
- `services/agrocare_coverage`
- `services/trail_camar`
- `services/simulator_3d`

Формальные JSON-схемы сохраненных артефактов находятся в `contracts/v1/scenario.schema.json` и `contracts/v1/preview.schema.json`. Человекочитаемое описание потока генерации - в `docs/scenarios/README.md`.
