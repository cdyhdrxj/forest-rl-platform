# Scientific Mode

Дата ревизии: 2026-05-23.

Scientific mode предназначен для пакетных headless-экспериментов без live WebSocket-сессии. Он запускает набор сценариев и методов, сохраняет связанные `run`, экспортирует артефакты каждого запуска и собирает suite-level отчет.

## Запуск

Основная команда:

```powershell
python -m experiments.scientific.run_suite --config experiments/configs/scientific/agrocare_smoke.json
```

Для полного agrocare-набора используются конфиги в `experiments/configs/scientific/`, например:

- `agrocare_smoke.json`
- `agrocare_paper_v1.json`
- `agrocare_paper_v1.yaml`
- `trail_smoke.json`

YAML поддерживается через PyYAML. Если PyYAML не установлен, используйте JSON-конфиг.

## Структура suite-конфига

Контракт: `contracts/v1/scientific_suite.schema.json`.

Pydantic-модель: `experiments/scientific/models.py`.

Корневые поля:

- `suite_code` — стабильный код серии, используется как имя выходного каталога.
- `title` — человекочитаемое название.
- `route_key` — маршрут dispatcher, например `continuous/coverage`.
- `task_kind` — тип задачи, например `coverage`.
- `environment_kind` — тип среды, например `continuous_2d`.
- `report_dir` — корень для выходных файлов, по умолчанию `data/scientific/suites`.
- `seed` — базовый seed suite.
- `scenarios` — список определений сценариев.
- `methods` — список методов запуска.
- `report` — настройки файлов отчета.

### `scenarios`

Один элемент `scenarios` может описывать либо один split, либо bundle `train/val/test`.

Поля:

- `family` — семейство сценария, для coverage обычно `S1`, `S2`, `S3`, `S4`.
- `split` — `train`, `val` или `test`; если не задан, используется `test`.
- `count` — количество сценариев для одного split.
- `train_count`, `val_count`, `test_count` — альтернативный способ задать split bundle.
- `seed_start` — первый seed для materialized-сценариев; если не задан, вычисляется из suite seed.
- `generation_params` — параметры генерации сценария.
- `evaluation_params` — параметры исполнения для этих сценариев.

Важно: актуальное имя поля в коде и схеме — `generation_params`. Старое имя `generator_params` из ТЗ не используется текущей моделью.

### `methods`

Поля:

- `code` — код метода в отчете.
- `algorithm` — код алгоритма для runtime; если не задан, используется `code`.
- `kind` — `baseline` или `rl`.
- `enabled` — включает или отключает метод.
- `repeats` — число повторов; для RL также может браться из `training.repeats`.
- `role` — роль независимого запуска, например `baseline`.
- `start_params` — параметры, напрямую передаваемые в `start_run`.
- `training` — параметры обучения RL: `repeats`, `total_timesteps`, `eval_every_steps`, `early_stop_patience` и другие runtime-поля.
- `evaluation` — параметры evaluation: `deterministic`, `eval_episodes`, `selection_metric`, `selection_mode`.

Baseline-методы для `continuous/coverage`:

- `greedy_nearest`
- `greedy_two_step`

RL-методы идут через `stable-baselines3` и `services/agrocare_coverage/service.py`; выбор класса берется из `apps/api/sb3/sb3_trainer.py`.

### `report`

Поля:

- `formats` — список из `json`, `csv`, `html`.
- `representative_runs_per_method` — сколько representative trajectory renders сохранять на метод.
- `save_trajectory_plots` — сохранять trajectory SVG.
- `save_distribution_plots` — сохранять summary-графики.

## RL-протокол

Для `kind: rl` orchestrator группирует сценарии по `family`.

Если есть `train` split:

1. последовательно запускает train runs;
2. сохраняет checkpoint после train run;
3. периодически оценивает checkpoint на `val`;
4. выбирает лучший checkpoint по `evaluation.selection_metric`;
5. оценивает выбранный checkpoint на `test`.

Если `train` split отсутствует, метод запускается как независимый evaluation/baseline-style метод по заданным сценариям.

## Выходной каталог

Для suite с `suite_code: agrocare-smoke-suite` и стандартным `report_dir` результат пишется в:

```text
data/scientific/suites/agrocare-smoke-suite/
  suite_manifest.json
  report.json
  summary.csv
  report.html
  plots/
  trajectories/
  checkpoints/
```

Наличие `report.json`, `summary.csv` и `report.html` зависит от `report.formats`. `suite_manifest.json` пишется всегда.

## Структура `report.json`

Контракт: `contracts/v1/scientific_report.schema.json`.

Основные поля:

- `generated_at` — время генерации отчета.
- `suite` — id, code, title, route, mode, status, timestamps.
- `config` — исходный suite config после Pydantic-нормализации.
- `overview` — число запусков, методы, семейства сценариев, split'ы, статусы.
- `aggregates` — агрегаты по `method_code x role x dataset_split`.
- `runs` — строка на каждый связанный run.
- `artifacts` — относительные пути к plots и trajectories.

`runs[]` содержит:

- идентификаторы: `run_id`, `scenario_family`, `dataset_split`, `method_code`, `replicate_index`, `role`, `group_key`;
- seed'ы: `train_seed`, `eval_seed`;
- статус и алгоритм: `status`, `algorithm_code`, `success`;
- episode metrics: `episode_success_rate`, `episode_reward_mean`, `episode_reward_median`, `episode_steps_mean`;
- coverage metrics: `coverage_ratio_mean`, `missed_area_ratio`, `return_to_start_success`, `return_error`, `path_length`, `task_time_sec`, `transition_count`, `repeat_coverage_ratio`, `angular_work_rad`, `compute_time_sec`;
- checkpoint поля: `checkpoint_in_path`, `checkpoint_out_path`, `source_train_run_id`, `checkpoint_paths`;
- export paths: `run_result_path`, `metrics_export_path`, `episode_log_path`, `trajectory_path`;
- `config_json` из run.

## Что еще нужно доделать

- Добавить provenance-блок в `report.json`: git commit, Python/dependency versions, hash исходного config.
- Реализовать статистические сравнения из ТЗ: Wilcoxon, Mann-Whitney, поправка на множественные сравнения.
- Расширить plots до полного набора распределений из ТЗ.
- Согласовать, какие метрики считаются главными для статьи: сейчас в отчете есть coverage/reward/success агрегаты, но нет отдельного блока statistical conclusions.
