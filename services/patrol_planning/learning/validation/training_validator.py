"""
TrainingValidator — лёгкий валидатор для периодической оценки во время обучения.

Запускается каждые N шагов, прогоняет K эпизодов на отдельной eval-среде
и возвращает DataFrame с метриками (без сохранения графиков и файлов).

Поддерживает все 4 алгоритма:
  - PPO, DQN, RPPO — через SB3ValidationCallback
  - AltDRQN        — через TrainingValidator.maybe_validate()

Пример (PPO / DQN / RPPO):
    from services.patrol_planning.learning.validation.training_validator import (
        SB3ValidationCallback, ValidationConfig,
    )
    val_cb = SB3ValidationCallback(
        ValidationConfig(config_path="path/to/config.json", freq=20_000, n_episodes=20),
        model_type="ppo",   # или "dqn" / "rppo"
    )
    model.learn(..., callback=[SpeedLoggerCallback(), val_cb])
    # val_cb.results — list[pd.DataFrame], по одному на каждую валидацию

Пример (AltDRQN):
    validator = TrainingValidator(ValidationConfig(config_path="...", freq=20_000))
    while agent._step < total_timesteps:
        ...
        df = validator.maybe_validate(agent._step, AltDRQNLiveAgent(agent))
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from stable_baselines3.common.callbacks import BaseCallback

from services.patrol_planning.learning.test.evaluation.agent import EvalAgent
from services.patrol_planning.learning.test.evaluation.collector import EvalCollector
from services.patrol_planning.learning.test.evaluation.runner import _run_single_episode


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class ValidationConfig:
    """Конфигурация периодической валидации во время обучения."""

    config_path: str
    """Путь к JSON-конфигу GridForestConfig для eval-среды."""

    exclude_layers: list[str] = field(default_factory=lambda: ["terrain", "rows", "cols"])
    """Слои, исключаемые из наблюдения (должны совпадать с обучающей средой)."""

    freq: int = 10_000
    """Каждые N обучающих шагов запускать валидацию."""

    n_episodes: int = 20
    """Число эпизодов за одну валидацию."""

    seed: int = 999
    """Базовый seed. Эпизод ep использует seed=seed+ep."""

    drqn_device: str = "cpu"
    """Устройство для инференса AltDRQNLiveAgent."""

    verbose: bool = True
    """Печатать краткий итог после каждой валидации."""

    log_images: bool = True
    """Логировать ли изображения в TensorBoard после каждой валидации."""

    shared_train_state: object = None
    """Если задан — результаты валидации записываются в shared_train_state["val_metrics"]."""


# ---------------------------------------------------------------------------
# TensorBoard image helpers
# ---------------------------------------------------------------------------

def _fig_to_tensor(fig) -> "torch.Tensor":
    import io
    import torch
    import numpy as np
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    import matplotlib.pyplot as plt
    plt.close(fig)
    buf.seek(0)
    img = np.array(Image.open(buf))[:, :, :3]  # HWC RGB
    return torch.from_numpy(img).permute(2, 0, 1)  # CHW


def _get_sb3_tb_writer(model):
    from stable_baselines3.common.logger import TensorBoardOutputFormat
    for fmt in model.logger.output_formats:
        if isinstance(fmt, TensorBoardOutputFormat):
            return fmt.writer
    return None


_ACTION_LABELS = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]


def _log_images_to_tb(collector: "EvalCollector", writer, step: int) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    hm = collector.get_heatmap()
    if hm is not None:
        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(hm, cmap="hot", interpolation="nearest")
        fig.colorbar(im, ax=ax, label="посещений")
        ax.set_title("Agent visits")
        ax.axis("off")
        writer.add_image("val/img/agent_visits", _fig_to_tensor(fig), step)

    hm_mean = collector.get_idleness_heatmap()
    if hm_mean is not None:
        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(hm_mean, cmap="RdYlGn_r", interpolation="nearest")
        fig.colorbar(im, ax=ax, label="шагов")
        ax.set_title("Idleness mean")
        ax.axis("off")
        writer.add_image("val/img/idleness_mean", _fig_to_tensor(fig), step)

    hm_max = collector.get_max_idleness_heatmap()
    if hm_max is not None:
        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(hm_max, cmap="RdYlGn_r", interpolation="nearest")
        fig.colorbar(im, ax=ax, label="шагов")
        ax.set_title("Idleness max")
        ax.axis("off")
        writer.add_image("val/img/idleness_max", _fig_to_tensor(fig), step)

    action_hist = collector.get_action_histogram(normalize=True)
    if action_hist is not None:
        fig, ax = plt.subplots(figsize=(5, 3))
        bars = ax.bar(_ACTION_LABELS, action_hist)
        for bar, v in zip(bars, action_hist):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.1%}", ha="center", va="bottom", fontsize=8)
        ax.set_title("Action distribution")
        ax.set_ylim(0, 1)
        writer.add_image("val/img/action_hist", _fig_to_tensor(fig), step)

    inv = collector.get_invalid_action_counts()
    if inv:
        means = [np.mean(inv.get("invalid_out", [0])),
                 np.mean(inv.get("invalid_block", [0]))]
        fig, ax = plt.subplots(figsize=(4, 3))
        bars = ax.bar(["out_of_bounds", "impassable"], means, color=["#e74c3c", "#e67e22"])
        for bar, v in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.2f}", ha="center", va="bottom", fontsize=9)
        ax.set_title("Invalid actions / episode")
        ax.set_ylabel("mean per episode")
        writer.add_image("val/img/invalid_hist", _fig_to_tensor(fig), step)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_eval_env(config_path: str, exclude_layers: list[str]):
    """Создать GridForest из JSON-конфига.

    metrics_config.enabled остаётся True (по умолчанию) — метрики нужны.
    Возвращает (env, grid_size).
    """
    from services.patrol_planning.assets.envs.forest import GridForest
    from services.patrol_planning.assets.envs.models import GridForestConfig
    from services.patrol_planning.service.models import GridWorldTrainState

    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    config = GridForestConfig.model_validate(raw)
    config.obs_config.exclude_layers = exclude_layers
    env = GridForest.load(config)
    env.train_state = GridWorldTrainState()
    return env, config.grid_size


def _print_val_summary(df: pd.DataFrame, step: Optional[int] = None) -> None:
    """Краткий вывод результатов: одна строка в консоль."""
    prefix = f"[val@{step}]" if step is not None else "[val]"
    mean_r = df["total_reward"].mean() if "total_reward" in df.columns else float("nan")
    parts = [f"{prefix}  ep={len(df)}  R={mean_r:.2f}"]
    if "metric_Z" in df.columns:
        parts.append(f"Z={df['metric_Z'].mean():.4f}")
    if "catch_rate" in df.columns:
        parts.append(f"catch={df['catch_rate'].mean():.1%}")
    print("  ".join(parts))


# ---------------------------------------------------------------------------
# Live agent wrappers
# ---------------------------------------------------------------------------

class _LiveSB3Agent(EvalAgent):
    """Обёртка над обычным SB3-агентом (PPO, DQN) для использования в валидаторе."""

    def __init__(self, model) -> None:
        self._model = model

    def predict(self, obs: np.ndarray) -> int:
        action, _ = self._model.predict(obs, deterministic=True)
        return int(action)


class _LiveRecurrentAgent(EvalAgent):
    """Обёртка над RecurrentPPO — хранит LSTM-состояние между шагами."""

    def __init__(self, model) -> None:
        self._model = model
        self._lstm_states = None
        self._ep_starts = np.ones((1,), dtype=bool)

    def reset(self) -> None:
        self._lstm_states = None
        self._ep_starts = np.ones((1,), dtype=bool)

    def predict(self, obs: np.ndarray) -> int:
        action, self._lstm_states = self._model.predict(
            obs,
            state=self._lstm_states,
            episode_start=self._ep_starts,
            deterministic=True,
        )
        self._ep_starts = np.zeros((1,), dtype=bool)
        return int(action)


class AltDRQNLiveAgent(EvalAgent):
    """Обёртка над AltDRQNAgent для использования в TrainingValidator.

    Запускает инференс на одной среде (без батчевого режима).
    LSTM-состояние сбрасывается при reset().

    Args:
        agent:  экземпляр AltDRQNAgent из пакета alt_drqn
        device: устройство для torch-тензоров ("cpu" или "cuda")
    """

    def __init__(self, agent, device: str = "cpu") -> None:
        import torch
        self._agent = agent
        try:
            self._device = next(agent.net.parameters()).device
        except StopIteration:
            self._device = torch.device(device)
        self._hidden = agent.net.init_hidden(1, self._device)

    def reset(self) -> None:
        self._hidden = self._agent.net.init_hidden(1, self._device)

    def predict(self, obs: np.ndarray) -> int:
        import torch
        with torch.no_grad():
            obs_t = torch.tensor(
                obs[np.newaxis, np.newaxis],  # (1, 1, C, H, W)
                dtype=torch.float32,
                device=self._device,
            )
            q_values, self._hidden = self._agent.net(obs_t, self._hidden)
        return int(q_values[0, 0].argmax().item())


# ---------------------------------------------------------------------------
# TrainingValidator
# ---------------------------------------------------------------------------

class TrainingValidator:
    """Периодический валидатор для использования во время обучения.

    Создаёт eval-среду один раз при инициализации и переиспользует её
    при каждом вызове run_validation() / maybe_validate().

    Для AltDRQN:
        validator = TrainingValidator(cfg)
        while agent._step < total_timesteps:
            ...
            df = validator.maybe_validate(agent._step, AltDRQNLiveAgent(agent))
    """

    def __init__(self, cfg: ValidationConfig) -> None:
        self.cfg = cfg
        self._last_validated_step: int = 0
        self._env, self._grid_size = _build_eval_env(cfg.config_path, cfg.exclude_layers)

    def run_validation(
        self, agent: EvalAgent, step: Optional[int] = None, writer=None,
        save_dir: Optional[str] = None,
    ) -> pd.DataFrame:
        """Прогнать n_episodes эпизодов и вернуть DataFrame с метриками.

        Args:
            save_dir: Если указан, сохраняет сырые данные (heatmap_*.npy,
                      action_histogram.npy, episodes.csv) через collector.save_all().
        """
        collector = EvalCollector(
            grid_size=self._grid_size,
            run_id="val",
            agent_name="live",
            max_episodes=self.cfg.n_episodes + 10,
        )
        self._env.rl_logger = collector
        self._env.reset(seed=self.cfg.seed)
        for ep in range(self.cfg.n_episodes):
            agent.reset()
            _run_single_episode(self._env, agent)
            self._env.reset(seed=self.cfg.seed + ep + 1)
        self._env.rl_logger = None
        df = collector.episodes_to_df()
        if self.cfg.verbose:
            _print_val_summary(df, step=step)
        if writer is not None and self.cfg.log_images and not df.empty:
            _log_images_to_tb(collector, writer, step or 0)
        if save_dir is not None:
            collector.save_all(save_dir)
            collector.save_plots(save_dir)
        if self.cfg.shared_train_state is not None and not df.empty:
            _VAL_COLS = ("total_reward", "metric_Z", "metric_M_idleness",
                         "metric_M_damage", "metric_M_move", "catch_rate")
            val_m = {col: round(float(df[col].mean()), 4)
                     for col in _VAL_COLS if col in df.columns}
            if val_m:
                self.cfg.shared_train_state["val_metrics"] = val_m
                if step is not None:
                    self.cfg.shared_train_state["val_step"] = step
        return df

    def maybe_validate(
        self, step: int, agent: EvalAgent, writer=None
    ) -> Optional[pd.DataFrame]:
        """Запустить валидацию, если прошло cfg.freq шагов с последней.

        Возвращает DataFrame или None, если валидация не запускалась.
        """
        if step - self._last_validated_step < self.cfg.freq:
            return None
        self._last_validated_step = step
        return self.run_validation(agent, step=step, writer=writer)


# ---------------------------------------------------------------------------
# SB3ValidationCallback — для PPO / DQN / RPPO
# ---------------------------------------------------------------------------

class SB3ValidationCallback(BaseCallback):
    """SB3-коллбек для периодической валидации во время обучения.

    Поддерживаемые алгоритмы: "ppo", "dqn", "rppo".

    Args:
        cfg:        ValidationConfig с параметрами валидации
        model_type: "ppo" | "dqn" | "rppo"

    Атрибуты после обучения:
        results: list[pd.DataFrame] — по одному DataFrame на каждую валидацию

    Пример:
        val_cb = SB3ValidationCallback(
            ValidationConfig(config_path="cfg.json", freq=20_000, n_episodes=20),
            model_type="rppo",
        )
        model.learn(..., callback=[SpeedLoggerCallback(), val_cb])
    """

    _SUPPORTED = ("ppo", "dqn", "rppo")

    def __init__(self, cfg: ValidationConfig, model_type: str) -> None:
        super().__init__(verbose=0)
        if model_type not in self._SUPPORTED:
            raise ValueError(
                f"model_type должен быть одним из {self._SUPPORTED}, получено: {model_type!r}"
            )
        self.validator = TrainingValidator(cfg)
        self.model_type = model_type
        self.results: list[pd.DataFrame] = []

    _VAL_TB_COLS = (
        "total_reward", "metric_Z", "metric_M_idleness",
        "metric_M_damage", "metric_M_move", "catch_rate",
    )

    def _on_step(self) -> bool:
        step = self.num_timesteps
        if step - self.validator._last_validated_step < self.validator.cfg.freq:
            return True
        agent = self._make_live_agent()
        _tb_writer = _get_sb3_tb_writer(self.model)
        df = self.validator.run_validation(agent, step=step, writer=_tb_writer)
        self.validator._last_validated_step = step
        self.results.append(df)

        if not df.empty:
            for col in self._VAL_TB_COLS:
                if col in df.columns:
                    self.model.logger.record(f"val/{col}", float(df[col].mean()))
            self.model.logger.dump(step)
        return True

    def _make_live_agent(self) -> EvalAgent:
        if self.model_type == "rppo":
            return _LiveRecurrentAgent(self.model)
        return _LiveSB3Agent(self.model)
