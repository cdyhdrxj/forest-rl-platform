# ТЗ: внедрение scientific mode для серии воспроизводимых экспериментов

## Статус

Рабочее техническое задание на внедрение отдельного научного режима в проект `forest-rl-platform`.

## Цель

Реализовать в проекте отдельный scientific mode, позволяющий:

- запускать эксперименты без live-визуализации и без постоянного WebSocket-сеанса;
- выполнять серии воспроизводимых запусков по заранее заданному конфигу;
- сравнивать базовые алгоритмы и методы обучения с подкреплением на одном наборе сценариев;
- сохранять агрегированную статистику, промежуточные артефакты и итоговый отчет в файл;
- строить offline-визуализацию конечного результата, включая путь робота, покрытие и распределения метрик.

## Основание

Scientific mode должен поддержать вычислительный протокол для задачи покрытия междурядий при агротехнических уходах, описанный в статье про планирование движения автономного мобильного робота в лесных культурах.

Обязательные элементы протокола:

- сценарные семейства `S1`, `S2`, `S3`, `S4`;
- раздельные наборы `train`, `val`, `test`;
- несколько независимых запусков RL с разной инициализацией;
- сравнение минимум трех методов: `Greedy-1`, `Greedy-2`, `RL`;
- расчет сводных метрик, статистик и построение характерных траекторий.

## Принципы внедрения

- Текущий live-режим через `apps/web` и WebSocket-маршруты не заменяется и не ломается.
- Scientific mode реализуется как соседний контур поверх существующих `scenario`, `run`, `episode`, `metric`, `replay`.
- MVP scientific mode запускается из CLI и не требует обязательного web-интерфейса.
- Все сценарии, split'ы, seed'ы, конфиги и отчеты должны быть воспроизводимыми.

## Область работ

### Входит в MVP

- новый тип задачи `coverage` для агротехнических уходов;
- новый headless runtime для экспериментов покрытия;
- генератор сценариев `S1-S4`;
- конфигурируемые split'ы `train/val/test`;
- запуск baseline-методов и RL-метода на общем наборе сценариев;
- отдельный orchestrator для experiment suite;
- сбор метрик и статистическая агрегация;
- генерация `report.html`, `report.json`, `summary.csv`, `plots/*.png`, `trajectories/*.png`;
- offline-рендер траектории и покрытия для отдельных `run`.

### Не входит в MVP

- замена текущего WebSocket-протокола на HTTP API;
- онлайн-панель scientific mode в `apps/web`;
- поддержка MARL;
- перенос scientific mode в ROS 2 / Unity 3D;
- автоматическое распределение запусков по нескольким машинам.

## Целевой сценарий использования

Пользователь запускает одну команду:

```powershell
python -m experiments.scientific.run_suite --config experiments/configs/scientific/agrocare_paper_v1.yaml
```

По завершении запуска система:

- создает запись suite в БД;
- создает связанные `run` для всех элементов серии;
- сохраняет сырьевые артефакты каждого `run`;
- строит итоговый агрегированный отчет;
- сохраняет offline-графики и характерные траектории;
- пишет manifest suite с ссылками на все связанные `run_id` и файлы.

## Целевая модель данных

### 1. Новый тип задачи

Необходимо добавить новый `task_kind`:

- `coverage`

И новый `project_mode`:

- `coverage`

Целевой route key для первого этапа:

- `continuous/coverage`

Первый этап scientific mode должен работать на `continuous_2d` представлении среды.

### 2. Новые таблицы БД

Необходимо добавить таблицу `experiment_suites`.

Минимальные поля:

- `id`
- `code`
- `title`
- `route_key`
- `mode`
- `status`
- `config_json`
- `summary_json`
- `manifest_uri`
- `created_by_user_id`
- `created_at`
- `started_at`
- `finished_at`

Необходимо добавить таблицу `experiment_suite_runs`.

Минимальные поля:

- `id`
- `suite_id`
- `run_id`
- `scenario_family`
- `dataset_split`
- `method_code`
- `replicate_index`
- `role`
- `train_seed`
- `eval_seed`
- `group_key`
- `created_at`

`role` принимает значения:

- `train`
- `eval`
- `baseline`

Suite-level plots и отчеты не нужно хранить отдельной таблицей артефактов в MVP.
Для них достаточно `manifest_uri` в `experiment_suites`, указывающего на `suite_manifest.json`.

## Файловая структура

### Новые директории и модули

Необходимо создать:

