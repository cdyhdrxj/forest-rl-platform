# ROS 2 workspace

`ros2_ws` содержит ROS 2 Humble workspace для интеграции Unity/симулятора с backend. Главные локальные пакеты:

- `src/forest_msgs` - source of truth для сообщений и сервисов платформы;
- `src/ros_tcp_endpoint` - ROS TCP endpoint;
- `src/robot_adapter` - заготовка адаптера робота.

Человеческое описание ROS-контрактов находится в `../contracts/v2/ros_interfaces.md`, но при расхождении побеждают реальные `.msg/.srv` в `src/forest_msgs`.

## Основной запуск

Основной способ запуска - через compose из корня репозитория:

```powershell
docker compose up ros2
```

Обычно `ros2` поднимается вместе с backend и Unity:

```powershell
docker compose up server ros2 unity
```

Старый ручной сценарий с отдельной Docker-сетью `ros-unity-net` и образом `ros2-endpoint` оставлен только как исторический способ изолированной отладки. Для проверки платформенной интеграции используйте compose.

## Проверка интерфейсов

Показать `Step` service:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/srv/Step"
```

Показать `Event` message:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/msg/Event"
```

Список опубликованных сервисов:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service list"
```

Если `/env/step` отсутствует, это текущее ограничение Unity/ROS-части: backend 3D route будет падать при `start` в обычном `sync_step` режиме.

## Пример вызова `/env/generate`

Команда полезна только если соответствующий service уже опубликован Unity/ROS-стороной:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service call /env/generate forest_msgs/srv/SetTerrainParams '{uniform_scale: 0.1, mesh_height_multiplayer: 10.0, noise_scale: 60.0, seed: 15, octaves: 4, persistance: 0.5, lacunarity: 2.0, offset_x: 0.0, offset_y: 0.0, density: 20, max_view_dst: 500, noise_normalize_mode: 0}'"
```
