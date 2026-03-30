# Контракты платформы Forest RL `v1`

Этот каталог содержит текущий набор контрактов `v1`, используемый платформой.

## Файлы

- `scenario.schema.json` - каноническая схема для сохраняемого `scenario.json`
- `preview.schema.json` - каноническая схема для сохраняемого `preview.json`
- `replay.schema.json` - схема одной NDJSON-строки в `replay_*.jsonl`
- `metrics.schema.json` - канонический JSON-формат экспорта метрик
- `episode_log.schema.json` - канонический JSON-формат экспорта эпизодов и событий
- `ros_interfaces.md` - исторический контракт ROS-интерфейсов

## Связанные контракты вне этого каталога

- `../websocket_protocol.md` - канонический контракт времени исполнения по WebSocket
- `../openapi.yaml` - HTTP-метаданные backend-сервиса
- `../v2/ros_interfaces.md` - основная ROS-спецификация событий и топиков, используемая текущей кодовой базой

## Примечания

- `scenario.json` и `preview.json` соответствуют структурам, которые сейчас пишет `services/scenario_generator/storage.py`.
- Replay-файлы являются newline-delimited JSON. Схема replay применяется к каждой строке, а не ко всему файлу как к одному JSON-документу.
- Схемы метрик и журнала эпизодов задают канонический export-формат для данных, которые сейчас в основном сохраняются в базе.
- Route-specific runtime-поля остаются расширяемыми внутри replay-записей и WebSocket state snapshots.