```text
services/agrocare_coverage/
  __init__.py
  models.py
  generator.py
  environment.py
  baselines.py
  metrics.py
  renderer.py
  service.py
  callback.py

experiments/scientific/
  __init__.py
  run_suite.py
  suite_loader.py
  orchestrator.py
  report_builder.py
  stats.py
  render_run.py

experiments/configs/scientific/
  agrocare_paper_v1.yaml
  agrocare_smoke.yaml
```

### Новые документы и контракты

Необходимо создать:

- `contracts/v1/scientific_suite.schema.json`
- `contracts/v1/scientific_report.schema.json`

Новые схемы должны использоваться вместе с уже существующими:

- `contracts/v1/scenario.schema.json`
- `contracts/v1/replay.schema.json`
- `contracts/v1/metrics.schema.json`
- `contracts/v1/episode_log.schema.json`

## Конфиг scientific suite

В проекте должен появиться конфиг suite в YAML, валидируемый Pydantic-моделью и JSON Schema.

Минимальные поля suite-конфига:

- `suite_code`
- `title`
- `route_key`
- `task_kind`
- `environment_kind`
- `report_dir`
- `seed`
- `scenarios`
- `methods`
- `report`

### Поля блока `scenarios`

Для каждого семейства `S1-S4` должны задаваться:

- `family`
- `train_count`
- `val_count`
- `test_count`
- `generator_params`

`generator_params` минимум включает:

- диапазон числа рядов;
- диапазон длин рядов;
- параметры кривизны;
- параметры внутренних препятствий;
- вероятность разрывов;
- габариты робота;
- радиус рабочей зоны;
- seed генерации.

### Поля блока `methods`

Для каждого метода должны задаваться:

- `code`
- `kind`
- `enabled`
- `training`
- `evaluation`

Обязательные коды для первого этапа:

- `greedy_nearest`
- `greedy_two_step`
- `sac`

### Пример конфига

```yaml
suite_code: agrocare-paper-v1
title: Agrocare coverage benchmark S1-S4
route_key: continuous/coverage
task_kind: coverage
environment_kind: continuous_2d
report_dir: data/scientific/suites
seed: 20260401

scenarios:
  - family: S1
    train_count: 300
    val_count: 100
    test_count: 150
    generator_params:
      row_count_range: [8, 12]
      curvature_level: low
      gap_probability: 0.0
      obstacle_count_range: [0, 0]
  - family: S2
    train_count: 300
    val_count: 100
    test_count: 150
    generator_params:
      row_count_range: [8, 12]
      curvature_level: low
      gap_probability: 0.0
      obstacle_count_range: [1, 2]
  - family: S3
    train_count: 300
    val_count: 100
    test_count: 150
    generator_params:
      row_count_range: [8, 12]
      curvature_level: medium
      gap_probability: 0.0
      obstacle_count_range: [2, 4]
  - family: S4
    train_count: 300
    val_count: 100
    test_count: 150
    generator_params:
      row_count_range: [8, 12]
      curvature_level: high
      gap_probability: 0.2
      obstacle_count_range: [2, 4]

methods:
  - code: greedy_nearest
    kind: baseline
    enabled: true
  - code: greedy_two_step
    kind: baseline
    enabled: true
  - code: sac
    kind: rl
    enabled: true
    training:
      repeats: 5
      total_timesteps: 500000
      eval_every_steps: 10000
      early_stop_patience: 5
    evaluation:
      deterministic: true

report:
  formats: [html, json, csv]
  representative_runs_per_method: 3
  save_trajectory_plots: true
  save_distribution_plots: true
```

## Требования к генерации сценариев

### Общие требования

- Генерация должна быть детерминированной при фиксированном seed.
- Один и тот же suite-конфиг должен порождать одинаковые `train/val/test` split'ы.
- Для каждого экземпляра должен формироваться стабильный `scenario_id` внутри suite.

### Семейства сценариев

Должны быть реализованы четыре семейства:

- `S1`: простой полигон, нет внутренних препятствий, почти прямые ряды, нет разрывов;
- `S2`: 1-2 внутренние непроходимые зоны, малая кривизна рядов;
- `S3`: сложная форма участка, несколько препятствий, криволинейные, но непрерывные ряды;
- `S4`: сложная форма участка, несколько препятствий, криволинейные ряды с разрывами.

### Хранимые артефакты сценария

Для каждого сценария должны сохраняться:

- `scenario.json`
- `preview.json`
- слои среды
- сериализованный runtime config
- метаданные family/split/index/seed

