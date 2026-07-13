# API backend

## Текущее состояние

Backend построен на FastAPI, но основной runtime-интерфейс платформы - WebSocket. HTTP endpoints используются для health check, списка runs, просмотра replay, переименования run и проверки checkpoint.

Канонический live-контракт:

- `contracts/websocket_protocol.md`

HTTP/OpenAPI:

- `contracts/openapi.yaml` сейчас неполный и не описывает все реальные HTTP endpoints;
- source of truth для HTTP endpoints - `apps/api/app.py`.

Отдельно существует вспомогательный WebRTC-signaling слой для Unity video stream. Он не управляет lifecycle run и не заменяет runtime WebSocket routes.

## WebSocket routes

Активные routes определены в `apps/api/app.py` и `apps/api/dispatcher.py`:

| Route | Route key | Назначение |
| --- | --- | --- |
| `/continuous/trail` | `continuous/trail` | 2D непрерывная прокладка тропы. |
| `/continuous/coverage` | `continuous/coverage` | Headless coverage runtime для scientific MVP. |
| `/discrete/patrol` | `discrete/patrol` | Grid patrol runtime. |
| `/discrete/reforestation` | `discrete/reforestation` | Grid reforestation runtime. |
| `/threed/patrol` | `threed/patrol` | 3D patrol через `Simulator3DService`. |
| `/threed/trail` | `threed/trail` | 3D trail через `Simulator3DService`. |

Это список backend routes. Текущий frontend selector может показывать подмножество этих routes; например `threed/patrol` объявлен в backend и `WS_MAP`, но не включен в `TASKS_BY_ENV` как ручной выбор нового эксперимента.

Пример:

```text
ws://localhost:8000/discrete/patrol
```

## Сообщение клиента

Базовая форма:

```json
{
  "action": "generate",
  "params": {}
}
```

Дополнительные поля верхнего уровня:

- `run_id` - загрузить существующий run;
- `scenario_version_id` - создать новый run из сохраненной версии сценария;
- `source_run_id` - источник checkpoint для `start_eval`;
- `params` - параметры генерации, загрузки или старта.

## WebSocket actions

| Action | Статус | Смысл |
| --- | --- | --- |
| `generate` | рабочий | Сгенерировать сценарий и загрузить runtime session. |
| `load` | рабочий | Загрузить `run_id` или `scenario_version_id`. |
| `start` | рабочий | Запустить активный run; если run нет, backend может сначала сгенерировать его. |
| `start_eval` | рабочий в коде | Запустить evaluation из checkpoint другого run. Требует `source_run_id`. |
| `stop` | рабочий | Остановить run без финального статуса, потенциально сохранив checkpoint. |
| `finish` | рабочий | Финализировать run со статусом `finished`. |
| `reset` | рабочий | Сбросить run и повторно загрузить сценарий. |
| `dispose` | рабочий | Освободить session и отменить run. |

## Примеры команд

Сгенерировать сценарий:

```json
{
  "action": "generate",
  "params": {
    "seed": 17
  }
}
```

Загрузить run:

```json
{
  "action": "load",
  "run_id": 12
}
```

Загрузить сохраненную версию сценария как новый run:

```json
{
  "action": "load",
  "scenario_version_id": 5,
  "params": {
    "algorithm": "ppo"
  }
}
```

Запустить:

```json
{
  "action": "start",
  "params": {
    "algorithm": "ppo",
    "max_steps": 240
  }
}
```

Запустить evaluation из checkpoint:

```json
{
  "action": "start_eval",
  "source_run_id": 10,
  "params": {
    "deterministic": true
  }
}
```

Финализировать:

```json
{
  "action": "finish"
}
```

## State snapshots

Сервер отправляет JSON-снимки состояния примерно каждые `0.1` секунды, пока WebSocket открыт.

Обязательные поля dispatcher:

- `running`;
- `route_key`;
- `environment_kind`;
- `task_kind`;
- `run_id`;
- `scenario_version_id`;
- `scenario_loaded`;
- `scenario_generated`;
- `execution_phase`.

После загрузки сценария добавляются:

- `world_file_uri`;
- `preview_uri`;
- `validation_passed`;
- `validation_messages`;
- `validation_report`;
- `error`, если была ошибка.

Runtime service добавляет route-specific поля, например:

- `episode`;
- `step`;
- `total_reward`;
- `last_episode_reward`;
- `new_episode`;
- `agent_pos`;
- `goal_pos`;
- `trajectory`;
- `terrain_map`;
- `goal_count`;
- `collision_count`;
- `coverage_ratio`;
- `intruders_remaining`.

Для 3D также возможны:

- `world_descriptor`;
- `runtime_mode`;
- `last_observation`;
- `last_info`;
- `terminated`;
- `truncated`.

## Execution phase

Возможные значения:

- `idle`;
- `preview`;
- `running`;
- `finished`;
- `stopped`;
- `failed`;
- `cancelled`.

## HTTP endpoints

Реальные endpoints в `apps/api/app.py`:

| Method | Path | Назначение |
| --- | --- | --- |
| `GET` | `/api/health` | Health check backend. |
| `GET` | `/api/runs` | Список runs с pagination и search. |
| `GET` | `/api/runs/{run_id}` | Metadata конкретного run. |
| `GET` | `/api/runs/{run_id}/replay` | Последний replay run как массив frames. |
| `PATCH` | `/api/runs/{run_id}` | Переименовать run. |
| `GET` | `/api/runs/{run_id}/checkpoint` | Проверить наличие checkpoint artifact. |

## WebRTC signaling endpoints

`apps/api/app.py` подключает `apps/api/webrtc_routes.py`. Эти endpoints нужны компоненту Unity WebRTC stream во frontend:

| Type | Path | Назначение |
| --- | --- | --- |
| `GET` | `/webrtc/config` | Конфигурация signaling mode для WebRTC player. |
| WebSocket | `/ws` | Основной signaling канал, который использует текущий `WebRTCPlayer`. |
| WebSocket | `/signaling` | Совместимый WebSocket signaling endpoint. |

`apps/web/src/constants/envs.js` также содержит legacy HTTP key `WebrtcSignaling` для старого polling-клиента, но текущий компонент `WebRTCPlayer` использует `WebSocketSignaling` и подключается к `/ws`.

## Ошибки

В WebSocket `v1` отдельный error envelope не определен. При ошибке backend отправляет текущий state и добавляет:

```json
{
  "error": "human-readable message"
}
```

HTTP endpoints используют обычные JSON responses с `detail` и соответствующим status code там, где это реализовано.

## Связанные документы

- [../runtime/README.md](../runtime/README.md)
- [../contracts/README.md](../contracts/README.md)
- `contracts/websocket_protocol.md`
- `apps/api/README.md`
