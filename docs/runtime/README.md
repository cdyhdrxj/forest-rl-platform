# Runtime и жизненный цикл run

## Главные роли

| Роль | Код | Ответственность |
| --- | --- | --- |
| WebSocket manager | `apps/api/websocket_manager.py` | Принимает команды клиента и отправляет state snapshots. |
| ExperimentDispatcher | `apps/api/dispatcher.py` | Генерирует/загружает сценарии, создает runs, выбирает runtime service. |
| Scenario generator | `services/scenario_generator` | Строит `GeneratedScenario`, preview, runtime config и validation report. |
| Runtime service | `services/*` | Исполняет конкретную среду и отдает `get_state()`. |
| RunObserver | `apps/api/runtime_monitor.py` | Пишет replay, metrics, episodes, episode events и service logs. |
| Storage layer | `packages/db`, `data/` | Хранит metadata и файлы. |

## Поддерживаемые routes

| Route key | Runtime service | Environment | Task | Статус |
| --- | --- | --- | --- | --- |
| `continuous/trail` | `CamarService` | `continuous_2d` | `trail` | рабочий |
| `continuous/coverage` | `AgrocareCoverageService` | `continuous_2d` | `coverage` | scientific MVP, развитие заморожено |
| `discrete/patrol` | `GridWorldService` | `grid` | `patrol` | рабочий |
| `discrete/reforestation` | `SeedlingPlantingService` | `grid` | `reforestation` | рабочий |
| `threed/trail` | `Simulator3DService` | `simulator_3d` | `trail` | ожидает реальный `/env/step` |
| `threed/patrol` | `Simulator3DService` | `simulator_3d` | `patrol` | ожидает реальный `/env/step` |

Source of truth для таблицы - `DEFAULT_ROUTES` в `apps/api/dispatcher.py`.

## Lifecycle

```text
idle
  -> generate/load
  -> preview
  -> start
  -> running
  -> stop | finish | reset | dispose | failure
```

### `generate`

1. Dispatcher выбирает `RuntimeRoute`.
2. Route builder создает `GenerationRequest`.
3. Scenario generator возвращает `GeneratedScenario`.
4. Runtime config builder готовит параметры сервиса.
5. Сценарий валидируется на уровне request, generator и runtime.
6. Создаются записи `project`, `scenario`, `scenario_version`, `algorithm`, `run`.
7. Сценарий сохраняется в `data/scenarios/generated/...`.
8. Runtime service получает `load_scenario(...)`.

### `load`

Есть два варианта:

- загрузить существующий `run_id`;
- загрузить `scenario_version_id` и создать новый run на базе сохраненного сценария.

### `start`

Dispatcher вызывает `service.start(params)`, затем создает `RunObserver`. Observer начинает опрашивать `get_state()` и сохранять runtime-артефакты.

### `stop`

Останавливает runtime и observer без финального статуса. Для обучающих режимов dispatcher пытается сохранить checkpoint, если runtime выставил `_last_checkpoint_path`.

### `finish`

Финализирует run со статусом `finished`, останавливает observer и сохраняет checkpoint для train run.

### `reset`

Останавливает текущий runtime, сбрасывает service state, повторно загружает сценарий и возвращает run к статусу `created`.

### `dispose`

Освобождает session, отменяет run и используется при закрытии WebSocket или переключении активного run.

## Runtime service interface

Минимальный интерфейс:

```python
load_scenario(scenario, runtime_config)
start(params)
stop()
reset()
get_state() -> dict
```

Дополнительные методы:

```python
validate_scenario(scenario, runtime_config) -> list[str]
drain_runtime_events() -> list[dict]
```

`get_state()` должен возвращать как минимум `running`. Для хорошей интеграции с observer желательно поддерживать:

- `episode`;
- `step`;
- `total_reward`;
- `last_episode_reward`;
- `new_episode`;
- `goal_count`;
- `collision_count`;
- `agent_pos`;
- `goal_pos`;
- `trajectory`;
- route-specific metrics.

## Execution phase

Dispatcher нормализует `execution_phase`:

- `idle` - run не загружен;
- `preview` - сценарий загружен, runtime не запущен;
- `running` - runtime активен;
- `stopped` - runtime остановлен после старта;
- `finished` - run завершен;
- `failed` - ошибка runtime/dispatcher;
- `cancelled` - run отменен.

## RunObserver

Observer пишет:

- replay JSONL;
- `MetricSeries` и `MetricPoint`;
- `Episode`;
- `EpisodeEvent`;
- `Replay`;
- `Artifact`;
- `ServiceLog`.

Replay line имеет форму:

```json
{
  "timestamp": "2026-05-23T12:00:00.000000",
  "route_key": "discrete/patrol",
  "state": {}
}
```

Observer сначала использует прямые события из `drain_runtime_events()`. Если их нет, часть событий выводится эвристически из state, например по росту `collision_count` или `goal_count`.

## 3D runtime

Для `threed/trail` и `threed/patrol` выбран синхронный Gymnasium-like handshake:

```text
reset(config) -> observation, info
step(action) -> observation, reward, terminated, truncated, info
```

В ROS это сервис `/env/step` типа `forest_msgs/srv/Step`.

Synthetic loop в `Simulator3DService` не является обычным runtime. Он включается только явно:

```powershell
$env:SIMULATOR_3D_SYNTHETIC="1"
```

или через params:

```json
{
  "synthetic": true
}
```

Обычный режим по умолчанию - `sync_step`. Если Unity/ROS не реализует `/env/step`, `start` 3D run завершится ошибкой.

## Границы ответственности 3D

| Слой | Ответственность |
| --- | --- |
| Unity/симулятор | Реальное состояние сцены, физика, сенсоры, `/env/reset`, `/env/step`, runtime events. |
| ROS integration | `.msg/.srv`, rosbridge, ROS TCP endpoint, совместимость типов. |
| Backend/API | Dispatcher, сохранение replay/metrics/events, адаптация ROS response в platform state. |
| RL-разработчики | Action space, reward semantics, done semantics, policies и training params. |
