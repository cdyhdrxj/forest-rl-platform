# Статус контрактов и черновые решения

Этот файл фиксирует текущее состояние контрактов после первичного заполнения на основе текущего кода.
В нем явно перечислены допущения, на которых собраны нынешние схемы и документы для работы в реальном времени.

## Что уже можно считать извлеченным из реализации

### API времени исполнения

Из текущего кода уже можно уверенно восстановить:

- список активных WebSocket route key;
- набор действий `generate/load/start/stop/reset/dispose`;
- общий каркас dispatcher state;
- flow генерации, загрузки, запуска, остановки и replay/metrics persistence.

### Сценарии

Из `services/scenario_generator` уже можно восстановить:

- структуру `GenerationRequest`;
- структуру `GeneratedScenario`;
- формат `preview.json`;
- формат `scenario.json`;
- структуру layer manifest;
- наличие `validation_report` как обязательной смысловой части сценария.

### Телеметрия времени исполнения

Из `apps/api/runtime_monitor.py` уже можно восстановить:

- формат строк replay JSONL;
- набор snapshot-метрик;
- принцип формирования `Episode`;
- формат `EpisodeEvent` с `payload_json`.

### Соответствие событий ROS

Из `contracts/v2/ros_interfaces.md`, `packages/schemas/event_mapping.py` и `packages/db/models/enums.py` уже можно восстановить:

- набор ROS v2 event codes;
- их отображение в platform event types;
- наличие исторических алиасов событий для совместимости.

## Что уже добавлено

- `contracts/websocket_protocol.md` фиксирует текущий WebSocket runtime-протокол.
- `contracts/openapi.yaml` теперь прямо указывает, что runtime-контракт живет отдельно в WebSocket-документе.
- `contracts/v1/scenario.schema.json` и `contracts/v1/preview.schema.json` описывают сохраняемые сценарии.
- `contracts/v1/replay.schema.json` описывает одну строку replay NDJSON.
- `contracts/v1/metrics.schema.json` и `contracts/v1/episode_log.schema.json` задают канонические export-форматы.

## Принятые допущения

Текущие контракты собраны на следующих рабочих решениях:

1. Официально поддерживаются только 5 активных WebSocket routes из `apps/api/app.py`.
2. Realtime-контракт хранится отдельным markdown-файлом рядом с OpenAPI.
3. Обязательными считаются только поля состояния, добавляемые диспетчером.
4. Поля, зависящие от маршрута, разрешены как добавочные расширения.
5. Ошибки в `v1` остаются встроенными через поле `error`.
6. `scenario.schema.json` описывает сохраненный `scenario.json`.
7. `preview.json` считается частью формального контракта.
8. Replay, metrics и episode log фиксируются как канонические форматы времени исполнения и экспорта с общим базовым ядром и расширениями по режимам.
9. `contracts/v2/ros_interfaces.md` считается основной ROS-спецификацией, а `v1` сохраняется как историческая версия.
10. Структура для multi-agent явно отложена за пределы `v1`.

## Что еще остается на будущее

- оформить реальный ROS 2 message/service пакет в `ros2_ws/src/forest_interfaces`;
- при необходимости ужесточить `params` и схемы состояния, зависящие от маршрута;
- добавить тесты, валидирующие реальные артефакты против новых JSON Schema;
- решить, нужен ли в будущем AsyncAPI вместо markdown-описания WebSocket-протокола.
