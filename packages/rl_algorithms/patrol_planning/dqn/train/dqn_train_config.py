from __future__ import annotations

from pydantic import BaseModel, Field


class DQNTrainConfig(BaseModel):
    """Гиперпараметры обучения DQN (Deep Q-Network, SB3).
    """

    lr: float = Field(
        1e-4,
        description=(
            "Learning rate оптимизатора Adam для Q-сети. "
            "DQN обычно требует меньший LR чем PPO из-за нестабильности off-policy обучения."
        ),
    )
    gamma: float = Field(
        0.99,
        description=(
            "Коэффициент дисконтирования в Bellman target. "
            "Близко к 1.0 — долгосрочная оптимизация; близко к 0 — жадная."
        ),
    )
    batch_size: int = Field(
        32,
        description=(
            "Размер мини-батча, сэмплируемого из replay buffer за один градиентный шаг. "
            "Маленький батч = шумные градиенты, но быстрые апдейты."
        ),
    )
    buffer_size: int = Field(
        50_000,
        description=(
            "Максимальный размер replay buffer (в переходах). "
            "Больший буфер = лучшее покрытие состояний, но больше памяти."
        ),
    )
    learning_starts: int = Field(
        1_000,
        description=(
            "Число шагов случайного исследования перед первым градиентным апдейтом. "
            "Нужно для заполнения буфера достаточным количеством переходов."
        ),
    )
    target_update_interval: int = Field(
        500,
        description=(
            "Частота жёсткого копирования online-сети в target-сеть (в шагах среды). "
            "Маленькое значение = целевая сеть быстро устаревает; большое = нестабильность."
        ),
    )
    exploration_fraction: float = Field(
        0.2,
        description=(
            "Доля total_timesteps, на протяжении которой epsilon линейно убывает от 1.0. "
            "После этой доли epsilon = exploration_final_eps."
        ),
    )
    exploration_final_eps: float = Field(
        0.05,
        description=(
            "Финальное значение epsilon после завершения расписания убывания. "
            "Остаётся постоянным до конца обучения."
        ),
    )
    checkpoint_freq: int = Field(
        100_000,
        description="Сохранять чекпоинт каждые N шагов среды.",
    )
    checkpoint_name_prefix: str = Field(
        "dqn",
        description="Префикс имени файла для чекпоинтов CheckpointCallback.",
    )
    save_replay_buffer: bool = Field(
        False,
        description=(
            "Сохранять replay buffer вместе с чекпоинтом. "
            "Полезно для возобновления обучения, но сильно увеличивает размер файла."
        ),
    )
    use_cnn: bool = Field(
        True,
        description=(
            "True = использовать CNNExtractor5x5 (CnnPolicy) для пространственных наблюдений. "
            "False = плоская MlpPolicy."
        ),
    )
    features_dim: int = Field(
        128,
        description=(
            "Размер выходного вектора CNN feature extractor. "
            "Игнорируется при use_cnn=False."
        ),
    )
    n_envs: int = Field(
        1,
        description=(
            "Число параллельных сред. DQN обычно используется с 1 средой — "
            "несколько сред полезны для ускорения сбора данных."
        ),
    )
    common_seed: bool = Field(
        True,
        description=(
            "True = все среды с одним seed. "
            "False = seed+i для каждой среды."
        ),
    )
    use_torch_compile: bool = Field(
        False,
        description=(
            "Применить torch.compile к policy сети. "
            "Может дать 10–30% ускорение на GPU после прогрева. "
            "Требует cl.exe на Windows (см. torch_setup.py)."
        ),
    )
    torch_compile_mode: str = Field(
        "reduce-overhead",
        description=(
            "Режим torch.compile: "
            "'reduce-overhead' — уменьшает накладные расходы Python (рекомендован для RL); "
            "'max-autotune' — максимальная оптимизация, долгая компиляция; "
            "'default' — базовый режим."
        ),
    )
    device: str = Field(
        "cuda",
        description="Torch device: 'cpu', 'cuda', 'cuda:0' и т.д.",
    )
    verbose: int = Field(
        1,
        description="Уровень verbosity SB3: 0=тихий, 1=info, 2=debug.",
    )
    reset_num_timesteps: bool = Field(
        False,
        description=(
            "False = счётчик шагов продолжается с предыдущего обучения (полезно при дообучении). "
            "True = сброс счётчика в начало."
        ),
    )
    cpu_cores_num: int | None = Field(
        None,
        description=(
            "Если задано — вызывает torch.set_num_threads(n). "
            "None = PyTorch определяет число потоков автоматически."
        ),
    )
    normalize_rewards: bool = Field(
        False,
        description=(
            "Оборачивать ли vec_env в VecNormalize(norm_obs=False, norm_reward=True). "
            "Нормализует награды к нулевому среднему и единичной дисперсии в ходе обучения. "
            "Аналог normalize_rewards=True в AltDRQNTrainConfig."
        ),
    )
