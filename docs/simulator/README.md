# Unity 3D simulator

## Роль симулятора

Unity simulator должен быть физическим 3D runtime для маршрутов:

- `threed/trail`;
- `threed/patrol`.

Backend отвечает за dispatcher, replay, metrics и хранение. Unity/ROS отвечает за физику, сенсоры, события и синхронный step.

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
