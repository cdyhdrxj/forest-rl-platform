# 3D runtime contract

Дата ревизии: 2026-05-30.

## Решение

Канонический RL-контур для `threed/trail` и `threed/patrol` работает синхронно через `/env/step`.

```text
reset(config) -> observation, info
step(action) -> observation, reward, terminated, truncated, info
```

Live-топики ROS (`/robot_{id}/pose`, `/robot_{id}/base_scan`, `/env/events`) остаются каналом мониторинга и визуализации. Они не заменяют step-handshake для обучения.

## ROS API

- `/env/generate` - подготовка terrain.
- `/env/set_robots` - начальные позиции роботов.
- `/env/set_goal` - целевая точка или параметры цели.
- `/env/reset` - сброс сцены.
- `/env/step` - один синхронный шаг среды, тип `forest_msgs/srv/Step`.

Источник правды для ROS-интерфейсов - файлы `.msg/.srv` в `ros2_ws/src/forest_msgs`. `contracts/v2/ros_interfaces.md` является документацией к ним.

Практический checklist для Unity/ROS-разработчика: [../simulator/unity_env_step_integration.md](../simulator/unity_env_step_integration.md).

## Action

`forest_msgs/EnvAction` поддерживает два типа действия:

- `TWIST` - непрерывная команда `geometry_msgs/Twist` для 3D/2D continuous.
- `GRID_STEP` - дискретное действие `UP/DOWN/LEFT/RIGHT/STAY` для клеточного режима.

Для `threed/trail` базовый action space - continuous `Twist`.

Для `threed/patrol` базовый action space тоже `Twist`; дискретная политика может быть отдельным adapter layer, который переводит дискретные действия в `Twist`.

## Observation

На первом этапе `/env/step` возвращает `observation_json`, чтобы не блокировать интеграцию на полном typed ROS-сообщении наблюдения.

Минимальные ожидаемые поля:

- `agent_pos`: `[[x, y], ...]`;
- `goal_pos`: `[[x, y], ...]`;
- `trajectory`: `[[x, y], ...]`, если симулятор ведет траекторию;
- sensor summary: по возможности lidar/scan summary или ссылка на актуальный `/robot_{id}/base_scan`.

## Reward и done

Backend является владельцем платформенной семантики `reward`, `terminated`, `truncated` и episode/replay persistence.

Unity/ROS возвращает физическое состояние и события шага. Если Unity уже считает reward/done, backend может принять эти значения, но они должны быть явно описаны в `info_json`.

## Synthetic mode

Синтетический цикл `Simulator3DService` сохраняется только для тестов dispatcher/runtime observer.

Включение:

```text
SIMULATOR_3D_SYNTHETIC=1
```

или параметр запуска:

```json
{"synthetic": true}
```

Обычный runtime по умолчанию - `sync_step`.
