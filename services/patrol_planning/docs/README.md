# Патрулирование

## Установка

1. Установите [uv](https://docs.astral.sh/uv/).
2. Перейдите в корень репозитория
3. Выполните:

```bash
uv sync
```

## GridWorld

### Обучение агента

1. Перейдите в корень репозитория
2. Выполните:

```bash
uv run services/patrol_planning/learning/train/train.py
```

После выполнения в директории `services/patrol_planning/learning/models/` появится файл `ppo_gridworld_agent_1.zip`.

### Тест с ботами

1. Перейдите в корень репозитория
2. Выполните:

```bash
uv run services/patrol_planning/learning/test/test_with_bots.py
```

### Интерактивный тест

1. Перейдите в корень репозитория
2. Выполните:

```bash
uv run services/patrol_planning/learning/test/test_with_input.py
```

Для управления нарушителем используйте клавиши:

- `W` - вверх
- `S` - вниз
- `A` - влево
- `D` - вправо
- `ESC` - выход

<figure style="text-align: center;">
  <img src="image.png" alt="Так выглядит представление среды в терминале">
  <figcaption>Так выглядит графическое представление среды в терминале</figcaption>
</figure>

## Pydantic Модели

### `GridWorldTrainState`

[`services/patrol_planning/service/models.py`](../service/models.py)

Состояние обучения GridWorld. Хранит параметры среды, агента и статистику эпизодов:

- `agent_pos`, `goal_pos` — позиции агента и цели
- `trajectory` — путь агента
- `step`, `episode` — счетчики шагов и эпизодов
- `total_reward`, `last_episode_reward` — накопленные награды
- `collision_count`, `goal_count` — статистика столкновений и достижения целей (не используются)
- `i_count` — число не пойманных нарушителей
- `landmark_pos` — позиции препятствий
- `terrain_map` — карта рельефа (не используется)
- `obs_raw` — данные наблюдения агента
- `is_collision` — флаг столкновения
- `new_episode` — флаг начала нового эпизода
- `running` — флаг выполнения обучения
- `mode` — режим работы

Метод `reset_counters()` сбрасывает все счетчики и статистику для нового эпизода.

### `GridWorldConfig`

[`services/patrol_planning/assets/envs/models.py`](../assets/envs/models.py)

Конфигурация среды GridWorld:

- `agent_config` — конфигурация агента
- `intruder_config` — список конфигураций нарушителей
- `obs_config` — конфигурация наблюдения
- `max_steps` — длина эпизода (по умолчанию 50)
- `grid_size` — размер сетки (по умолчанию 20)

### Нарушители (Intruders)

#### `IntruderConfig` (базовый)

[`services/patrol_planning/assets/intruders/models.py`](../assets/intruders/models.py)

Базовый конфиг для нарушителей:

- `pos` — позиция
- `is_random_spawned` — случайный спавн при reset()
- `catch_reward` — награда за поимку

#### `ControllableConfig(IntruderConfig)`

Управляемый нарушитель (управляется с клавиатуры).

#### `WandererConfig(IntruderConfig)`

Блуждающий нарушитель (движется случайно).

### Наблюдения (Observations)

#### `ObservationConfig` (базовый)

[`services/patrol_planning/assets/observations/models.py`](../assets/observations/models.py)

Базовая конфигурация области наблюдения:

- `size` — размер области (по умолчанию 3)

#### `ObsBoxConfig`

Конфигурация коробочного наблюдения:

- `layers_count` — число слоёв (по умолчанию 2)
