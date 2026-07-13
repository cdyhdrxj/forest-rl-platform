# Построение реплеев

Каталог зарезервирован под отдельные инструменты построения replay, но сейчас не содержит исполняемого кода.

## Где replay создается сейчас

Основной replay-flow находится в `apps/api/runtime_monitor.py`: `RunObserver` опрашивает `RuntimeService.get_state()` и пишет JSONL-файл в `data/runs/run_<id>/...`.

Формат одной строки replay описан в:

- `contracts/v1/replay.schema.json`;
- `contracts/websocket_protocol.md`.

Просмотр replay реализован через:

- HTTP endpoint `GET /api/runs/{run_id}/replay` в `apps/api/app.py`;
- frontend-страницу `apps/web/src/pages/ReplayPage.jsx`.

## Ожидаемая роль каталога

Сюда можно вынести offline-конвертеры, сжатие, сборку видео/визуализаций или восстановление replay из внешних логов. Такой код должен оставаться совместимым с текущим JSONL-контрактом.
