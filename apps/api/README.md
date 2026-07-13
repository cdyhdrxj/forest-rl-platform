# API и диспетчер экспериментов

Сервис `apps/api` поднимает FastAPI-приложение и публикует WebSocket-маршруты,
через которые фронтенд управляет генерацией сценариев, загрузкой рантайма и запуском обучения.

Каноническое описание live runtime-протокола находится в:

- `contracts/websocket_protocol.md`
- `docs/api/README.md`

`contracts/openapi.yaml` сейчас содержит только HTTP-метаданные и ссылку на WebSocket-контракт. Не используйте его как полную спецификацию backend API.

Помимо runtime routes, backend подключает вспомогательные WebRTC-signaling endpoints из `webrtc_routes.py`. Они нужны для Unity video stream и не являются частью lifecycle `generate/load/start/stop`.

## Запуск

### Локально через Python

Из корня репозитория:

```powershell
python apps/api/main.py
```

По умолчанию сервер слушает `http://127.0.0.1:8000`.

Если `DATABASE_URL` не задан, backend использует SQLite `data/platform_dev.sqlite3`. Это нормальный быстрый smoke-режим для разработки. Для проверки с PostgreSQL, поднятым через compose, задайте host-URL перед запуском:

```powershell
$env:DATABASE_URL = "postgresql://forest:forest@localhost:5432/forest_rl"
alembic upgrade head
python apps/api/main.py
```

URL из `.env` вида `postgresql://forest:forest@postgres:5432/forest_rl` предназначен для контейнеров внутри docker-compose сети; локальный Python-процесс на хосте должен использовать `localhost`.

### Через Docker

Первый запуск или пересборка:

```bash
docker compose up --build server
```

Повторный запуск:

```bash
docker compose up server
```

## Поддерживаемые WebSocket-маршруты

Активные маршруты определены в `apps/api/app.py`:

- `/continuous/trail`
- `/continuous/coverage`
- `/discrete/patrol`
- `/discrete/reforestation`
- `/threed/patrol`
- `/threed/trail`

Закомментированные маршруты не считаются частью текущего публичного интерфейса.

## Вспомогательные WebRTC endpoints

`setup_webrtc_routes(...)` добавляет:

- `GET /webrtc/config` - конфигурация WebRTC signaling mode;
- `WS /ws` - основной signaling канал текущего frontend `WebRTCPlayer`;
- `WS /signaling` - совместимый signaling endpoint.

Карта frontend endpoint'ов находится в `apps/web/src/constants/envs.js`. Текущий player использует `WebrtcConfig` и `WebrtcWs`; `WebrtcSignaling` относится к старому HTTP polling-клиенту и backend endpoint `/webrtc/signaling` сейчас не публикует.

## Как устроен запрос

Клиент отправляет JSON-объект вида:

```json
{
  "action": "generate",
  "params": {}
}
```

Поддерживаемые действия:

- `generate` — сгенерировать сценарий и загрузить его в сессию;
- `load` — загрузить существующий `run_id` или `scenario_version_id`;
- `start` — запустить загруженную сессию;
- `start_eval` — запустить evaluation из checkpoint другого run;
- `stop` — остановить выполнение;
- `finish` — финализировать run со статусом `finished`;
- `reset` — сбросить состояние и повторно загрузить сценарий;
- `dispose` — освободить текущую сессию.

Дополнительные поля:

- `run_id` — для повторной загрузки существующего запуска;
- `scenario_version_id` — для загрузки сохранённой версии сценария;
- `source_run_id` — для `start_eval`, чтобы взять checkpoint из другого run;
- `params` — параметры генерации, загрузки или старта.

## Как устроен ответ

Сервер непрерывно отправляет снимки состояния в JSON.
В каждом сообщении есть общий слой полей от `ExperimentDispatcher`, а также
специфические поля конкретного runtime-сервиса.

Общие поля:

- `running`
- `route_key`
- `environment_kind`
- `task_kind`
- `run_id`
- `scenario_version_id`
- `scenario_loaded`
- `scenario_generated`
- `execution_phase`

Когда сценарий уже загружен, дополнительно приходят:

- `world_file_uri`
- `preview_uri`
- `validation_passed`
- `validation_messages`
- `validation_report`
- `error` — если во время выполнения произошла ошибка

Подробная структура состояния и набор зависящих от маршрута полей описаны в `contracts/websocket_protocol.md`.

## Основные модули

- `app.py` — объявляет FastAPI-приложение и WebSocket-маршруты;
- `webrtc_routes.py` — добавляет WebRTC signaling endpoints для Unity stream;
- `websocket_manager.py` — управляет сокетом, приёмом команд и отправкой состояния;
- `dispatcher.py` — связывает маршруты с генерацией сценариев, БД, runtime-сервисами и наблюдением за запуском;
- `runtime_monitor.py` — пишет replay, метрики, события эпизодов и сервисные логи.

## Поток выполнения

1. Фронтенд подключается к одному из WebSocket-маршрутов.
2. `handle_ws(...)` принимает команду клиента.
3. `ExperimentDispatcher` создаёт или загружает `run` и связывает его со сценарием.
4. Сервис исполнения получает `load_scenario(...)` и затем `start(...)`.
5. `RunObserver` сохраняет replay, метрики и события.
6. Сервер продолжает отправлять клиенту текущее состояние, пока сокет открыт.
