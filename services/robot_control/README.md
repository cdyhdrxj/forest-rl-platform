# Управление роботом

Каталог отражает разделённую архитектуру для сценария управления роботом.

## Роли модулей

- `packages/env_bridge` — общие контракты и модели данных между обучением, runtime и транспортным слоем.
- `services/robot_control/policy_runner.py` — исполнение политики вне цикла обучения.
- `services/robot_control/safety.py` — отдельный safety-layer, который фильтрует команды до отправки в транспорт.
- `services/robot_control/bridge.py` — мост к ROS или другой транспортной шине.
- `services/robot_control/runtime.py` — orchestration-слой для режима исполнения.

## Контуры выполнения

### Обучение и оценка

Обучение идёт через `EnvironmentAdapter` и gym-совместимый цикл `reset/step`.
В этом режиме политика не должна зависеть от ROS-транспорта напрямую.

### Исполнение

Исполнение идёт по цепочке:

`PolicyRunner -> SafetySupervisor -> RobotBridge -> simulator/robot`

`EnvironmentAdapter` в runtime-контуре отвечает за синхронизацию шага и получение нового наблюдения,
но не заменяет safety-layer и не смешивает transport-логику с политикой.
