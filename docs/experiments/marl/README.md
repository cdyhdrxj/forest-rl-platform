# MARL-эксперименты

Этот каталог зарезервирован под документацию многоагентных экспериментов.

## Текущий статус

Полноценный MARL-контур сейчас не реализован:

- нет active runtime route для MARL в `apps/api/dispatcher.py`;
- нет конфигов `experiments/configs/marl/`;
- `contracts/websocket_protocol.md` явно оставляет multi-agent payloads за пределами `v1`;
- `services/marl_coordination` пока содержит только статусный README.

## Что нужно описать перед реализацией

- постановку multi-agent задачи;
- формат сценария и `runtime_config`;
- action/observation space для каждого агента;
- формат replay/events/metrics с идентификаторами агентов;
- протокол train/eval и benchmark-сравнения;
- изменения WebSocket/API-контракта.

До появления этих решений этот каталог не является пользовательским guide по запуску MARL.