## Требования к runtime и алгоритмам

### Общий интерфейс метода

Все методы должны приводиться к общему интерфейсу верхнего уровня:

- вход: сценарий покрытия и текущее состояние обхода;
- выход: следующее междурядье, направление входа, решение о переходе.

Нижнеуровневый контроллер движения должен быть одинаковым для baseline и RL.

### Baseline-методы

Необходимо реализовать:

- `greedy_nearest`
- `greedy_two_step`

Оба baseline должны работать в headless-режиме и не требовать отдельного обучения.

### RL-метод

Для MVP используется:

- `sac`

Требования:

- обучение на `train`;
- выбор checkpoint по `val`;
- итоговая оценка только на `test`;
- несколько независимых запусков обучения с разными seed;
- детерминированный evaluation из сохраненного checkpoint.

## Требования к orchestration

Необходимо реализовать `ExperimentSuiteOrchestrator`, который:

- создает запись suite в БД;
- разворачивает suite в набор run-задач;
- запускает baseline и RL сценарии в корректном порядке;
- ожидает завершения run без WebSocket;
- сохраняет связь `suite -> run`;
- инициирует постобработку и сбор отчета;
- корректно переводит suite в статусы `created/running/finished/failed/cancelled`.

### Порядок выполнения suite

`baseline`:

- сразу запускается на `test` split.

`rl`:

- обучение на `train`;
- периодическая оценка на `val`;
- выбор лучшего checkpoint;
- итоговая оценка на `test`.

## Требования к ExperimentDispatcher

Нужно расширить `ExperimentDispatcher` методами для headless-контура:

- `wait_run(run_id, poll_interval, timeout_sec)`
- `get_run_result(run_id)`
- `export_run_bundle(run_id)`

Scientific mode должен использовать dispatcher программно, без WebSocket.

## Метрики

### Обязательные метрики run-level

Для каждого run необходимо сохранять и/или вычислять:

- `success`
- `coverage_ratio`
- `missed_area_ratio`
- `return_to_start_success`
- `return_error`
- `path_length`
- `task_time_sec`
- `transition_count`
- `repeat_coverage_ratio`
- `angular_work_rad`
- `compute_time_sec`
- `collisions_count`

### Главная метрика

Главной метрикой сравнения является:

- `success_rate`

### Правило фильтрации

Метрики:

- `path_length`
- `task_time_sec`
- `transition_count`
- `repeat_coverage_ratio`
- `angular_work_rad`

сравниваются только на подмножестве успешно завершенных решений.

### Метрики RL-обучения

Для RL дополнительно нужно сохранять:

- `train_reward_mean`
- `val_success_rate`
- `best_checkpoint_step`
- `train_wall_time_sec`

## Статистическая обработка

Для каждой пары `scenario_family x method_code` должны рассчитываться:

- среднее;
- стандартное отклонение;
- медиана;
- межквартильный размах;
- число наблюдений.

Для попарных сравнений методов должны поддерживаться:

- `Wilcoxon` для парных сравнений на общем тестовом наборе;
- `Mann-Whitney` для независимых выборок;
- поправка на множественные сравнения.

MVP допускает расчет статистики только на этапе post-processing.

## Отчетность

### Обязательные файлы suite

После завершения suite должны существовать:

- `suite_manifest.json`
- `report.json`
- `summary.csv`
- `report.html`

### Обязательные графики

Нужно строить:

- распределение длины маршрута по методам;
- распределение повторного покрытия по методам;
- графики success rate по сценариям;
- характерные траектории по сценариям `S1-S4`.

### Минимальная структура report.json

`report.json` должен содержать:

- метаданные suite;
- список run;
- агрегированную таблицу по сценариям и методам;
- блок статистических сравнений;
- список файлов визуализации;
- provenance-блок.

### Формат итогового каталога

```text
data/scientific/suites/<suite_code>/
  suite_manifest.json
  report.json
  summary.csv
  report.html
  plots/
    success_rate.png
    path_length_distribution.png
    repeat_coverage_distribution.png
  trajectories/
    S1_greedy_nearest_run_101.png
    S1_greedy_two_step_run_102.png
    S1_sac_run_103.png
    ...
```

## Offline-визуализация конечного результата

Scientific mode обязан поддерживать отдельный рендеринг конечного результата по сохраненному `run`.

Нужно реализовать команду:

```powershell
python -m experiments.scientific.render_run --run-id 123 --output data/scientific/rendered/run_123
```

