# Разработка

## Базовый принцип

В проекте есть несколько независимых слоев, но внешний runtime должен проходить через общие контуры:

```text
contracts -> scenario generation -> dispatcher -> runtime service -> observer -> DB/data -> UI
```

Новые режимы, поля состояния и артефакты лучше добавлять через эти точки, а не напрямую в UI или отдельный сервис.

## Быстрый маршрут новой правки

1. Найдите source of truth: route в `apps/api/dispatcher.py`, WebSocket protocol в `contracts/websocket_protocol.md`, HTTP endpoint в `apps/api/app.py`, ROS interface в `ros2_ws/src/forest_msgs`.
2. Проверьте, затрагивает ли правка контракт. Если да, сначала обновите contract/schema/docs, затем код и тесты.
3. Для backend/runtime правок начните с локального SQLite smoke или временной SQLite БД в тестах. Для изменений схемы БД обязательно проверьте PostgreSQL + Alembic migration.
4. Для frontend правок используйте `apps/web`, а не root-level `package.json`: корневые npm scripts сейчас placeholders.
5. Для 3D правок отдельно различайте synthetic test mode и реальный `sync_step` через `/env/step`.

## Как добавить новый runtime route

1. Добавить или переиспользовать `GenerationRequest` builder в `services/scenario_generator`.
2. Добавить runtime config builder, который превращает `GeneratedScenario` в параметры сервиса.
3. Реализовать service interface:
   - `load_scenario(scenario, runtime_config)`;
   - `start(params)`;
   - `stop()`;
   - `reset()`;
   - `get_state()`;
   - опционально `validate_scenario(...)`;
   - опционально `drain_runtime_events()`.
4. Зарегистрировать `RuntimeRoute` в `apps/api/dispatcher.py`.
5. Добавить WebSocket endpoint в `apps/api/app.py`.
6. Добавить route в `apps/web/src/constants/envs.js` и UI, если маршрут должен быть доступен пользователю.
7. Обновить `contracts/websocket_protocol.md`, `docs/api/README.md` и `docs/runtime/README.md`. `contracts/openapi.yaml` трогайте только если меняется публичная HTTP-часть или metadata, потому что runtime-контракт сейчас живет в WebSocket-документе.
8. Добавить тесты генерации, загрузки, start/stop и replay/metrics persistence.

## Как менять контракт

Перед изменением контракта нужно понять тип изменения:

| Изменение | Действие |
| --- | --- |
| Добавочное поле runtime state | Можно оставить `v1`, если обязательные поля не меняются. |
| Удаление/переименование обязательного поля | Нужна новая версия или совместимый bridge. |
| Новый route key | Обновить WebSocket contract, docs и frontend constants; OpenAPI менять только при изменении публичной HTTP-части или metadata. |
| Breaking change ROS `.msg/.srv` | Обновить `ros2_ws/src/forest_msgs`, `contracts/v2/ros_interfaces.md`, mapping tests. |
| Breaking change JSON artifact | Создать новую версию схемы только для этого артефакта. |

Сейчас версия `v2` введена только для ROS-интерфейсов. JSON-схемы `contracts/v1/*` остаются стабильными, пока в конкретном артефакте нет несовместимого изменения.

## Где сохраняются данные

| Данные | Место |
| --- | --- |
| Metadata, runs, episodes, metrics | PostgreSQL через `packages/db` |
| Сценарии и preview | `data/scenarios/generated/...` |
| Replay | `data/runs/run_<id>/replay_<timestamp>.jsonl` |
| Model checkpoints | файл в `data/runs/run_<id>/...`, запись в `models`, связанный `ArtifactType.model_checkpoint` |
| Scientific reports | `experiments/scientific` и configured output dir |

## Работа с БД

Актуальная модель - SQLAlchemy-модели в `packages/db/models`. Миграции лежат в `packages/db/migrations`.

Docker запускает миграции через сервис `migrate` перед стартом `server`.

Локальный Python-запуск без `DATABASE_URL` использует SQLite `data/platform_dev.sqlite3`. Это удобно для быстрой проверки dispatcher/UI flow, но миграции Alembic так не проверяются. Если нужно проверить PostgreSQL локально, задайте `DATABASE_URL` на host-адрес:

```powershell
$env:DATABASE_URL = "postgresql://forest:forest@localhost:5432/forest_rl"
alembic upgrade head
```

Если меняется модель:

1. Обновите SQLAlchemy model.
2. Добавьте Alembic migration.
3. Проверьте запуск `migrate`.
4. Обновите [database/README.md](database/README.md), если меняется смысл сущностей.

## Runtime state

`RunObserver` пишет replay, metrics, episodes и events на основе `service.get_state()`. Поэтому runtime-сервис должен:

- держать стабильные числовые поля для метрик, если они есть;
- выставлять `running`;
- корректно обновлять `episode`, `step`, `new_episode`;
- отдавать события через `drain_runtime_events()`, если события приходят из внешнего источника;
- не прятать ошибку: поле/атрибут `last_error` подхватывается dispatcher.

## Scientific mode

Scientific mode сейчас заморожен. Текущий MVP можно поддерживать, но не расширять до полного ТЗ без отдельного решения. Если правка ломает `experiments/scientific`, это считается регрессией, но новые возможности scientific mode сейчас не являются приоритетом.

## Frontend

Frontend находится в `apps/web` и работает поверх WebSocket/HTTP API backend. Root-level `package.json` не запускает реальный frontend build.

Основные точки:

- `apps/web/src/constants/envs.js` - route key и WebSocket endpoints;
- `apps/web/src/hooks/useRunActions.js` - WebSocket actions;
- `apps/web/src/pages/ExperimentPage.jsx` - основной экран эксперимента;
- `apps/web/src/pages/HomePage.jsx` - список runs;
- `apps/web/src/pages/ReplayPage.jsx` - replay view.

## Типовые ошибки

- Если локальные тесты падают на `ModuleNotFoundError: gymnasium`, установите зависимости из `packages/common/requirements.txt`.
- Если Unity пишет `Renderer: llvmpipe`, GPU виден не как реальный renderer. Это текущая открытая задача Docker/Unity stack.
- Если 3D route падает при `start`, проверьте наличие `/env/step`. Сейчас сервис ожидает этот endpoint по умолчанию.
- Если `docker compose up --build` пересобирает слишком много Python ML-зависимостей, это известный инфраструктурный TODO.
