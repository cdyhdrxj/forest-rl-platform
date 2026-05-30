# Оценка и метрики

Каталог зарезервирован под общий слой оценки, но сейчас не содержит исполняемого кода.

## Где метрики находятся сейчас

- Runtime/replay/episode persistence: `apps/api/runtime_monitor.py`.
- Baseline metrics для классических планировщиков: `packages/baselines/metrics.py`.
- Coverage-specific metrics: `services/agrocare_coverage/metrics.py`.
- Scientific suite statistics: `experiments/scientific/stats.py`.

## Ожидаемая роль каталога

Если появится общий API оценки качества, сюда можно вынести route-independent метрики и агрегаторы. При переносе важно не потерять совместимость с `contracts/v1/metrics.schema.json` и существующим `RunObserver`.
