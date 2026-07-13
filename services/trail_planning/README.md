# Прокладка троп

Этот каталог содержит ранние/prototype-материалы для задачи прокладки маршрута.

## Текущий статус

- `cost_map_builder.py` - простой генератор cost map, который используется в `experiments/benchmark_suites/run_baselines.py`.
- `forest_env.py` - ROS/Gazebo-oriented Gymnasium-среда. Сейчас она не подключена к современному dispatcher flow и зависит от внешних модулей/топиков (`lidar_processor`, `imu_processor`, `pose_reader`, Gazebo service), которых нет в основном Docker-compose контуре.

## Где актуальный runtime

Для backend route `continuous/trail` актуальный runtime находится в `services/trail_camar` и регистрируется через `apps/api/dispatcher.py`.

Для классических baseline-алгоритмов смотрите `packages/baselines`.

## Как относиться к этому каталогу

Используйте его как исследовательскую заготовку и исторический материал. Если код отсюда становится частью платформенного runtime, его нужно провести через общий путь:

`scenario generation -> dispatcher -> runtime service -> RunObserver -> contracts/docs/tests`.
