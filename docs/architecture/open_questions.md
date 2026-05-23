# Открытые архитектурные вопросы

Дата ревизии: 2026-05-23.

Этот документ фиксирует вопросы, которые нельзя закрыть только локальной правкой кода. По каждому пункту указано текущее состояние, рабочее решение и что нужно сделать дальше.

## 1. GPU для Unity в Docker

### Текущее состояние

- На рабочей машине обнаружена NVIDIA GeForce RTX 4050 Laptop GPU, драйвер 566.14, CUDA 12.7.
- В Docker Desktop доступен runtime `nvidia`.
- До правки контейнер `unity` падал не из-за GPU, а из-за CRLF в `/entrypoint.unity.sh`: лог показывал `exec /entrypoint.unity.sh: no such file or directory`.
- В `docker-compose.yml` теперь для `unity` задано `gpus: all`, `NVIDIA_VISIBLE_DEVICES=all`, `NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute,video,display`.
- Принудительный `LIBGL_ALWAYS_SOFTWARE=1` убран. CPU fallback теперь включается через `UNITY_SOFTWARE_RENDERING=1`.
- После пересборки `ros2` и `unity` стартуют без restart loop. Дополнительно исправлены runtime-зависимости Unity build: `libminizip1`, `libgomp1`, alias для `libnvidia-encode.so` и alias для `libdl`.
- Внутри контейнера `unity` команда `nvidia-smi` видит NVIDIA GPU, но лог Unity все еще показывает `Renderer: llvmpipe`, `Vendor: Mesa`.

### Что еще нужно проверить

- Если Xvfb все равно оставляет OpenGL на CPU, заменить headless-графический стек: рассмотреть EGL/VirtualGL/NVIDIA OpenGL base image или другой режим запуска Unity Render Streaming.
- Добавить короткую диагностическую команду/скрипт, который в CI или локально различает "GPU доступен контейнеру" и "Unity реально рендерит на GPU".

### Решение, которое нужно подтвердить

Нужно ли делать GPU обязательным для основного `docker-compose.yml`, или оставить GPU как основной путь на этой машине, но добавить отдельный CPU override-файл для разработчиков без NVIDIA GPU.

## 2. Реальный RL-цикл в `Simulator3DService`

### Текущее состояние

`services/simulator_3d/service.py` сейчас выполняет две разные роли:

- инициализирует Unity/ROS через `/env/generate`, `/env/set_robots`, `/env/set_goal`, `/env/reset`;
- генерирует синтетический runtime state в `_loop`, `_advance_trail` и patrol-ветке.

Синтетический цикл полезен для dispatcher/integration smoke-тестов, но это не настоящий 3D RL-контур: нет чтения pose/scan/events из ROS, нет канонического step/reset handshake, нет реальных наград, эпизодов и траекторий из Unity.

### Граница ответственности

Это совместная зона, а не задача одного разработчика:

- Unity/симулятор: публикует реальные pose, scan, events и поддерживает сервисы reset/step/init.
- ROS-интеграция: оформляет `.msg/.srv`, rosbridge/ROS TCP endpoint и совместимость типов.
- Backend/API: заменяет синтетический `_loop` на адаптер реальной телеметрии, пишет replay/metrics/events через `RunObserver`.
- RL-разработчики режимов: фиксируют reward, done, episode semantics и action space для trail/patrol.

### Что нужно сделать

- Зафиксировать минимальный 3D runtime contract: observation, action, reward, done, info, reset, step.
- Решить, будет ли 3D работать в push-модели через топики или в синхронной модели `/env/step`.
- Подписать `Simulator3DService` на реальные ROS-топики и `/env/events`.
- Оставить synthetic loop только как fallback/test mode с явным флагом, например `SIMULATOR_3D_SYNTHETIC=1`.
- Добавить интеграционный тест, который проверяет хотя бы один реальный ROS event -> platform event -> replay/episode event.

## 3. Контракты `v1` и `v2`

### Текущее состояние

- `contracts/v1/*` содержит стабильные платформенные схемы: сценарии, preview, replay, metrics, episode log, scientific suite/report.
- `contracts/v2/ros_interfaces.md` сейчас является отдельной основной ROS-спецификацией.
- `contracts/v1/ros_interfaces.md` остается историческим документом.
- Реальный ROS-пакет `ros2_ws/src/forest_msgs` пока не полностью совпадает с `contracts/v2/ros_interfaces.md`: текущий `Event.msg` содержит `type`, `robot_id`, `x`, `y`, `value`, а v2 описывает отдельные event constants, `geometry_msgs/Point position` и `intruder_id`; `StepCmd.msg` в пакете отсутствует.

### Рабочее решение

Не переносить весь каталог `v2` в `v1` и не переименовывать все схемы в `v2`. Версионирование должно быть поконтрактным:

- `v1` остается стабильной версией платформенных JSON-артефактов;
- ROS-интерфейсы живут в `v2`, потому что там уже есть breaking change по event codes;
- новые `v2` JSON-схемы стоит заводить только при реальном breaking change в соответствующем артефакте.

### Что нужно решить

- Можно ли прямо сейчас поменять `forest_msgs/Event.msg` под v2, или Unity уже жестко зависит от старого формата.
- Нужен ли compatibility bridge `legacy Event.msg -> v2 event mapping`.
- Где будет лежать канонический ROS package: текущий `forest_msgs` или новый пакет интерфейсов.

## 4. Scientific Mode

### Текущее состояние

Scientific mode уже не только ТЗ. В проекте есть:

- CLI `python -m experiments.scientific.run_suite --config ...`;
- Pydantic-модели suite config;
- JSON Schema `contracts/v1/scientific_suite.schema.json`;
- JSON Schema `contracts/v1/scientific_report.schema.json`;
- `ExperimentSuiteOrchestrator`;
- `report_builder`, `summary.csv`, `report.json`, `report.html`, `suite_manifest.json`;
- smoke/integration тесты.

Актуальная структура конфига и отчета описана в `docs/experiments/scientific_mode.md`.

### Что еще не закрыто

- Нет полноценного provenance-блока в `report.json`: git commit, версии зависимостей, версия Python, исходный config hash.
- Статистические сравнения Wilcoxon/Mann-Whitney из ТЗ пока не реализованы.
- Графики сейчас простые SVG, а не полный набор распределений/PNG из ТЗ.
- Нужно решить, считается ли текущий `coverage` MVP достаточным для статьи, или требуется более строгая модель агротехнических рядов.
