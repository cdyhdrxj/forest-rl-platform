# ROS 2 интеграция

## Назначение

ROS 2 слой связывает backend и Unity/симулятор. Сейчас он нужен в первую очередь для 3D runtime:

- инициализация terrain, роботов и целей;
- live-топики наблюдений и событий;
- синхронный `/env/step` для RL-контура;
- публикация runtime events в формате `forest_msgs/Event`.

## Source of truth

Для ROS-интерфейсов source of truth - реальные файлы:

- `ros2_ws/src/forest_msgs/msg/Event.msg`;
- `ros2_ws/src/forest_msgs/msg/EnvAction.msg`;
- `ros2_ws/src/forest_msgs/msg/StepCmd.msg`;
- `ros2_ws/src/forest_msgs/srv/Step.srv`;
- `ros2_ws/src/forest_msgs/srv/SetTerrainParams.srv`;
- `ros2_ws/src/forest_msgs/srv/SetRobots.srv`;
- `ros2_ws/src/forest_msgs/srv/SetGoal.srv`.

Человеческое описание находится в `contracts/v2/ros_interfaces.md`.

Минимальный guide для разработчика Unity/ROS, который реализует синхронный step, находится в [../simulator/unity_env_step_integration.md](../simulator/unity_env_step_integration.md).

## Docker-сервис

`ros2` основан на `osrf/ros:humble-desktop`.

При сборке выполняется:

```text
colcon build --packages-select ros_tcp_endpoint forest_msgs
```

Открытые порты:

- `9090` - rosbridge websocket;
- `10000` - ROS TCP endpoint.

## Проверка интерфейсов

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/msg/Event"
```

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/srv/Step"
```

Список сервисов:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service list"
```

## Топики

| Topic | Type | Назначение |
| --- | --- | --- |
| `/robot_{id}/base_scan` | `sensor_msgs/LaserScan` | Лидар/scan робота. |
| `/robot_{id}/pose` | `geometry_msgs/PoseStamped` | Положение робота. |
| `/env/events` | `forest_msgs/Event` | Общие события среды. |
| `/robot_{id}/events` | `forest_msgs/Event` | События конкретного робота. |
| `/robot_{id}/cmd_vel` | `geometry_msgs/Twist` | Непрерывное управление. |
| `/robot_{id}/cmd_step` | `forest_msgs/StepCmd` | Дискретный шаг клеточной среды. |

## Сервисы

| Service | Type | Назначение |
| --- | --- | --- |
| `/env/generate` | `forest_msgs/srv/SetTerrainParams` | Генерация terrain. |
| `/env/set_robots` | `forest_msgs/srv/SetRobots` | Начальные позиции и типы роботов. |
| `/env/set_goal` | `forest_msgs/srv/SetGoal` | Цель или зона цели. |
| `/env/reset` | `std_srvs/srv/Trigger` | Сброс сцены. |
| `/env/step` | `forest_msgs/srv/Step` | Один синхронный RL step. |

## Канонический 3D handshake

Backend вызывает:

```text
/env/reset
/env/step(actions, dt)
```

`/env/step` возвращает:

- `success`;
- `message`;
- `observation_json`;
- `reward`;
- `terminated`;
- `truncated`;
- `info_json`;
- `events`.

`observation_json` и `info_json` пока строковые JSON-поля, чтобы не блокировать интеграцию на полном typed observation message.

## Event v2

`forest_msgs/Event.msg` v2 содержит:

- `std_msgs/Header header`;
- `int32 robot_id`;
- `geometry_msgs/Point position`;
- constants `GOAL`, `FLIP`, `COLLISION_PASSABLE`, `COLLISION_IMPASSABLE`, `INTRUDER_APPEARED`, `INTRUDER_DETECTED`, `INTRUDER_CAUGHT`;
- `uint8 event_type`;
- `int32 intruder_id`.

Backend mapping живет в `packages/schemas/event_mapping.py`. Тесты mapping - `tests/unit/test_event_mapping.py`.

## Текущий статус

- `forest_msgs` синхронизирован с `contracts/v2/ros_interfaces.md`.
- `Simulator3DService` по умолчанию ожидает `/env/step`.
- Unity/ROS часть еще должна реализовать реальный `/env/step`.
- Если `ros2 service list` не показывает `/env/step`, 3D start будет падать в sync runtime. Это ожидаемый незакрытый пункт.
