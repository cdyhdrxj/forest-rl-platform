# WebSocket-протокол платформы Forest RL

Версия: `v1`

## Область действия

Этот документ определяет контракт управления и телеметрии во время исполнения,
который используется WebSocket-маршрутами backend-сервиса.
Именно он считается канонической спецификацией взаимодействия в реальном времени.

Связанный файл `contracts/openapi.yaml` намеренно не содержит HTTP-маршруты исполнения,
потому что текущая реализация платформы строится вокруг WebSocket.

## Поддерживаемые маршруты

Клиент подключается к одному из следующих путей:

- `/continuous/trail`
- `/discrete/patrol`
- `/discrete/reforestation`
- `/threed/patrol`
- `/threed/trail`

Пример адреса endpoint:

```text
ws://localhost:8000/threed/trail
```

## Транспортная модель

- сообщения клиента представляют собой JSON-объекты;
- сообщения сервера представляют собой JSON-снимки состояния;
- сервер непрерывно отправляет state, пока сокет открыт;
- поля, зависящие от маршрута, могут добавляться без смены версии,
  если обязательные поля диспетчера остаются стабильными;
- полезные нагрузки для multi-agent режима в `v1` не входят.

## Формат сообщения клиента

```json
{
  "action": "generate",
  "params": {}
}
```

Дополнительные поля верхнего уровня используются только при необходимости:

- `run_id`
- `scenario_version_id`
- `params`

## Поддерживаемые действия

### `generate`

Сгенерировать сценарий для текущего маршрута и загрузить его в сессию исполнения.

```json
{
  "action": "generate",
  "params": {
    "seed": 17
  }
}
```

### `load`

Загрузить либо существующий `run_id`, либо сохранённый `scenario_version_id`.

```json
{
  "action": "load",
  "run_id": 12
}
```

```json
{
  "action": "load",
  "scenario_version_id": 5,
  "params": {
    "algorithm": "ppo"
  }
}
```

### `start`

Запустить уже загруженную сессию исполнения.
Если активный run ещё не загружен, backend-сервис может сначала сгенерировать и загрузить его.

```json
{
  "action": "start",
  "params": {
    "algorithm": "ppo",
    "max_steps": 240
  }
}
```

### `stop`

Остановить текущий run.

```json
{
  "action": "stop"
}
```

### `reset`

Сбросить состояние исполнения и повторно загрузить текущий сценарий.

```json
{
  "action": "reset"
}
```

### `dispose`

Освободить текущую сессию исполнения и отвязать её от сокета.

```json
{
  "action": "dispose"
}
```

## Семейства параметров

Объект `params` зависит от маршрута.
В `v1` фиксируется общий внешний контейнер, а расширение полей,
зависящих от маршрута, допускается внутри `params`.

### `/continuous/trail`

Плоский объект параметров.
Сейчас backend-сервис обычно использует здесь такие ключи:

- `seed`
- `grid_size`
- `obstacle_density`
- `terrain_hilliness`
- `algorithm`
- `max_steps`
- поля настройки награды и динамики

### `/discrete/patrol`

Backend принимает либо:

- плоский объект, совместимый с `GridWorldConfig`, или
- объект с полем `grid_world_config`

Сейчас маршрут опирается на семантику `GridWorldConfig`
для генерации патрульного сценария и запуска исполнения.

### `/discrete/reforestation`

Backend принимает плоский объект, совместимый с `PlantingEnvConfig`.

### `/threed/patrol` и `/threed/trail`

Плоский объект параметров.
Сейчас backend-сервис обычно использует здесь такие ключи:

- `seed`
- `preview_size` or `grid_size`
- `tree_density`
- `terrain_hilliness`
- `algorithm`
- `max_steps`
- параметры обучения, зависящие от задачи

## Формат сообщения сервера

Сервер отправляет JSON-объект, представляющий текущее состояние маршрута.

### Обязательные поля диспетчера

Эти поля входят в стабильный контракт `v1`:

- `running`
- `route_key`
- `environment_kind`
- `task_kind`
- `run_id`
- `scenario_version_id`
- `scenario_loaded`
- `scenario_generated`
- `execution_phase`

### Дополнительные поля диспетчера

Когда сценарий уже загружен, backend-сервис может также добавлять:

- `world_file_uri`
- `preview_uri`
- `validation_passed`
- `validation_messages`
- `validation_report`
- `error`

### Поля конкретного runtime-сервиса

Сервисы исполнения добавляют дополнительные поля, зависящие от маршрута.
Часто встречаются, например:

- `episode`
- `step`
- `total_reward`
- `last_episode_reward`
- `new_episode`
- `agent_pos`
- `goal_pos`
- `landmark_pos`
- `is_collision`
- `goal_count`
- `collision_count`
- `trajectory`
- `terrain_map`

Дополнительные примеры по режимам:

- patrol: `intruders_remaining`
- reforestation: `planted_pos`, `coverage_ratio`, `remaining_seedlings`, `invalid_plant_count`, `plantable_map`, `planted_map`
- 3D runtime: `world_descriptor`, `max_steps`

## Значения `execution_phase`

Сейчас backend-сервис отдаёт следующие значения:

- `idle`
- `preview`
- `running`
- `finished`
- `stopped`
- `failed`
- `cancelled`

## Обработка ошибок

В `v1` используется встроенное поле ошибки.
При ошибке backend-сервис отправляет текущий снимок состояния с полем:

```json
{
  "error": "human-readable message"
}
```

Отдельный контейнер ошибки в `v1` не определён.

## Связанные сохраняемые артефакты

WebSocket-протокол связан со следующими форматами сохраняемых данных:

- `contracts/v1/scenario.schema.json`
- `contracts/v1/preview.schema.json`
- `contracts/v1/replay.schema.json`
- `contracts/v1/metrics.schema.json`
- `contracts/v1/episode_log.schema.json`

## Политика версионирования

- добавочные поля, зависящие от маршрута, допускаются в пределах `v1`;
- удаление обязательных полей диспетчера считается несовместимым изменением;
- переименование действий или изменение смысла сохраняемых полей артефактов считается несовместимым изменением;
- поддержка multi-agent потребует новой ревизии контракта или явно версионированного расширения.
