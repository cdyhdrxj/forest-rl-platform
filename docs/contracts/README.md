# Контракты

Этот документ объясняет, какие контракты уже формализованы и как их менять.

## Карта контрактов

| Файл | Область | Статус |
| --- | --- | --- |
| `contracts/websocket_protocol.md` | Realtime WebSocket API | Канонический live runtime contract. |
| `contracts/openapi.yaml` | HTTP metadata | Неполный, runtime intentionally вынесен в WebSocket contract. |
| `contracts/v1/scenario.schema.json` | `scenario.json` | Стабильный JSON artifact v1. |
| `contracts/v1/preview.schema.json` | `preview.json` | Стабильный JSON artifact v1. |
| `contracts/v1/replay.schema.json` | replay JSONL line | Стабильный JSON artifact v1. |
| `contracts/v1/metrics.schema.json` | metrics export | Стабильный JSON artifact v1. |
| `contracts/v1/episode_log.schema.json` | episode log export | Стабильный JSON artifact v1. |
| `contracts/v1/scientific_suite.schema.json` | scientific suite config | MVP, scientific mode заморожен. |
| `contracts/v1/scientific_report.schema.json` | scientific report | MVP, scientific mode заморожен. |
| `contracts/v2/ros_interfaces.md` | ROS 2 interfaces | Документация к `.msg/.srv`; v2 breaking change. |
| `ros2_ws/src/forest_msgs/msg/*` | ROS messages | Source of truth для ROS types. |
| `ros2_ws/src/forest_msgs/srv/*` | ROS services | Source of truth для ROS services. |

## Версионирование

Версионирование поконтрактное:

- `v1` JSON-схемы остаются `v1`, пока конкретный JSON-артефакт не ломается несовместимо;
- ROS-интерфейсы уже имеют `v2`, потому что `forest_msgs/Event.msg` изменен несовместимо;
- перенос всего каталога `v1` в `v2` не планируется автоматически;
- новый `v2` JSON contract нужен только при реальном breaking change конкретного JSON-файла.

## WebSocket contract

Realtime API строится вокруг WebSocket routes:

- `/continuous/trail`;
- `/continuous/coverage`;
- `/discrete/patrol`;
- `/discrete/reforestation`;
- `/threed/patrol`;
- `/threed/trail`.

Основные actions:

- `generate`;
- `load`;
- `start`;
- `start_eval`;
- `stop`;
- `finish`;
- `reset`;
- `dispose`.

Подробности: `contracts/websocket_protocol.md` и [../api/README.md](../api/README.md).

## ROS contract

Source of truth:

- `ros2_ws/src/forest_msgs/msg/Event.msg`;
- `ros2_ws/src/forest_msgs/msg/EnvAction.msg`;
- `ros2_ws/src/forest_msgs/msg/StepCmd.msg`;
- `ros2_ws/src/forest_msgs/srv/Step.srv`;
- остальные `.srv` в `forest_msgs`.

`contracts/v2/ros_interfaces.md` описывает эти интерфейсы для людей, но при расхождении побеждает реальный `.msg/.srv`.

## Breaking change `Event.msg`

Принято решение не делать compatibility bridge для старого event format. `forest_msgs/Event.msg` переведен на v2:

- `robot_id`;
- `geometry_msgs/Point position`;
- v2 event code constants;
- `event_type`;
- `intruder_id`.

Если Unity/ROS-код еще отправляет старый формат, его нужно обновить под v2.

## Checklist изменения контракта

1. Изменить source of truth: JSON Schema, `.msg/.srv` или WebSocket markdown.
2. Обновить код, который сериализует/читает контракт.
3. Обновить tests, особенно schema validation и mapping tests.
4. Обновить `docs/*`, где описан внешний интерфейс.
5. Зафиксировать breaking/non-breaking характер изменения в [../contracts_status.md](../contracts_status.md).

## Текущие пробелы

- нет строгой JSON Schema для входных WebSocket messages;
- нет строгой JSON Schema для server state;
- route-specific `params` и runtime state остаются расширяемыми;
- формат ошибок WebSocket пока представлен полем `error`;
- multi-agent payloads не входят в текущий `v1`.
