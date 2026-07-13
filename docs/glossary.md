# Глоссарий

| Термин | Значение |
| --- | --- |
| `route_key` | Строковый ключ runtime-маршрута, например `discrete/patrol`. |
| `run` | Конкретный запуск алгоритма на сценарии. |
| `scenario` | Логическая серия сценариев в БД. |
| `scenario_version` | Конкретная сохраненная версия сценария с seed, параметрами и файлами. |
| `GeneratedScenario` | Python-модель результата генерации среды. |
| `preview.json` | Легковесный файл для UI preview. |
| `scenario.json` | Канонический сохраненный сценарий. |
| `runtime_config` | Конфиг, который передается runtime-сервису при `load_scenario`. |
| `ExperimentDispatcher` | Backend-компонент, управляющий генерацией, запуском и хранением run. |
| `RuntimeService` | Исполнитель среды с методами `load_scenario/start/stop/reset/get_state`. |
| `RunObserver` | Компонент, который опрашивает runtime state и пишет replay, metrics, episodes, events. |
| `replay` | JSONL-файл со снимками runtime state. |
| `episode` | Один эпизод выполнения среды. |
| `EpisodeEvent` | Событие внутри эпизода: collision, goal, intruder и т.д. |
| `forest_msgs` | ROS 2 пакет с сообщениями и сервисами платформы. |
| `/env/step` | Синхронный ROS service для одного RL-шага 3D среды. |
| `synthetic mode` | Тестовый режим `Simulator3DService`, который генерирует состояние без реальной Unity/ROS телеметрии. |
| `llvmpipe` | Software renderer Mesa. Если Unity использует его, GPU rendering фактически не работает. |
| `scientific mode` | Headless-контур пакетных экспериментов и отчетов; сейчас заморожен. |
