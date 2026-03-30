# Сценарии и генерация среды

## Общая идея

В текущей реализации сценарий — это не только набор параметров для среды, а отдельный сериализуемый артефакт, который можно:

- сгенерировать;
- провалидировать;
- сохранить;
- повторно загрузить;
- связать с `run`;
- использовать для preview и воспроизводимости эксперимента.

## Основные модели

`services/scenario_generator/models.py` задает текущую предметную модель генерации.

### `GenerationRequest`

Содержит:

- `environment_kind`
- `task_kind`
- `seed`
- `terrain_params`
- `forest_params`
- `task_params`
- `visualization_options`
- `metadata`

### `GeneratedScenario`

Содержит:

- `environment_kind`
- `task_kind`
- `seed`
- `generator_name`
- `generator_version`
- `effective_params`
- `layers`
- `preview_payload`
- `runtime_context`
- `validation_messages`
- `validation_passed`
- `validation_report`

### `GeneratedLayer`

Каждый слой описывается именем, типом, данными, форматом файла и описанием.
По умолчанию слои сохраняются в `npy`, но часть слоев может храниться и как JSON.

## Что сохраняется на диск

При сохранении сценария в `services/scenario_generator/storage.py` создаются:

- `preview.json`
- `scenario.json`
- файлы слоев, например `terrain.npy`, `free_mask.npy`, `terrain_preview.npy`

Файлы кладутся в `data/scenarios/generated/scenario_<id>/version_<n>_run_<id>/`.

## Смысл основных файлов

### `preview.json`

Легковесное описание для UI и быстрого предпросмотра.
Содержит:

- `environment_kind`
- `task_kind`
- `preview_payload`
- `validation_passed`
- `validation_messages`
- `validation_report`

### `scenario.json`

Канонический сериализованный результат генерации.
Содержит:

- общие атрибуты сценария;
- итоговые параметры;
- runtime context;
- validation report;
- исходный `request`;
- `runtime_config`;
- манифест слоев;
- ссылку на `preview.json`.

## Связь со структурой БД

Сценарий в файловом хранилище связан с несколькими сущностями БД:

- `scenarios` — логическая серия сценариев;
- `scenario_versions` — конкретная версия с seed, конфигами и ссылкой на world/preview;
- `scenario_layers` — отдельные слои среды;
- `runs` — конкретные исполнения, использующие эту версию сценария;
- `artifacts` — зарегистрированные файлы сценария и preview.

## Виды среды и задач

На текущий момент в коде поддерживаются:

### `environment_kind`

- `grid`
- `continuous_2d`
- `simulator_3d`

### `task_kind`

- `trail`
- `patrol`
- `reforestation`
- `robot`

Из них реально активны в runtime `trail`, `patrol` и `reforestation`.

## Валидация

Валидация идет в несколько шагов:

1. проверка входного `GenerationRequest`;
2. проверка результата генератора;
3. runtime-specific validation перед загрузкой в конкретный service;
4. объединение issues в единый `ValidationReport`.

Это значит, что `validation_report` уже является важной частью текущего формата сценария и должен быть отражен в будущих формальных контрактах.

## Что формализовано в contracts

Теперь текущая структура сохраненных файлов зафиксирована в:

- `contracts/v1/scenario.schema.json`
- `contracts/v1/preview.schema.json`

При этом содержимое `preview_payload`, `runtime_context`, `runtime_config` и параметрических словарей, зависящее от маршрута, остаётся расширяемым, потому что именно в этих местах проект пока продолжает активно расти.
