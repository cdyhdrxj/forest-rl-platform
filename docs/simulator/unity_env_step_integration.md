# Unity `/env/step` integration guide

Этот документ описывает минимальную интеграцию Unity/ROS-симулятора с backend routes `threed/trail` и `threed/patrol`. Он рассчитан на разработчика симулятора, который не работает внутри backend-кода каждый день.

## Цель интеграции

Backend уже умеет:

- генерировать и сохранять 3D scenario;
- вызывать init-сервисы `/env/generate`, `/env/set_robots`, `/env/set_goal`;
- запускать `Simulator3DService` в режиме `sync_step`;
- сохранять replay, metrics и events через `RunObserver`.

Unity/ROS должен закрыть недостающую часть: реализовать реальный синхронный RL step `/env/step` и вернуть состояние среды после каждого действия.

## Source of truth

Формальные ROS-типы находятся в `ros2_ws/src/forest_msgs`:

- `srv/SetTerrainParams.srv`;
- `srv/SetRobots.srv`;
- `srv/SetGoal.srv`;
- `srv/Step.srv`;
- `msg/EnvAction.msg`;
- `msg/Event.msg`;
- `msg/StepCmd.msg`.

Человеческое описание контрактов: `contracts/v2/ros_interfaces.md`.

## Lifecycle, который ожидает backend

1. `load_scenario(...)` вызывает `/env/generate` с `map_config`.
2. Затем вызывает `/env/set_robots` с `robot_config`.
3. Затем вызывает `/env/set_goal` с `target_config`.
4. `start(...)` вызывает `/env/reset`.
5. После reset backend в цикле вызывает `/env/step(actions, dt)`.
6. Каждый response преобразуется в platform state и попадает в replay.

Важно: `/env/reset` должен применить последние параметры generate/robots/goal. Если Unity очищает сцену, она не должна терять эти настройки.

## Минимальная реализация `/env/step`

Тип сервиса: `forest_msgs/srv/Step`.

Request:

```text
forest_msgs/EnvAction[] actions
float32 dt
```

Response:

```text
bool success
string message
string observation_json
float32 reward
bool terminated
bool truncated
string info_json
forest_msgs/Event[] events
```

Если шаг выполнен, верните `success=true`. Если симулятор не может выполнить шаг, верните `success=false`, заполните `message`, а backend переведет run в ошибочное состояние.

## Action mapping

`EnvAction.action_type`:

- `TWIST=0` - использовать поле `twist` как `geometry_msgs/Twist`;
- `GRID_STEP=1` - использовать поле `step_action` как дискретный шаг `UP/DOWN/LEFT/RIGHT/STAY`.

Для текущих 3D routes базовый ожидаемый action - `TWIST`. Если политика дискретная, adapter должен явно переводить дискретное действие в движение Unity-робота.

## Минимальный `observation_json`

`observation_json` - строка с JSON. Минимум, который backend/UI смогут отобразить:

```json
{
  "agent_pos": [[0.0, 0.0]],
  "goal_pos": [[10.0, 10.0]],
  "trajectory": [[0.0, 0.0]]
}
```

Дополнительные поля допустимы. Рекомендуемые поля:

- `agent_heading`;
- `velocity`;
- `scan_summary`;
- `distance_to_goal`;
- `collisions`;
- `coverage_ratio` для patrol/coverage-подобных режимов.

Координаты в `agent_pos`, `goal_pos` и `trajectory` должны быть 2D-проекцией сверху в одной и той же системе координат, чтобы UI не смешивал оси.

## `info_json`

`info_json` тоже строка с JSON. Используйте его для диагностической и route-specific информации:

```json
{
  "reward_terms": {
    "progress": 0.2,
    "collision_penalty": 0.0
  },
  "done_reason": null,
  "sim_time": 12.4
}
```

Если Unity считает reward/done самостоятельно, опишите составляющие reward и причину завершения именно здесь.

## Events

События шага возвращаются в `events` как `forest_msgs/Event`.

Поддерживаемые `event_type`:

- `GOAL=0`;
- `FLIP=1`;
- `COLLISION_PASSABLE=2`;
- `COLLISION_IMPASSABLE=3`;
- `INTRUDER_APPEARED=4`;
- `INTRUDER_DETECTED=5`;
- `INTRUDER_CAUGHT=6`.

Заполняйте:

- `robot_id`;
- `position`;
- `event_type`;
- `intruder_id`, либо `-1`, если событие не связано с нарушителем.

Backend mapping живет в `packages/schemas/event_mapping.py`, проверка - `tests/unit/test_event_mapping.py`.

## Smoke-проверки

Проверить, что тип сервиса виден:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/srv/Step"
```

Проверить, что сервис опубликован:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service list"
```

В списке должен быть `/env/step`. Если его нет, backend 3D route ожидаемо падает при `start` в обычном `sync_step` режиме.

Для backend-only тестов можно включить synthetic mode, но это не проверяет Unity:

```powershell
$env:SIMULATOR_3D_SYNTHETIC = "1"
```

## Definition of done

Интеграцию можно считать минимально готовой, когда:

- `/env/generate`, `/env/set_robots`, `/env/set_goal`, `/env/reset`, `/env/step` доступны в ROS;
- `/env/step` возвращает `success=true` и валидный JSON в `observation_json`;
- `agent_pos`, `goal_pos`, `trajectory` меняются согласованно после actions;
- хотя бы одно реальное событие Unity проходит путь `forest_msgs/Event -> backend mapping -> replay`;
- 3D run запускается без synthetic mode и не падает на отсутствии `/env/step`.
