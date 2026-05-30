# Симулятор Unity

Этот каталог содержит Docker-обертку для готового Linux build Unity simulator (`linux_build/`) и entrypoint для headless-запуска внутри общего compose-стека.

## Основной запуск

Основной способ запуска - из корня репозитория через `docker-compose.yml`, потому что Unity должна работать вместе с `server` и `ros2`:

```bash
docker compose up unity ros2 server
```

Основной профиль требует NVIDIA GPU. CPU-only fallback только для разработки на машинах без NVIDIA:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up unity ros2 server
```

Подробнее о GPU/CPU политике и диагностике: `../../docs/infrastructure/docker.md`.

## Локальная сборка образа

Если нужно проверить только Dockerfile симулятора, можно собрать образ вручную из этого каталога:

```bash
docker build -t unity-forest-simulator:latest .
```

Ручная сборка не поднимает ROS 2, backend и общую сеть проекта. Для end-to-end проверки используйте compose из корня репозитория.

## ROS/Unity runtime

`Simulator3DService` ожидает, что Unity/ROS реализует:

- `/env/generate`;
- `/env/set_robots`;
- `/env/set_goal`;
- `/env/reset`;
- `/env/step`.

Минимальный guide по `/env/step`: `../../docs/simulator/unity_env_step_integration.md`.

Старый ручной сценарий с отдельной сетью `ros-unity-net` и контейнером `ros2-endpoint` больше не является основным путем запуска. Он может быть полезен только для изолированной отладки ROS TCP endpoint.

## Диагностика

Проверка графического backend:

```bash
docker compose logs unity --tail=200
```

Если в логе `Renderer: llvmpipe`, Unity рендерит на CPU. Это не считается готовым GPU-режимом.

`UNITY_GRAPHICS_API=vulkan` оставлен как диагностический режим. На текущей Windows + Docker Desktop + WSL2 машине Vulkan внутри контейнера видит только `llvmpipe`, поэтому стабильный default пока `glcore`.
