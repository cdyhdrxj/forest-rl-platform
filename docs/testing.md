# Тестирование и проверки

## Установка зависимостей для локальных тестов

```powershell
python -m pip install -r packages/common/requirements.txt
```

Если локальное окружение не содержит `gymnasium`, часть runtime/import тестов будет падать. Docker image `server` устанавливает зависимости из `packages/common/requirements.txt`.

## База данных в локальных проверках

Если `DATABASE_URL` не задан, код использует SQLite `data/platform_dev.sqlite3`. Многие unit/integration тесты дополнительно переопределяют `DATABASE_URL` на временный SQLite-файл, поэтому для первого `pytest` PostgreSQL не обязателен.

PostgreSQL обязателен, когда вы проверяете:

- Alembic migrations;
- поведение, зависящее от PostgreSQL dialect;
- compose-flow `postgres -> migrate -> server`.

Для локальной проверки миграций с PostgreSQL, поднятым через compose:

```powershell
$env:DATABASE_URL = "postgresql://forest:forest@localhost:5432/forest_rl"
alembic upgrade head
```

## Быстрые unit-проверки

```powershell
python -m pytest tests/unit/test_event_mapping.py tests/unit/test_contract_schemas.py
```

Эти тесты проверяют mapping ROS events и базовую валидность контрактов на доступных sample-артефактах.

## Проверка Python-синтаксиса ключевых runtime-файлов

```powershell
python -m py_compile services/simulator_3d/service.py services/trail_robot/wrapper.py apps/api/test2.py
```

## Полный pytest

```powershell
python -m pytest
```

Перед полным запуском убедитесь, что установлены Python-зависимости и доступна БД, если тесты используют dispatcher/storage.

## Docker smoke checks

Проверка конфигурации:

```powershell
docker compose config
```

Проверка CPU override:

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml config
```

Проверка сервисов:

```powershell
docker compose ps
```

Backend health:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

## Frontend checks

Команды frontend выполняются из `apps/web`:

```powershell
cd apps/web
npm install
npm run build
```

Root-level npm scripts не являются проверкой реального frontend build.

## ROS checks

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/srv/Step"
```

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service list"
```

## Unity checks

```powershell
docker compose exec unity nvidia-smi
```

```powershell
docker compose logs unity --tail=200
```

Смотреть в логах:

- `Renderer: NVIDIA ...` - желаемый GPU rendering;
- `Renderer: llvmpipe` - CPU rendering;
- ошибки `DllNotFoundException`, `libnvidia-encode`, `Failed to open plugin` - проблемы runtime libraries;
- ошибки `/env/step` - Unity/ROS не реализует sync service.

## Что должно быть покрыто тестами при новой правке

| Область правки | Минимальная проверка |
| --- | --- |
| WebSocket action | unit/integration тест `handle_ws` или dispatcher flow |
| Runtime route | generate/load/start/stop через dispatcher |
| Scenario format | schema validation и storage reload |
| ROS event mapping | `tests/unit/test_event_mapping.py` |
| DB model/migration | migration upgrade + smoke create/read |
| Frontend route | ручной запуск UI или e2e, если появится |
| 3D runtime | synthetic test и отдельный real `/env/step` integration test |

## Известные test gaps

- нет полного CI pipeline;
- нет строгой schema validation для WebSocket request/state;
- нет real Unity `/env/step` integration test;
- нет автоматической проверки, что Unity реально рендерит на NVIDIA GPU;
- scientific mode покрыт MVP-smoke, но полный набор из ТЗ заморожен.
