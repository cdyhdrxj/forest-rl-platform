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
