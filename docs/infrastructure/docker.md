# Docker и инфраструктура

## Compose-сервисы

| Сервис | Контейнер | Порты | Назначение |
| --- | --- | --- | --- |
| `postgres` | `postgres` | `5432:5432` | PostgreSQL 15 для metadata, runs, metrics, episodes. |
| `pgadmin` | `pgadmin` | `5050:80` | Web UI для PostgreSQL. |
| `migrate` | `migrate` | нет | Одноразовый запуск Alembic migrations. |
| `server` | `server` | `8000:8000` | FastAPI backend. |
| `client` | `client` | `5173:5173` | React/Vite frontend. |
| `ros2` | `ros2` | `9090:9090`, `10000:10000` | ROS 2 Humble, rosbridge, ROS TCP endpoint, `forest_msgs`. |
| `unity` | `unity` | `10001:10000` | Unity simulator build. |

## Основной запуск

```powershell
docker compose up --build
```

Повторный запуск:

```powershell
docker compose up -d
```

Остановить сервисы:

```powershell
docker compose down
```

## GPU policy для Unity

Принятое решение:

- если NVIDIA GPU доступен, Unity должна использовать GPU;
- основной `docker-compose.yml` требует NVIDIA GPU;
- CPU fallback разрешен только через явный override для разработчиков без NVIDIA.

В основном compose для `unity` заданы:

- `gpus: all`;
- `NVIDIA_VISIBLE_DEVICES=all`;
- `NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute,video,display`;
- `UNITY_REQUIRE_NVIDIA=1`;
- `UNITY_SOFTWARE_RENDERING=0`;
- `UNITY_GRAPHICS_API=glcore`.

CPU fallback:

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build unity ros2 server
```

В CPU override:

- `gpus` сбрасывается;
- `UNITY_REQUIRE_NVIDIA=0`;
- `UNITY_SOFTWARE_RENDERING=1`;
- `NVIDIA_VISIBLE_DEVICES=void`.

## Текущий статус GPU rendering

На рабочей Windows + Docker Desktop + WSL2 + NVIDIA машине:

- `nvidia-smi` внутри `unity` видит NVIDIA GPU;
- Unity контейнер стартует без restart loop;
- OpenGL/Vulkan диагностика может показывать `Renderer: llvmpipe`, `Vendor: Mesa`;
- forced Vulkan сейчас не является стабильным default, потому что текущий Unity build может завершаться с ошибкой unsupported renderer.

Иными словами, GPU проброшен в контейнер, но реальный Unity renderer на NVIDIA пока не подтвержден. Это открытая задача, а не закрытый production-ready GPU stack.

## Диагностика Unity

Логи:

```powershell
docker compose logs unity --tail=200
```

Проверка NVIDIA runtime:

```powershell
docker compose exec unity nvidia-smi
```

Проверка Vulkan:

```powershell
docker compose exec unity vulkaninfo
```

Интерпретация:

- `nvidia-smi` работает - GPU доступен контейнеру;
- `Renderer: NVIDIA ...` - Unity реально рендерит на GPU;
- `Renderer: llvmpipe` - идет CPU rendering, это не готовый GPU-режим.

## Переменные Unity

| Переменная | Значение по умолчанию | Смысл |
| --- | --- | --- |
| `UNITY_REQUIRE_NVIDIA` | `1` | Падать при отсутствии NVIDIA runtime. |
| `UNITY_SOFTWARE_RENDERING` | `0` | Включить software rendering только в CPU fallback. |
| `UNITY_GRAPHICS_API` | `glcore` | `glcore`, `vulkan` или `auto`. |
| `UNITY_HEADLESS_NO_GRAPHICS` | `0` | Запуск Unity с `-batchmode -nographics`. |
| `UNITY_SCREEN` | `1280x720x24` | Xvfb screen. |
| `UNITY_SCREEN_WIDTH` | `1280` | Ширина Unity окна. |
| `UNITY_SCREEN_HEIGHT` | `720` | Высота Unity окна. |

## ROS 2 в Docker

Сервис `ros2` собирает `ros_tcp_endpoint` и `forest_msgs`.

Проверить интерфейс:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/msg/Event"
```

Проверить сервисы:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service list"
```

Если `/env/step` отсутствует, это текущее ограничение Unity/ROS-реализации.

## Данные и volume

PostgreSQL хранится в Docker volume `postgres_data`.

Файловые артефакты находятся в рабочем каталоге:

- `data/scenarios/generated/...`;
- `data/runs/run_<id>/...`.

`server` монтирует корень репозитория в `/app`, поэтому изменения Python-кода видны контейнеру без пересборки, но изменения зависимостей требуют rebuild.

## Известные инфраструктурные TODO

- добиться реального NVIDIA renderer внутри Unity контейнера;
- добавить короткий smoke-check, который различает "GPU виден контейнеру" и "Unity рендерит на GPU";
- ускорить сборку `server`, чтобы проверка `unity`/`ros2` не тянула тяжелые Python ML-зависимости.
