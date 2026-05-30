# Документация ForestRobotTwin

Дата ревизии: 2026-05-30.

Этот каталог описывает текущее состояние проекта, а не только целевую архитектуру. Документация рассчитана на внешнего разработчика, который впервые открывает репозиторий и должен понять, что уже работает, где находятся источники правды и какие части еще не закрыты.

## Быстрый маршрут чтения

1. [getting_started.md](getting_started.md) - запуск проекта через Docker и локально.
2. [architecture/README.md](architecture/README.md) - компоненты платформы и поток данных.
3. [runtime/README.md](runtime/README.md) - жизненный цикл run, dispatcher, runtime-сервисы и observer.
4. [api/README.md](api/README.md) - WebSocket и HTTP-интерфейсы backend.
5. [contracts/README.md](contracts/README.md) - карта контрактов и правила версионирования.
6. [scenarios/README.md](scenarios/README.md) - генерация, сохранение и повторная загрузка сценариев.
7. [database/README.md](database/README.md) - модель хранения в PostgreSQL и файловых артефактах.
8. [infrastructure/docker.md](infrastructure/docker.md) - compose-сервисы, GPU/CPU режимы и диагностика.
9. [ros/README.md](ros/README.md) - ROS 2 workspace, `forest_msgs` и 3D handshake.
10. [simulator/README.md](simulator/README.md) - Unity/ROS 3D runtime и текущие ограничения.
11. [simulator/unity_env_step_integration.md](simulator/unity_env_step_integration.md) - минимальный guide для Unity/ROS-разработчика, который реализует `/env/step`.
12. [testing.md](testing.md) - быстрые проверки, интеграционные тесты и известные caveats.
13. [experiments/README.md](experiments/README.md) - эксперименты и замороженный scientific mode.
14. [glossary.md](glossary.md) - основные термины проекта.
15. [TODO.md](TODO.md) - открытые задачи.

## Первые ориентиры для внешнего разработчика

- `ForestRobotTwin` - название платформы и предметной области; `forest-rl-platform` - имя текущего репозитория/пакета.
- Самый надежный первый маршрут - поднять backend и frontend, проверить `GET /api/health`, затем запустить 2D/grid route (`continuous/trail`, `discrete/patrol` или `discrete/reforestation`). 3D routes сейчас полезны для проверки интеграционной обвязки, но реальный RL loop ждет `/env/step` в Unity/ROS.
- Docker-запуск с Unity по умолчанию требует NVIDIA GPU. Для разработки без NVIDIA используйте CPU-only compose override, а для чистого backend-smoke можно запускать Python локально с SQLite fallback.
- Если документация расходится с кодом, source of truth указан в таблице ниже. Для HTTP endpoints это `apps/api/app.py`, для runtime routes - `apps/api/dispatcher.py`, для ROS - реальные `.msg/.srv`.

## Проект в одном абзаце

ForestRobotTwin - платформа для моделирования, обучения, запуска и анализа алгоритмов поведения агентов в лесной среде. В системе есть генератор сценариев, runtime-сервисы для разных задач, FastAPI/WebSocket backend, React/Vite клиент, PostgreSQL-хранилище и задел под Unity + ROS 2 3D-симулятор.

## Главный поток данных

```text
Web client
  -> WebSocket/HTTP API
  -> ExperimentDispatcher
  -> ScenarioGenerator
  -> RuntimeService
  -> RunObserver
  -> PostgreSQL + data/
```

Для 3D-режимов runtime дополнительно идет через ROS 2 и Unity:

```text
Simulator3DService
  -> rosbridge / ROS TCP endpoint
  -> Unity simulator
  -> forest_msgs events/services
```

## Основные каталоги

| Каталог | Назначение |
| --- | --- |
| `apps/api` | FastAPI backend, WebSocket routes, dispatcher, observer, HTTP endpoints. |
| `apps/web` | React + Vite клиент. |
| `apps/simulator` | Docker-обертка Unity build и entrypoint для headless-запуска. |
| `services/scenario_generator` | Общая генерация и сохранение сценариев. |
| `services/*` | Runtime-сервисы предметных режимов. |
| `packages/db` | SQLAlchemy-модели, миграции и DB session. |
| `packages/schemas` | Общие Pydantic/enum/schema helpers. |
| `contracts` | Формальные JSON/ROS/WebSocket контракты. |
| `ros2_ws` | ROS 2 workspace, включая `forest_msgs`. |
| `data` | Сценарии, replay и runtime-артефакты. |
| `tests` | Unit, integration и e2e проверки. |