Команда должна строить:

- путь робота;
- карту покрытия;
- карту повторного покрытия;
- подпись с основными метриками.

## Требования к provenance и воспроизводимости

Для каждого suite необходимо сохранять:

- git commit;
- версию Python;
- версии ключевых зависимостей;
- suite seed;
- seed генерации сценариев;
- train/eval seed каждого run;
- исходный suite-конфиг;
- timestamp запуска.

Требования к воспроизводимости:

- генерация сценариев и baseline-методы должны быть строго детерминированными при фиксированном seed;
- evaluation RL из сохраненного checkpoint должен быть детерминированным;
- бит-в-бит воспроизводимость обучения на разном железе в MVP не требуется, но должна быть зафиксирована как ограничение.

## Требования к тестам

Необходимо добавить:

- unit-тесты на модели suite-конфига;
- unit-тесты на генерацию split'ов;
- unit-тесты на baseline-методы;
- unit-тесты на расчет научных метрик;
- integration smoke-test одного suite с маленьким конфигом;
- integration test на генерацию итогового `report.json`;
- test на повторяемость генерации сценариев при одинаковом seed.

Целевые файлы:

- `tests/unit/test_scientific_suite_config.py`
- `tests/unit/test_agrocare_metrics.py`
- `tests/unit/test_agrocare_baselines.py`
- `tests/integration/test_scientific_suite_smoke.py`
- `tests/integration/test_scientific_report_export.py`

## Требования к документации

Необходимо обновить:

- `docs/experiments/README.md`
- `docs/architecture/README.md`
- `docs/contracts_status.md`

После реализации scientific mode должен быть добавлен отдельный пользовательский документ с командами запуска и описанием структуры выходных файлов.

## План внедрения

### Этап 1. Домен и сценарии

- добавить `coverage` в enum'ы и route map;
- создать `services/agrocare_coverage/models.py`;
- реализовать генератор `S1-S4`;
- реализовать сериализацию сценариев и split'ов.

### Этап 2. Методы и runtime

- реализовать baseline `greedy_nearest`;
- реализовать baseline `greedy_two_step`;
- реализовать `CoverageService`;
- реализовать RL-обучение и evaluation через `sac`.

### Этап 3. Suite orchestration

- добавить таблицы suite;
- реализовать `ExperimentSuiteOrchestrator`;
- добавить CLI `run_suite.py`;
- расширить `ExperimentDispatcher` headless-методами.

### Этап 4. Отчетность

- реализовать сбор агрегированных метрик;
- реализовать статистический модуль;
- реализовать `report_builder.py`;
- реализовать offline-рендер траекторий.

### Этап 5. Тесты и документация

- покрыть MVP smoke/integration тестами;
- обновить документацию;
- подготовить пример paper-конфига.

## Критерии приемки

Задача считается принятой, если одновременно выполнены все условия:

- в проекте существует отдельный CLI scientific mode без обязательного web-интерфейса;
- suite-конфиг валидируется и порождает воспроизводимый набор `train/val/test`;
- реализованы четыре семейства сценариев `S1-S4`;
- реализованы три метода: `greedy_nearest`, `greedy_two_step`, `sac`;
- baseline и RL сравниваются на одном test-наборе;
- по завершении suite формируются `report.html`, `report.json`, `summary.csv`;
- строятся trajectory plots минимум для одного representative run на метод и сценарий;
- в БД сохраняются suite, связи suite-run и базовая summary-информация;
- smoke-test suite проходит в CI на уменьшенном конфиге;
- текущий live-режим WebSocket остается работоспособным.

## Риски

- Текущая модель `run` ориентирована на одиночный запуск, а не на suite.
- Текущие `RunObserver` и `MetricSeries` не покрывают все научные метрики и потребуют расширения.
- Для больших suite replay может занять слишком много места, если не ввести режимы детализации.
- Строгая воспроизводимость RL-обучения ограничена особенностями backend и платформы.

## Решения, зафиксированные этим ТЗ

- Scientific mode внедряется как отдельный CLI-конур, а не как расширение WebSocket UI.
- Для задачи статьи вводится новый `task_kind = coverage`, а не переиспользуются `trail` или `reforestation`.
- MVP опирается на `continuous_2d`, без обязательной 3D-интеграции.
- Suite-level отчет хранится через `suite_manifest.json`, а не через расширение существующей модели `Artifact`.
- Offline-визуализация конечного результата обязательна уже в MVP.
