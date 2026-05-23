# Быстрый старт

Этот документ помогает поднять проект с нуля и выполнить первые проверки. Все команды запускаются из корня репозитория, если явно не указано другое.

## Требования

Для основного Docker-запуска:

- Docker Desktop с WSL2 backend;
- NVIDIA GPU и работающий NVIDIA runtime в Docker;
- `.env` в корне проекта с переменными PostgreSQL, pgAdmin и `DATABASE_URL`;
- свободные порты `5173`, `8000`, `5050`, `5432`, `9090`, `10000`, `10001`.

Для локальной разработки без Docker:

- Python 3.10;
- Node.js 20;
- PostgreSQL 15 или доступ к compose-сервису `postgres`;
- зависимости из `packages/common/requirements.txt`;
- зависимости frontend из `apps/web/package.json`.

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

Запуск API:

```powershell
python apps/api/main.py
```

По умолчанию сервер слушает `http://127.0.0.1:8000`.

## Локальный запуск frontend

```powershell
cd apps/web
npm install
npm run dev
```

Root-level `package.json` сейчас содержит placeholder scripts. Для frontend используйте команды из `apps/web`.

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