Некоторые каталоги являются заготовками или историческими прототипами, а не готовыми runtime-компонентами. Перед использованием проверьте локальный README: это особенно важно для `apps/worker`, `services/marl_coordination`, `services/evaluation`, `services/replay_builder`, `services/robot_control_base` и `services/trail_planning`.

## Поддерживаемые runtime-маршруты

| Route key | Среда | Задача | Статус |
| --- | --- | --- | --- |
| `continuous/trail` | `continuous_2d` | прокладка тропы | рабочий 2D runtime |
| `continuous/coverage` | `continuous_2d` | покрытие междурядий | используется scientific MVP, развитие заморожено |
| `discrete/patrol` | `grid` | патрулирование | рабочий grid runtime |
| `discrete/reforestation` | `grid` | посадка саженцев | рабочий grid runtime |
| `threed/trail` | `simulator_3d` | тропа в 3D | контракт задан, реальный `/env/step` в Unity/ROS еще нужен |
| `threed/patrol` | `simulator_3d` | патруль в 3D | контракт задан, реальный `/env/step` в Unity/ROS еще нужен |

Важно различать backend route и видимость в текущем UI. Backend объявляет все шесть WebSocket routes из таблицы. В селекторе нового эксперимента frontend сейчас показывает `continuous/trail`, `continuous/coverage`, `discrete/patrol`, `discrete/reforestation` и `threed/trail`; `threed/patrol` есть в `WS_MAP`, но не включен в `TASKS_BY_ENV` для ручного выбора. Если нужно открыть его в UI, обновите `apps/web/src/constants/envs.js`.

## Источники правды

| Область | Смотреть в первую очередь |
| --- | --- |
| WebSocket runtime API | `contracts/websocket_protocol.md`, `apps/api/websocket_manager.py` |
| HTTP endpoints | `apps/api/app.py`, затем `docs/api/README.md` |
| Unity WebRTC stream | `apps/api/webrtc_routes.py`, `apps/web/src/components/WebRTCPlayer.jsx` |
| Runtime routes | `apps/api/dispatcher.py` |
| Сценарии | `services/scenario_generator/*`, `contracts/v1/scenario.schema.json`, `contracts/v1/preview.schema.json` |
| Replay/metrics/episodes | `apps/api/runtime_monitor.py`, `contracts/v1/*` |
| DB schema | `packages/db/models/*`, `packages/db/migrations/*` |
| ROS interfaces | `ros2_ws/src/forest_msgs/msg/*`, `ros2_ws/src/forest_msgs/srv/*` |
| 3D runtime contract | `docs/architecture/3d_runtime_contract.md`, `contracts/v2/ros_interfaces.md` |
| Docker/runtime env | `docker-compose.yml`, `docker-compose.cpu.yml`, `apps/simulator/entrypoint.unity.sh` |

## Что важно знать сразу

- Основной runtime API сейчас WebSocket, а не REST.
- `contracts/openapi.yaml` не является полным описанием backend API.
- Основной `docker-compose.yml` требует NVIDIA GPU для Unity. Для машин без NVIDIA есть явный dev-only override `docker-compose.cpu.yml`.
- В контейнере Unity GPU уже проброшен на уровне `nvidia-smi`, но реальный renderer все еще может быть `llvmpipe`. Это открытая инфраструктурная задача.
- Для 3D выбран синхронный RL handshake `/env/step`. В Unity/ROS его еще нужно реализовать.
- Synthetic 3D loop оставлен только для тестов и должен включаться явно.
- Scientific mode заморожен: текущий MVP остается, полный набор из ТЗ не внедряется без отдельного решения.

## Открытые вопросы

Краткий список находится в [TODO.md](TODO.md). Архитектурные решения и незакрытые пункты по GPU, 3D runtime, контрактам и scientific mode собраны в [architecture/open_questions.md](architecture/open_questions.md).
