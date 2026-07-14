from __future__ import annotations

from pydantic import BaseModel, Field


class AltDRQNTrainConfig(BaseModel):
    """Гиперпараметры обучения AltDRQN (кастомный DRQN с async GPU апдейтами).
    """

    lr: float = Field(
        5e-5,
        description=(
            "Learning rate оптимизатора Adam для DRQN Q-сети. "
            "Меньше чем у DQN (1e-4) из-за нестабильности LSTM градиентов и off-policy BPTT."
        ),
    )
    gamma: float = Field(
        0.995,
        description=(
            "Коэффициент дисконтирования в Bellman TD target. "
            "Высокое значение подходит для задач патрулирования с длинным горизонтом."
        ),
    )
    batch_size: int = Field(
        64,
        description=(
            "Число эпизодных последовательностей в одном батче для BPTT. "
            "Каждая последовательность имеет длину unroll_length."
        ),
    )
    lstm_hidden_size: int = Field(
        256,
        description=(
            "Размер скрытого состояния LSTM в DRQN сети. "
            "Увеличение улучшает memory capacity но замедляет inference."
        ),
    )
    unroll_length: int = Field(
        20,
        description=(
            "Длина последовательности для BPTT (Backpropagation Through Time). "
            "Более длинные последовательности захватывают дальние зависимости, "
            "но требуют больше памяти и времени на апдейт."
        ),
    )
    buffer_capacity: int = Field(
        10_000,
        description=(
            "Максимальное число полных эпизодов в replay buffer. "
            "В отличие от DQN, буфер хранит эпизоды целиком (не переходы) "
            "для корректной BPTT развёртки."
        ),
    )
    learning_starts: int = Field(
        5_000,
        description=(
            "Число шагов среды перед первым градиентным апдейтом. "
            "Нужно для заполнения буфера достаточным числом эпизодов."
        ),
    )
    target_update_freq: int = Field(
        2000,
        description=(
            "Частота жёсткого копирования online-сети в target-сеть (в шагах среды). "
            "Меньше = чаще обновляется цель, нестабильнее; больше = стабильнее, медленнее."
        ),
    )
    epsilon_decay_steps: int = Field(
        40_000,
        description=(
            "Число шагов среды для линейного затухания epsilon от 1.0 до epsilon_final. "
            "После этих шагов epsilon фиксируется на epsilon_final."
        ),
    )
    epsilon_final: float = Field(
        0.05,
        description=(
            "Минимальное значение epsilon после завершения расписания затухания. "
            "Поддерживает небольшое случайное исследование в течение всего обучения."
        ),
    )
    train_freq: int = Field(
        4,
        description=(
            "Запускать фоновый градиентный апдейт каждые N шагов среды. "
            "Меньше = частые апдейты (лучше sample efficiency, больше нагрузка на GPU)."
        ),
    )
    log_interval: int = Field(
        20,
        description=(
            "Выводить таблицу статистики каждые N завершённых эпизодов. "
            "Лог считается в эпизодах, не в шагах."
        ),
    )
    checkpoint_freq: int = Field(
        100_000,
        description="Сохранять .pt чекпоинт каждые N шагов среды.",
    )
    n_envs: int = Field(
        2,
        description=(
            "Число независимых экземпляров среды. "
            "Не multiprocessing — шаги выполняются последовательно в одном процессе. "
            "Больше сред = разнообразие опыта и более стабильные APR оценки."
        ),
    )
    use_amp: bool = Field(
        True,
        description=(
            "Использовать PyTorch Automatic Mixed Precision (float16) для GPU апдейтов. "
            "Ускоряет обучение на современных GPU с минимальной потерей точности. "
            "Автоматически отключается если device='cpu'."
        ),
    )
    burn_in: int = Field(
        10,
        description=(
            "Число шагов прогрева LSTM в начале каждой обучающей последовательности. "
            "Эти шаги не включаются в loss — только формируют hidden state. "
            "Устраняет смещение из-за zero-инициализации hidden state при сэмплировании. "
            "Рекомендуется 30-50% от unroll_length."
        ),
    )
    normalize_rewards: bool = Field(
        False,
        description=(
            "Применить log-преобразование к наградам: sign(r) * log1p(|r|). "
            "Сжимает большие значения (10^4 → 9.2), сохраняет знак и относительный порядок, "
            "не требует параметров и не уничтожает мелкие сигналы."
        ),
    )
    device: str = Field(
        "cuda",
        description=(
            "Torch device для модели и апдейтов: 'cpu' или 'cuda'. "
            "AMP (use_amp) работает только с 'cuda'."
        ),
    )
    common_seed: bool = Field(
        False,
        description=(
            "False = каждая среда получает seed+i — разнообразие начальных условий (рекомендуется). "
            "True = все среды с одним seed."
        ),
    )
    cpu_cores_num: int | None = Field(
        None,
        description=(
            "Если задано — вызывает torch.set_num_threads(n). "
            "None = PyTorch определяет число потоков автоматически."
        ),
    )
