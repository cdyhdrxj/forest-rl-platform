# API и протокол WebSocket

## Текущее состояние

Сейчас backend платформы построен вокруг FastAPI-приложения, но его рабочий внешний интерфейс — это WebSocket-маршруты.
`contracts/openapi.yaml` хранит HTTP-метаданные backend-сервиса, а канонический контракт работы в реальном времени вынесен в `contracts/websocket_protocol.md`.

## Поддерживаемые маршруты

Активные маршруты определены в `apps/api/app.py`:

- `/continuous/trail`
- `/discrete/patrol`
- `/discrete/reforestation`
- `/threed/patrol`
- `/threed/trail`

Закомментированные маршруты не считаются частью поддерживаемого публичного интерфейса.

## Формат клиентского сообщения

Клиент отправляет JSON-объект.
Базовая форма сейчас такая:

```json
{
  "action": "generate",
  "params": {}
}
```

Дополнительные поля используются точечно:

- `run_id` — для загрузки уже существующего запуска;
- `scenario_version_id` — для загрузки ранее сохраненной версии сценария;
- `params` — параметры генерации, загрузки или старта.

## Поддерживаемые действия

На текущий момент в `apps/api/websocket_manager.py` реализованы:

- `generate` — сгенерировать сценарий и сразу загрузить его в сервис исполнения;
- `load` — загрузить `run_id` или `scenario_version_id`;
- `start` — запустить сервис исполнения;
- `stop` — остановить сервис исполнения;
- `reset` — сбросить сервис исполнения и повторно загрузить сценарий;
- `dispose` — освободить сессию исполнения.

## Формат серверного состояния

Сервер отправляет JSON-снимок состояния с высокой частотой.
Есть два слоя полей:

### Общие поля от диспетчера

Эти поля добавляются или нормализуются в `ExperimentDispatcher.get_state(...)`:

- `running`
- `route_key`
- `environment_kind`
- `task_kind`
- `run_id`
- `scenario_version_id`
- `scenario_loaded`
- `scenario_generated`
- `execution_phase`
- `world_file_uri`
- `preview_uri`
- `validation_passed`
- `validation_messages`
- `validation_report`
- `error` — при ошибке во время исполнения

### Поля от сервиса, зависящие от маршрута

Конкретный сервис исполнения возвращает собственный набор полей через `get_state()`.
Чаще всего встречаются:

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

Дополнительные поля зависят от режима:

- patrol: `intruders_remaining`
- reforestation: `planted_pos`, `coverage_ratio`, `remaining_seedlings`, `invalid_plant_count`, `plantable_map`, `planted_map`
- 3d-сервис: возвращает снимок собственного `_state`, включая события времени исполнения и данные, производные от preview

## Ошибки

Сейчас ошибки не выделены в отдельный формальный контракт ошибок.
При исключении backend формирует текущее состояние и добавляет в него поле:

```json
{
  "error": "..."
}
```

Это рабочее поведение, но не финализированная контрактная модель.

## Реплеи, метрики и события

Во время выполнения `RunObserver` записывает:

- replay в `data/runs/run_<id>/replay_<timestamp>.jsonl`;
- snapshot-метрики в таблицы `metric_series` и `metric_points`;
- завершенные эпизоды в `episodes`;
- события времени исполнения в `episode_events`;
- сервисные логи в `service_logs`.

## Что уже стабильно, а что нет

### Можно считать относительно стабильным

- набор активных route key;
- общий lifecycle run-сессии: generate/load/start/stop/reset/dispose;
- наличие обязательных полей состояния, добавляемых диспетчером;
- сценарий `generate -> load -> start -> observer -> replay/metrics`.

### Пока считаем черновым

- формальный JSON Schema для входных WebSocket-сообщений;
- формальный JSON Schema для server state;
- версия протокола и политика backward compatibility;
- строгая модель ошибок;
- разграничение обязательных полей и полей, зависящих от маршрута.

## Что нужно формализовать дальше

Для переноса этого описания в `contracts/` нужны решения по:

- месту хранения контракта реального времени: markdown рядом с OpenAPI или отдельный AsyncAPI;
- набору обязательных state-полей;
- политике расширения `params`;
- версии протокола;
- формату ошибок;
- поддержке полей для multi-agent режима.

Подробный список спорных решений вынесен в `../contracts_status.md`.
