# Быстрый старт

Этот документ помогает поднять проект с нуля и выполнить первые проверки. Все команды запускаются из корня репозитория, если явно не указано другое.

## Какой маршрут выбрать

- **Docker + NVIDIA GPU** - основной маршрут, если нужно поднять всю систему вместе с Unity.
- **Docker CPU-only** - dev/diagnostic fallback для машин без NVIDIA GPU. Подходит для проверки связки backend/frontend/ROS/Unity-контейнеров, но не считается готовым GPU-режимом.
- **Локальный backend + локальный frontend** - самый быстрый маршрут для правок API, dispatcher, сценариев и UI. Без `DATABASE_URL` backend использует SQLite-файл `data/platform_dev.sqlite3`, поэтому PostgreSQL не обязателен для первого smoke-запуска.

## Требования

Для основного Docker-запуска:

- Docker Desktop с WSL2 backend;
- NVIDIA GPU и работающий NVIDIA runtime в Docker;
- `.env` в корне проекта с переменными PostgreSQL, pgAdmin и `DATABASE_URL`;
- свободные порты `5173`, `8000`, `5050`, `5432`, `9090`, `10000`, `10001`.

Для локальной разработки без Docker:

- Python 3.10 для паритета с текущим Docker image `apps/api/Dockerfile`;
- Node.js 20;
- PostgreSQL 15 нужен только для проверки production-like хранения и Alembic migrations; для первого локального запуска можно оставить `DATABASE_URL` пустым и использовать SQLite fallback;
- зависимости из `packages/common/requirements.txt`;
- зависимости frontend из `apps/web/package.json`.

`pyproject.toml` сейчас содержит package metadata с `requires-python >=3.11`, но текущий Docker runtime использует Python 3.10 и устанавливает зависимости из `packages/common/requirements.txt`. Пока эти источники не выровнены, для разработки ориентируйтесь на Dockerfile и requirements-based setup.

## `.env` и база данных

Docker Compose читает `.env` из корня репозитория. Минимальный dev-набор:

```env
DATABASE_URL=postgresql://forest:forest@postgres:5432/forest_rl
POSTGRES_DB=forest_rl
POSTGRES_USER=forest
POSTGRES_PASSWORD=forest
PGADMIN_DEFAULT_EMAIL=forest@forest.com
PGADMIN_DEFAULT_PASSWORD=forest
```

Хост `postgres` работает внутри docker-compose сети. Если вы запускаете backend локально на хосте, а PostgreSQL поднят через compose, используйте URL с `localhost`:

```powershell
$env:DATABASE_URL = "postgresql://forest:forest@localhost:5432/forest_rl"
```

Если `DATABASE_URL` не задан, `packages/db/session.py` создает SQLite БД в `data/platform_dev.sqlite3`. Это удобно для локального backend-smoke, но не заменяет проверку миграций PostgreSQL перед изменениями схемы.

## Запуск через Docker

Первый запуск или запуск после изменения Dockerfile/requirements:

```powershell
docker compose up --build
```

Обычный повторный запуск:

```powershell
docker compose up -d
```

Проверка контейнеров:

```powershell
docker compose ps
```

Доступные адреса:

| Сервис | Адрес |
| --- | --- |
| Web client | http://localhost:5173 |
| API backend | http://localhost:8000 |
| API health | http://localhost:8000/api/health |
| pgAdmin | http://localhost:5050 |
| rosbridge | ws://localhost:9090 |
| ROS TCP endpoint | localhost:10000 |

## CPU-only fallback

Основной compose требует NVIDIA GPU. На машине без NVIDIA используйте явный override:

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up --build
```

CPU-режим нужен только для разработки и диагностики. Если NVIDIA GPU доступен, Unity должна запускаться через основной compose.

## Быстрая проверка backend

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "message": "Server is running"
}
```

## Первый запуск эксперимента в UI

1. Откройте http://localhost:5173.
2. Выберите режим, например `discrete/patrol` или `continuous/trail`.
3. Нажмите генерацию сценария.
4. Запустите run.
5. Для сохранения финального статуса используйте завершение run.
6. Для просмотра сохраненных запусков используйте список runs и replay-страницу.

3D-маршруты сейчас полезны для проверки генерации и интеграционной обвязки. Реальный 3D RL loop требует реализации `/env/step` в Unity/ROS.

## Локальный запуск backend

Установите зависимости в выбранное Python-окружение:

```powershell
python -m pip install -r packages/common/requirements.txt
```

Быстрый запуск API со SQLite fallback:

```powershell
python apps/api/main.py
```

По умолчанию сервер слушает `http://127.0.0.1:8000`.

Если нужна локальная проверка с PostgreSQL, сначала задайте `DATABASE_URL` с `localhost`, затем примените миграции:

```powershell
$env:DATABASE_URL = "postgresql://forest:forest@localhost:5432/forest_rl"
alembic upgrade head
python apps/api/main.py
```

## Локальный запуск frontend

```powershell
cd apps/web
npm install
npm run dev
```

Root-level `package.json` сейчас содержит placeholder scripts. Для frontend используйте команды из `apps/web`. Адрес backend настраивается переменными Vite:

```powershell
$env:VITE_API_ADDRESS = "127.0.0.1"
$env:VITE_API_PORT = "8000"
```

По умолчанию эти значения уже такие же; менять их нужно только если backend запущен на другом хосте или порту. Карта HTTP/WebSocket endpoint'ов находится в `apps/web/src/constants/envs.js`.

## Остановка и очистка

Остановить compose-сервисы:

```powershell
docker compose down
```

Остановить compose-сервисы и удалить PostgreSQL volume:

```powershell
docker compose down -v
```

Команда с `-v` удалит локальную БД PostgreSQL. Используйте ее только если готовы потерять dev-данные.

## Полезные команды диагностики

Проверить итоговый compose:

```powershell
docker compose config
```

Проверить CPU override:

```powershell
docker compose -f docker-compose.yml -f docker-compose.cpu.yml config
```

Посмотреть логи Unity:

```powershell
docker compose logs unity --tail=200
```

Проверить, видит ли контейнер NVIDIA GPU:

```powershell
docker compose exec unity nvidia-smi
```

Проверить ROS interfaces:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 interface show forest_msgs/srv/Step"
```

Список ROS-сервисов:

```powershell
docker compose exec ros2 bash -lc "source /ros2_ws/install/setup.bash && ros2 service list"
```

Если `/env/step` отсутствует, это ожидаемое текущее ограничение Unity/ROS-части.
