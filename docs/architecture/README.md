# Архитектура платформы

Этот документ описывает текущее состояние архитектуры проекта. Исторические материалы оставлены рядом:

- `ENVIRONMENT_GENERATION_ARCHITECTURE.md`;
- `docs/architecture/forest_robot_twin_architecture.drawio`;
- `docs/architecture/forest_robot_twin_architecture.jpg`.

Целевое ТЗ scientific mode находится в `docs/experiments/scientific_mode_tz.md`, но развитие scientific mode сейчас заморожено.

## Архитектурная схема

```text
apps/web
  -> apps/api WebSocket/HTTP
  -> ExperimentDispatcher
      -> services/scenario_generator
      -> RuntimeService
      -> RunObserver
  -> packages/db + data/

3D branch:
RuntimeService -> rosbridge/ROS TCP -> Unity simulator -> forest_msgs
```

## Компоненты

### Web client

`apps/web` - React + Vite приложение. Оно:

- выбирает route/mode;
- отправляет WebSocket actions;
- отображает preview и live state;
- показывает список runs и replay;
- опционально подключает Unity WebRTC stream через `WebRTCPlayer`.

### API backend

`apps/api` содержит:

- FastAPI app;
- WebSocket endpoints;
- HTTP endpoints для runs/replay/checkpoint;
- WebRTC signaling endpoints для Unity stream;
- `ExperimentDispatcher`;
- `RunObserver`;
- export helpers для результатов run.

Backend является центром orchestration. Он не должен знать внутреннюю физику среды, но отвечает за единый lifecycle, storage и persistence.
WebRTC endpoints обслуживают только видеопоток/интерактивный stream Unity и не являются runtime lifecycle API.

### Scenario generator

`services/scenario_generator` генерирует общий формат сценария:

- `GenerationRequest`;
- `GeneratedScenario`;
- layers;
- `preview_payload`;
- `runtime_context`;
- `validation_report`;
- `scenario.json`;
- `preview.json`.

Один и тот же контур генерации используется для 2D, grid и 3D routes.

### Runtime services

| Route key | Service | Назначение |
| --- | --- | --- |
| `continuous/trail` | `CamarService` | Непрерывная 2D среда прокладки тропы. |
| `continuous/coverage` | `AgrocareCoverageService` | Headless coverage runtime для scientific MVP. |
| `discrete/patrol` | `GridWorldService` | Клеточное патрулирование. |
| `discrete/reforestation` | `SeedlingPlantingService` | Клеточная посадка саженцев. |
| `threed/trail` | `Simulator3DService` | 3D trail adapter к Unity/ROS. |
| `threed/patrol` | `Simulator3DService` | 3D patrol adapter к Unity/ROS. |

Минимальный interface runtime-сервиса описан в [../runtime/README.md](../runtime/README.md).

### Storage

Хранение разделено на два слоя:

- PostgreSQL через `packages/db` - metadata, runs, episodes, metrics, events, artifacts;
- файловое хранилище `data/` - scenario files, preview, layers, replay и крупные артефакты.

Обученные модели хранятся как checkpoint-файлы в `data/runs/run_<id>/...`, описываются строкой `models` и регистрируются как связанный `ArtifactType.model_checkpoint`.

### ROS/Unity

3D слой состоит из:

- `apps/simulator` - Unity build в Docker;
- `ros2_ws` - ROS 2 Humble workspace;
- `forest_msgs` - сообщения и сервисы;
- `Simulator3DService` - backend adapter.

Каноническая 3D модель - синхронный `/env/step`, а ROS topics остаются live-мониторингом.

## Поток run

1. Клиент открывает WebSocket route.
2. Клиент отправляет `generate` или `load`.
3. Dispatcher строит/загружает scenario.
4. Dispatcher создает или переиспользует DB rows.
5. Runtime service получает `load_scenario(...)`.
6. Клиент отправляет `start`.
7. Runtime service начинает выполнение.
8. RunObserver пишет replay, metrics, episodes и events.
9. Dispatcher отдает state snapshots клиенту.
10. Run завершается через `finish`, `stop`, `reset`, `dispose` или ошибку.

## Контракты и версии

Основные правила:

- WebSocket runtime contract - `contracts/websocket_protocol.md`;
- JSON artifacts - `contracts/v1/*.schema.json`;
- ROS interfaces - реальные `.msg/.srv` в `ros2_ws/src/forest_msgs`;
- `contracts/v2/ros_interfaces.md` - документация к ROS v2;
- `v2` не означает перенос всех JSON-схем из `v1`.

Подробнее: [../contracts/README.md](../contracts/README.md).

## Текущее состояние 3D

Принято:

- основной 3D runtime - synchronous `/env/step`;
- synthetic mode - только для тестов;
- `forest_msgs/Event.msg` переведен на v2 breaking change без compatibility bridge;
- основной compose требует GPU, CPU fallback вынесен отдельно.

Не закрыто:

- Unity renderer внутри Docker еще может быть `llvmpipe`;
- Unity/ROS должен реализовать `/env/step`;
- real observation/reward/done/info должны прийти из симуляции;
- нужен end-to-end тест real ROS event -> platform event -> replay.

## Источники правды

| Вопрос | Source of truth |
| --- | --- |
| Routes | `apps/api/dispatcher.py` |
| WebSocket handling | `apps/api/websocket_manager.py` |
| HTTP endpoints | `apps/api/app.py` |
| WebRTC signaling | `apps/api/webrtc_routes.py`, `apps/web/src/components/WebRTCPlayer.jsx` |
| Runtime observer | `apps/api/runtime_monitor.py` |
| Scenario format | `services/scenario_generator`, `contracts/v1/scenario.schema.json` |
| DB model | `packages/db/models/*`, `packages/db/migrations/*` |
| ROS messages/services | `ros2_ws/src/forest_msgs/msg/*`, `ros2_ws/src/forest_msgs/srv/*` |
| Docker runtime | `docker-compose.yml`, `docker-compose.cpu.yml` |

## Открытые архитектурные вопросы

См. [open_questions.md](open_questions.md) и [../TODO.md](../TODO.md).
