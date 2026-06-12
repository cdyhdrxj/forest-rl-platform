from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalRunConfig:
    """Конфигурация одного запуска оценки агента.

    Один запуск — один агент, N эпизодов на одном конфиге.
    Для сравнения нескольких агентов запускать по одному:
    результаты сохраняются в CSV и затем агрегируются compare.py.
    """

    # --- Идентификация агента ---
    agent_name: str
    """Метка агента в CSV и на графиках (например, "drqn_v3_final")."""

    agent_type: str
    """Тип агента: "ppo" | "dqn" | "sac" | "a2c" | "rppo" | "drqn" |
    "random" | "greedy_intruder" | "greedy_damage"."""

    model_path: str | None = None
    """Путь к файлу модели (.zip для SB3-агентов, .pt для drqn).
    Не нужен для алгоритмических агентов (random, greedy_*)."""

    # --- Конфигурация среды ---
    config_path: str = ""
    """Путь к JSON-конфигу GridForestConfig."""

    exclude_layers: list[str] = field(default_factory=lambda: ["terrain", "rows", "cols"])
    """Слои, исключаемые из наблюдения."""

    # --- Параметры запуска ---
    n_episodes: int = 200
    """Количество эпизодов."""

    seed: int = 42
    """Базовый seed (каждый эпизод получает seed+ep)."""

    # --- Вывод ---
    output_dir: str = "services/patrol_planning/research/evaluation"
    """Корневая директория для результатов. Каждый run сохраняется в output_dir/run_id/."""

    run_id: str | None = None
    """Идентификатор запуска (имя подпапки). По умолчанию: agent_name + timestamp."""

    # --- Параметры DRQN (используются только при agent_type="drqn") ---
    drqn_device: str = "cpu"
    """Устройство для инференса DRQN ("cpu" или "cuda")."""

    # --- Рендер ---
    show_render: bool = False
    """Показывать ли Rich-рендер во время тестирования."""

    render_delay: float = 0.1
    """Задержка между шагами при включённом рендере (секунды)."""

    # --- TensorBoard ---
    tb_mode: bool = False
    """Если True — вместо PNG-файлов логировать результаты в TensorBoard."""

    tb_log_dir: str | None = None
    """Директория для TB-логов. По умолчанию: output_dir/tensorboard/."""
