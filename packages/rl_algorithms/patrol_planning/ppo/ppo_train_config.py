from __future__ import annotations

from pydantic import BaseModel, Field


class PPOTrainConfig(BaseModel):
    """Гиперпараметры обучения PPO (Proximal Policy Optimization, SB3).
    """

    lr: float = Field(
        3e-4,
        description=(
            "Learning rate оптимизатора Adam для policy и value сетей. "
            "Уменьшение стабилизирует обучение, увеличение ускоряет сходимость "
            "но может вызвать расходимость."
        ),
    )
    gamma: float = Field(
        0.99,
        description=(
            "Коэффициент дисконтирования будущих наград. "
            "Близко к 1.0 — агент ценит долгосрочные награды; "
            "близко к 0 — максимизирует немедленную награду."
        ),
    )
    gae_lambda: float = Field(
        0.95,
        description=(
            "Lambda для GAE (Generalized Advantage Estimation). "
            "1.0 = Monte Carlo оценка (нет bias, высокая дисперсия); "
            "0.0 = TD(0) (низкая дисперсия, высокий bias). "
            "0.95 — стандартный компромисс."
        ),
    )
    ent_coef: float = Field(
        0.0,
        description=(
            "Коэффициент энтропийной регуляризации. "
            "Добавляет штраф за deterministic policy, поощряя исследование. "
            "0.0 = без регуляризации. Типичные значения: 0.0–0.05."
        ),
    )
    n_steps: int = Field(
        2048,
        description=(
            "Число шагов, собираемых с каждой среды перед каждым апдейтом. "
            "Большие значения = более низкая дисперсия, но больше памяти. "
            "n_steps * n_envs должно делиться на batch_size."
        ),
    )
    batch_size: int = Field(
        64,
        description=(
            "Размер мини-батча для градиентных апдейтов. "
            "Должен делить n_steps * n_envs без остатка."
        ),
    )
    n_epochs: int = Field(
        10,
        description=(
            "Число полных проходов по собранному роллауту за один апдейт. "
            "Больше эпох = лучшее использование данных, но риск переобучения на старых данных."
        ),
    )
    clip_range: float = Field(
        0.2,
        description=(
            "PPO ε-клиппинг для ratio политики. "
            "Ограничивает величину изменения политики за один апдейт. "
            "0.1–0.3 — типичный диапазон."
        ),
    )
    device: str = Field(
        "cpu",
        description=(
            "Torch device: 'cpu', 'cuda', 'cuda:0' и т.д. "
            "PPO по умолчанию обучается на CPU — это часто быстрее при малом batch_size."
        ),
    )
    n_envs: int = Field(
        4,
        description=(
            "Число параллельных сред для сбора данных. "
            "Увеличение ускоряет сбор траекторий, но требует больше памяти."
        ),
    )
    use_subproc_env: bool = Field(
        False,
        description=(
            "True = SubprocVecEnv (отдельные процессы, нет GIL). "
            "False = DummyVecEnv (один процесс, быстрый старт). "
            "SubprocVecEnv полезен когда env сама по себе медленная."
        ),
    )
    common_seed: bool = Field(
        True,
        description=(
            "True = все среды запускаются с одним seed. "
            "False = каждая среда получает seed+i — разнообразие стартовых условий."
        ),
    )
    n_stack: int = Field(
        1,
        description=(
            "Число последовательных наблюдений для стэкинга (VecFrameStack). "
            "1 = стэкинг отключён. Стэкинг даёт агенту контекст о динамике."
        ),
    )
    policy_type: str = Field(
        "mlp",
        description=(
            "Тип policy сети: 'mlp' для плоских наблюдений (MlpPolicy), "
            "'cnn' для сеточных/изображение-подобных наблюдений (CnnPolicy с CNNExtractor5x5)."
        ),
    )
    render_delay: float = Field(
        0.1,
        description="Пауза в секундах между кадрами рендера (только если show_render=True).",
    )
    verbose: int = Field(
        1,
        description="Уровень verbosity SB3: 0=тихий, 1=info, 2=debug.",
    )
    features_dim: int = Field(
        64,
        description=(
            "Размер выходного вектора CNNExtractor5x5. "
            "Используется только при policy_type='cnn'. "
            "Типичные значения: 64, 128."
        ),
    )
    cpu_cores_num: int | None = Field(
        None,
        description=(
            "Если задано — вызывает torch.set_num_threads(n) перед обучением. "
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
