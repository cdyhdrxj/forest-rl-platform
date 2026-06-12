from __future__ import annotations

from pydantic import BaseModel, Field


class RPPOTrainConfig(BaseModel):
    """Гиперпараметры обучения RecurrentPPO (LSTM-PPO, sb3-contrib).

    Не содержит путей к файлам, конфигу среды или total_timesteps — это
    аргументы функции run_training(). Все дефолты соответствуют ранее
    захардкоженным значениям в run_training_rppo().
    """

    lr: float = Field(
        3e-4,
        description=(
            "Learning rate оптимизатора Adam для policy, value и LSTM сетей. "
            "Типичный диапазон: 1e-4 — 3e-4 для обучения с нуля, 1e-4 или ниже для дообучения."
        ),
    )
    gamma: float = Field(
        0.995,
        description=(
            "Коэффициент дисконтирования. "
            "Высокое значение (0.995–1.0) подходит для патрулирования с длинным горизонтом, "
            "где кумулятивная награда важна на сотнях шагов."
        ),
    )
    gae_lambda: float = Field(
        0.95,
        description=(
            "Lambda для GAE (Generalized Advantage Estimation). "
            "1.0 = Monte Carlo (нет bias, высокая дисперсия); "
            "0.0 = TD(0) (низкая дисперсия, высокий bias). "
            "0.95 — стандартный компромисс для RecurrentPPO."
        ),
    )
    ent_coef: float = Field(
        0.03,
        description=(
            "Коэффициент энтропийной регуляризации. "
            "Более высокое значение чем у PPO (0.0) — поощряет исследование "
            "в частично наблюдаемой среде (POMDP)."
        ),
    )
    n_steps: int = Field(
        256,
        description=(
            "Число шагов роллаута с каждой среды перед апдейтом. "
            "n_steps * n_envs должно делиться на batch_size без остатка. "
            "Меньшее значение чем у PPO из-за LSTM состояния."
        ),
    )
    batch_size: int = Field(
        64,
        description=(
            "Размер мини-батча. "
            "Должен делить n_steps * n_envs без остатка."
        ),
    )
    lstm_hidden_size: int = Field(
        256,
        description=(
            "Число скрытых единиц в LSTM ячейке на каждом слое. "
            "Увеличение улучшает memory capacity, но замедляет обучение."
        ),
    )
    n_lstm_layers: int = Field(
        1,
        description=(
            "Число стэкированных LSTM слоёв. "
            "1 достаточно для большинства задач; 2+ редко даёт улучшение."
        ),
    )
    shared_lstm: bool = Field(
        False,
        description=(
            "True = актор и критик делят LSTM веса. "
            "False = отдельный LSTM для каждого (стандартно). "
            "Shared_lstm уменьшает параметры, но может снизить качество."
        ),
    )
    use_cnn: bool = Field(
        True,
        description=(
            "True = использовать CNNExtractor5x5 для пространственных наблюдений. "
            "False = MLP extractor с net_arch слоями."
        ),
    )
    features_dim: int = Field(
        128,
        description=(
            "Размер выходного вектора CNN feature extractor. "
            "Игнорируется при use_cnn=False."
        ),
    )
    net_arch: list[int] = Field(
        default_factory=lambda: [64, 64],
        description=(
            "Размеры скрытых слоёв MLP extractor (только когда use_cnn=False). "
            "Например [64, 64] = два скрытых слоя по 64 нейрона."
        ),
    )
    n_envs: int = Field(
        4,
        description=(
            "Число параллельных сред для сбора роллаутов. "
            "Увеличение ускоряет сбор данных."
        ),
    )
    use_subproc_env: bool = Field(
        False,
        description=(
            "True = SubprocVecEnv (отдельные процессы, нет GIL). "
            "False = DummyVecEnv (один процесс). "
            "SubprocVecEnv полезен при медленной среде."
        ),
    )
    common_seed: bool = Field(
        True,
        description=(
            "True = все среды с одним seed. "
            "False = seed+i для каждой среды — разнообразие опыта."
        ),
    )
    use_torch_compile: bool = Field(
        False,
        description=(
            "Применить torch.compile к policy сети. "
            "Backend автоматически выбирается: 'inductor' для GPU, 'aot_eager' для CPU. "
            "Требует cl.exe на Windows (см. torch_setup.py)."
        ),
    )
    device: str = Field(
        "cuda",
        description="Torch device: 'cpu', 'cuda', 'cuda:0' и т.д.",
    )
    checkpoint_save_freq: int = Field(
        100_000,
        description="Сохранять чекпоинт каждые N шагов среды через CheckpointCallback.",
    )
    checkpoint_name_prefix: str = Field(
        "rppo",
        description="Префикс имени файла для чекпоинтов.",
    )
    save_replay_buffer: bool = Field(
        False,
        description=(
            "Сохранять replay buffer с чекпоинтом. "
            "PPO не использует replay buffer, параметр оставлен для единообразия API."
        ),
    )
    verbose: int = Field(
        1,
        description="Уровень verbosity SB3: 0=тихий, 1=info, 2=debug.",
    )
    cpu_cores_num: int | None = Field(
        None,
        description=(
            "Если задано — вызывает torch.set_num_threads(n). "
            "None = PyTorch определяет число потоков автоматически."
        ),
    )
