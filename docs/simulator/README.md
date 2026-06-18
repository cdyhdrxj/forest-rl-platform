# Unity 3D simulator

## Роль симулятора

Unity simulator должен быть физическим 3D runtime для маршрутов:

- `threed/trail`;
- `threed/patrol`.

Backend отвечает за dispatcher, replay, metrics и хранение. Unity/ROS отвечает за физику, сенсоры, события и синхронный step.

Если вы реализуете Unity/ROS-сторону `/env/step`, начните с короткого внешнего guide: [unity_env_step_integration.md](unity_env_step_integration.md).

## Контур запуска

```text
docker compose
  -> ros2
  -> server
  -> unity
```

`Simulator3DService` при загрузке сценария вызывает ROS init services:

- `/env/generate`;
- `/env/set_robots`;
- `/env/set_goal`.

При старте обычного 3D runtime:

- вызывается `/env/reset`;
- затем в цикле вызывается `/env/step forest_msgs/srv/Step`;
- response преобразуется в platform state;
- events сохраняются через `RunObserver`.

## Прием данных генерации карты

Для 3D симулятора backend не передает готовый `terrain_map`. Карта строится процедурно на стороне Unity по seed и параметрам шума. `terrain_map` остается форматом preview/layer для 2D и grid-сред.

При `generate` dispatcher сохраняет `GeneratedScenario`, а `Simulator3DService.load_scenario(...)` отправляет в ROS три группы параметров:

| Группа | ROS service | Что делает симулятор |
| --- | --- | --- |
| `map_config` | `/env/generate` (`forest_msgs/srv/SetTerrainParams`) | Строит terrain и статические объекты процедурно. |
| `robot_config` | `/env/set_robots` (`forest_msgs/srv/SetRobots`) | Задает стартовые позиции и типы роботов. |
| `target_config` | `/env/set_goal` (`forest_msgs/srv/SetGoal`) | Задает цель или первую runtime-цель. |

`world_descriptor` хранится в `scenario.json` и state как человекочитаемое описание мира: источник terrain, seed, `map_config`, `robot_config`, `target_config`, `max_steps`. Сейчас это не отдельный ROS service, а сохраненная обертка вокруг фактических ROS-параметров.

### Поля `map_config`

Текущий ROS source of truth - `ros2_ws/src/forest_msgs/srv/SetTerrainParams.srv`:

- `uniform_scale`;
- `mesh_height_multiplayer`;
- `noise_scale`;
- `seed`;
- `octaves`;
- `persistance`;
- `lacunarity`;
- `offset_x`;
- `offset_y`;
- `density`;
- `max_view_dst`;
- `noise_normalize_mode`.

`density` - это плотность процедурно размещаемых статических объектов в Unity. Если текущая сцена генерирует только деревья, симулятор может трактовать ее как плотность деревьев. Если появятся камни, кусты, валежник или другие классы, нужно расширить контракт типизированными плотностями, а не перегружать `tree_density`.

`terrain_hilliness` не является полем ROS-контракта. Для 3D сейчас используются прямые параметры шума и высоты: `mesh_height_multiplayer`, `noise_scale`, `octaves`, `lacunarity`. Высокоуровневый слайдер `terrain_hilliness` можно оставить только как UI alias, который backend преобразует в параметры шума.

### Preview-поля

`preview_payload` нужен UI и быстрому state snapshot. Для 3D это не источник построения сцены.

- `agent_pos` - старт робота в 2D-проекции сверху;
- `goal_pos` - цель или preview-позиции целей в 2D-проекции сверху;
- `landmark_pos` - статические ориентиры/препятствия для 2D preview. В текущем 3D контракте они не используются и обычно пустые.

Для 2D/grid `landmark_pos` часто означает препятствия или недоступные клетки. Для 3D, если нужны реальные ориентиры, их надо оформить отдельным typed layer или отдельным ROS-параметром, иначе это поле останется только визуальным preview.

### Что должно быть реализовано в Unity/ROS

1. `/env/generate` должен детерминированно строить terrain и статические объекты по `SetTerrainParams`.
2. `/env/set_robots` должен сохранить стартовые позы до `/env/reset`.
3. `/env/set_goal` должен сохранить цель до `/env/reset`.
4. `/env/reset` должен очистить текущую сцену и применить последние параметры generate/robots/goal.
5. `/env/step` должен вернуть реальное `observation_json`, `reward`, `terminated`, `truncated`, `info_json` и события шага.

## Synthetic mode

Synthetic mode оставлен только для тестов dispatcher/runtime observer.

Включение:

```powershell
$env:SIMULATOR_3D_SYNTHETIC="1"
```

или:

```json
{
  "synthetic": true
}
```

Без этого 3D runtime использует `sync_step`.

## GPU/CPU режимы

Основной compose требует NVIDIA GPU. CPU fallback:

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build unity ros2 server
```

Диагностика:

```powershell
docker compose exec unity nvidia-smi
docker compose logs unity --tail=200
```

`nvidia-smi` подтверждает доступность GPU контейнеру. Реальный GPU renderer подтверждается только логом Unity с NVIDIA renderer. `llvmpipe` означает CPU rendering.

## Текущее состояние

Что уже есть:

- Docker entrypoint исправлен для Linux line endings;
- Unity контейнер стартует без restart loop;
- NVIDIA runtime виден внутри контейнера;
- добавлены runtime libraries, нужные текущему Unity build;
- backend 3D service переведен на sync `/env/step`;
- ROS interfaces для `/env/step` добавлены в `forest_msgs`.

Что еще не закрыто:

- Unity внутри Docker пока может рендерить через `llvmpipe`;
- `/env/step` должен быть реализован на стороне Unity/ROS;
- наблюдение, reward, terminated/truncated и info должны наполняться реальными данными симуляции;
- нужен интеграционный тест: ROS event -> platform event -> replay/episode event.

## Минимальные требования к `/env/step`

Request:

- `forest_msgs/EnvAction[] actions`;
- `float32 dt`.

Response:

- `bool success`;
- `string message`;
- `string observation_json`;
- `float32 reward`;
- `bool terminated`;
- `bool truncated`;
- `string info_json`;
- `forest_msgs/Event[] events`.

Минимальный `observation_json`:

```json
{
  "agent_pos": [[0.0, 0.0]],
  "goal_pos": [[10.0, 10.0]],
  "trajectory": [[0.0, 0.0]]
}
```

Допустимы дополнительные поля, если backend не теряет базовые `agent_pos`, `goal_pos`, `trajectory` и события.
