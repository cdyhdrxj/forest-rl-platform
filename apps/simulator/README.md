# Симулятор Unity

## Сборка

docker build -t unity-forest-simulator:latest .

## Сеть

docker network create ros-unity-net

## Имя ROS 2 шлюза

ros2-endpoint

## Запуск через compose

Основной профиль требует NVIDIA GPU:

```bash
docker compose up unity ros2 server
```

CPU-only fallback только для разработки на машинах без NVIDIA:

```bash
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up unity ros2 server
```

Проверка графического backend:

```bash
docker compose logs unity --tail=200
```

Если в логе `Renderer: llvmpipe`, Unity рендерит на CPU. Это не считается готовым GPU-режимом.

`UNITY_GRAPHICS_API=vulkan` оставлен как диагностический режим. На текущей Windows + Docker Desktop + WSL2 машине Vulkan внутри контейнера видит только `llvmpipe`, поэтому стабильный default пока `glcore`.
