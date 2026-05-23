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
- Основной `docker-compose.yml` требует NVIDIA GPU. CPU-режим вынесен в `docker-compose.cpu.yml` и считается dev-only fallback.
- Целевая среда: Windows + Docker Desktop + WSL2 + NVIDIA.
- После пересборки `ros2` и `unity` стартуют без restart loop. Дополнительно исправлены runtime-зависимости Unity build: `libminizip1`, `libgomp1`, alias для `libnvidia-encode.so` и alias для `libdl`.
- Внутри контейнера `unity` команда `nvidia-smi` видит NVIDIA GPU, но OpenGL лог Unity все еще показывает `Renderer: llvmpipe`, `Vendor: Mesa`.
- Диагностика `UNITY_GRAPHICS_API=vulkan` тоже пока видит только `llvmpipe` в `vulkaninfo`; текущий Unity build выходит с `Forced renderer 21 is not supported`.

### Что еще нужно проверить

- Если Xvfb/Vulkan внутри Docker Desktop WSL2 все равно оставляют графику на CPU, заменить headless-графический стек: рассмотреть NVIDIA OpenGL base image, VirtualGL или запуск Unity вне Docker с backend/ROS в Docker.
- Добавить короткую диагностическую команду/скрипт, который в CI или локально различает "GPU доступен контейнеру" и "Unity реально рендерит на GPU".

### Решение

Если NVIDIA GPU доступен, Unity должна использовать GPU. CPU-режим допускается только через явный override для разработчиков без NVIDIA GPU.

## 2. Реальный RL-цикл в `Simulator3DService`

### Текущее состояние

`services/simulator_3d/service.py` больше не должен использовать synthetic loop как обычный runtime. Принятое решение: канонический 3D RL-контур работает синхронно через `/env/step`.

Синтетический цикл оставлен только как явный test mode: `SIMULATOR_3D_SYNTHETIC=1` или параметр запуска `synthetic=true`.

### Граница ответственности

Это совместная зона, а не задача одного разработчика:

- Unity/симулятор: публикует реальные pose, scan, events и поддерживает сервисы reset/step/init.
- ROS-интеграция: оформляет `.msg/.srv`, rosbridge/ROS TCP endpoint и совместимость типов.
- Backend/API: заменяет синтетический `_loop` на адаптер реальной телеметрии, пишет replay/metrics/events через `RunObserver`.
- RL-разработчики режимов: фиксируют reward, done, episode semantics и action space для trail/patrol.

### Что нужно сделать

- Реализовать `/env/step forest_msgs/srv/Step` на стороне Unity/ROS.
- Наполнить `observation_json`, `reward`, `terminated`, `truncated`, `info_json` реальными данными симуляции.
- Добавить интеграционный тест, который проверяет хотя бы один реальный ROS event -> platform event -> replay/episode event.

## 3. Контракты `v1` и `v2`

### Текущее состояние

- `contracts/v1/*` содержит стабильные платформенные схемы: сценарии, preview, replay, metrics, episode log, scientific suite/report.
- Файлы `.msg/.srv` в `ros2_ws/src/forest_msgs` являются source of truth для ROS-интерфейсов.
- `contracts/v2/ros_interfaces.md` является документацией к реальным `.msg/.srv`.
- `contracts/v1/ros_interfaces.md` остается историческим документом.
- `forest_msgs/Event.msg` переведен на v2 как breaking change. Compatibility bridge для старого формата не вводится.
- Добавлены `EnvAction.msg`, `StepCmd.msg` и `Step.srv` для синхронного `/env/step`.

### Рабочее решение

Не переносить весь каталог `v2` в `v1` и не переименовывать все схемы в `v2`. Версионирование должно быть поконтрактным:

- `v1` остается стабильной версией платформенных JSON-артефактов;
- ROS-интерфейсы документируются как `v2`, потому что там уже есть breaking change по event codes;
- новые `v2` JSON-схемы стоит заводить только при реальном breaking change в соответствующем артефакте.

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

### Статус

Scientific mode пока заморожен. Текущую реализацию оставляем как есть, полный набор из ТЗ не внедряем до отдельного решения.

## 5. HTTP/OpenAPI контракт

### Текущее состояние

Runtime-контур описан в `contracts/websocket_protocol.md`. В коде также есть HTTP endpoints:

- `GET /api/health`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/replay`
- `PATCH /api/runs/{run_id}`
- `GET /api/runs/{run_id}/checkpoint`

`contracts/openapi.yaml` пока содержит только metadata и ссылку на WebSocket contract, а не полную спецификацию этих HTTP endpoints.

### Рабочее решение

Пока считать HTTP endpoints вспомогательным API для текущего UI, а каноническим публичным runtime-контрактом считать WebSocket-документ.

### Что нужно сделать

Если HTTP API станет публичным для внешних интеграций, нужно заполнить `contracts/openapi.yaml`: schemas, parameters, responses, pagination, error model и auth/security policy.
