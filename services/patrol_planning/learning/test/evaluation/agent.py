from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class EvalAgent(ABC):
    """Абстрактный агент для системы оценки.

    Интерфейс намеренно минимален: predict() + reset().
    reset() вызывается runner-ом в начале каждого эпизода — стандартные агенты
    игнорируют его (no-op), рекуррентные сбрасывают LSTM-состояние.
    """

    @abstractmethod
    def predict(self, obs: np.ndarray) -> int:
        """Вернуть действие (0-4) для текущего наблюдения."""
        ...

    def reset(self) -> None:
        """Сброс внутреннего состояния агента в начале эпизода."""
        pass


class SB3EvalAgent(EvalAgent):
    """Обёртка над стандартными алгоритмами Stable-Baselines3 (PPO, DQN, SAC, A2C)."""

    SUPPORTED = ("ppo", "dqn", "sac", "a2c")

    def __init__(self, model_path: str, algorithm: str) -> None:
        algorithm = algorithm.lower()
        if algorithm not in self.SUPPORTED:
            raise ValueError(
                f"Неподдерживаемый алгоритм: {algorithm!r}. "
                f"Доступные: {self.SUPPORTED}"
            )
        if algorithm == "dqn":
            from stable_baselines3 import DQN
            self.model = DQN.load(model_path)
        elif algorithm == "sac":
            from stable_baselines3 import SAC
            self.model = SAC.load(model_path)
        elif algorithm == "a2c":
            from stable_baselines3 import A2C
            self.model = A2C.load(model_path)
        else:
            from stable_baselines3 import PPO
            self.model = PPO.load(model_path)

    def predict(self, obs: np.ndarray) -> int:
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)


class RecurrentSB3EvalAgent(EvalAgent):
    """RecurrentPPO из sb3_contrib — хранит LSTM-состояние между шагами.

    При вызове reset() состояние сбрасывается. Обязательно вызывать reset()
    перед каждым новым эпизодом (runner делает это автоматически).
    """

    def __init__(self, model_path: str) -> None:
        try:
            from sb3_contrib import RecurrentPPO
        except ImportError as e:
            raise ImportError(
                "Для RecurrentPPO требуется пакет sb3_contrib: pip install sb3-contrib"
            ) from e
        self.model = RecurrentPPO.load(model_path)
        self._lstm_states = None
        self._episode_starts = np.ones((1,), dtype=bool)

    def reset(self) -> None:
        self._lstm_states = None
        self._episode_starts = np.ones((1,), dtype=bool)

    def predict(self, obs: np.ndarray) -> int:
        action, self._lstm_states = self.model.predict(
            obs,
            state=self._lstm_states,
            episode_start=self._episode_starts,
            deterministic=True,
        )
        self._episode_starts = np.zeros((1,), dtype=bool)
        return int(action)


class AltDRQNEvalAgent(EvalAgent):
    """Обёртка над пользовательским DRQN (alt_drqn) — хранит LSTM-состояние между шагами.

    Загружает .pt-чекпоинт (формат alt_drqn), восстанавливает веса DRQNNet.
    observation_space и n_actions передаются из среды через runner._make_agent(env).
    reset() вызывается runner-ом в начале каждого эпизода — сбрасывает LSTM-состояние.
    """

    def __init__(
        self,
        model_path: str,
        observation_space,
        n_actions: int,
        device: str = "cpu",
    ) -> None:
        import torch
        try:
            from packages.rl_algorithms.patrol_planning.alt_drqn.networks.drqn_net import DRQNNet
        except ImportError as e:
            raise ImportError(
                "Для AltDRQNEvalAgent требуется пакет alt_drqn. "
                "Убедитесь, что packages/rl_algorithms/patrol_planning/alt_drqn доступен."
            ) from e

        self._torch = torch
        self.device = torch.device(device)
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        sd = checkpoint["net_state_dict"]
        # Архитектурные параметры выводятся из весов, а не дублируются в конфиге
        lstm_hidden_size = sd["lstm.weight_hh_l0"].shape[0] // 4
        features_dim = sd["lstm.weight_ih_l0"].shape[1]
        self.net = DRQNNet(observation_space, n_actions, lstm_hidden_size, features_dim).to(self.device)
        self.net.load_state_dict(sd)
        self.net.eval()
        self._hidden = self.net.init_hidden(1, self.device)

    def reset(self) -> None:
        self._hidden = self.net.init_hidden(1, self.device)

    def predict(self, obs: np.ndarray) -> int:
        torch = self._torch
        with torch.no_grad():
            obs_t = torch.tensor(
                obs[np.newaxis, np.newaxis],  # (1, 1, C, H, W) — batch=1, T=1
                dtype=torch.float32,
                device=self.device,
            )
            q_values, self._hidden = self.net(obs_t, self._hidden)
        return int(q_values[0, 0].argmax().item())


class RandomEvalAgent(EvalAgent):
    """Базовый случайный агент — равномерно сэмплирует из 5 действий."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed)

    def predict(self, obs: np.ndarray) -> int:
        return int(self._rng.integers(0, 5))


# Порядок слоёв в GridWorld/GridForest (insertion order)
_LAYER_ORDER = ["terrain", "intruders", "rows", "cols", "passability", "value", "idleness"]


def build_channel_map(exclude_layers: list[str]) -> dict[str, int]:
    """Вычислить индексы каналов obs по списку исключённых слоёв."""
    excluded = set(exclude_layers)
    return {
        name: idx
        for idx, name in enumerate(n for n in _LAYER_ORDER if n not in excluded)
    }


_ACTION_DELTA = {0: (-1, 0), 1: (1, 0), 2: (0, -1), 3: (0, 1)}


def _direction_to(dr: int, dc: int) -> int:
    """Действие (0=UP,1=DOWN,2=LEFT,3=RIGHT) в сторону смещения (dr, dc)."""
    if abs(dr) >= abs(dc):
        return 0 if dr < 0 else 1
    return 2 if dc < 0 else 3


class LawnmowerAgent(EvalAgent):
    """Обходит карту строками (boustrophedon / lawnmower pattern).

    Не использует нейросеть. Читает позицию агента из каналов rows/cols obs
    (нормированы на grid_size-1) и passability чтобы обходить препятствия.

    Требование: exclude_layers НЕ должен содержать "rows", "cols", "passability".
    Стандартный exclude_layers=["terrain"] подходит.

    Паттерн для grid_size=4:
        (0,0)→(0,1)→(0,2)→(0,3)
                              ↓
        (1,3)←(1,2)←(1,1)←(1,0)
        ↓
        (2,0)→(2,1)→(2,2)→(2,3)
    """

    def __init__(self, grid_size: int, channel_map: dict[str, int], seed=None) -> None:
        self._grid_size = grid_size
        self._ch_pass = channel_map.get("passability")
        self._ch_rows = channel_map.get("rows")
        self._ch_cols = channel_map.get("cols")
        self._seq = self._build_sequence()
        self._idx = 0

    def _build_sequence(self) -> list[tuple[int, int]]:
        cells = []
        for row in range(self._grid_size):
            cols = range(self._grid_size) if row % 2 == 0 else range(self._grid_size - 1, -1, -1)
            for col in cols:
                cells.append((row, col))
        return cells

    def reset(self) -> None:
        self._idx = 0

    def _read_pos(self, obs: np.ndarray) -> tuple[int, int] | None:
        if self._ch_rows is None or self._ch_cols is None:
            return None
        ch = obs.shape[1] // 2
        cw = obs.shape[2] // 2
        row = round(float(obs[self._ch_rows, ch, cw]) * (self._grid_size - 1))
        col = round(float(obs[self._ch_cols, ch, cw]) * (self._grid_size - 1))
        return int(np.clip(row, 0, self._grid_size - 1)), int(np.clip(col, 0, self._grid_size - 1))

    def _is_passable(self, obs: np.ndarray, action: int) -> bool:
        if self._ch_pass is None:
            return True
        dh, dw = _ACTION_DELTA[action]
        ch = obs.shape[1] // 2
        cw = obs.shape[2] // 2
        nh, nw = ch + dh, cw + dw
        if not (0 <= nh < obs.shape[1] and 0 <= nw < obs.shape[2]):
            return False
        return float(obs[self._ch_pass, nh, nw]) > 0.0

    def predict(self, obs: np.ndarray) -> int:
        pos = self._read_pos(obs)
        if pos is None:
            return 4  # STAY: каналы rows/cols отсутствуют

        cur_r, cur_c = pos

        # Шагаем по последовательности пока текущая цель уже достигнута
        if self._seq[self._idx] == (cur_r, cur_c):
            self._idx = (self._idx + 1) % len(self._seq)

        # Ищем ближайшую достижимую цель (пропускаем заблокированные)
        for _ in range(len(self._seq)):
            target_r, target_c = self._seq[self._idx]
            dr = target_r - cur_r
            dc = target_c - cur_c

            if dr == 0 and dc == 0:
                self._idx = (self._idx + 1) % len(self._seq)
                continue

            # Основное действие: сначала строка, потом столбец
            primary = (0 if dr < 0 else 1) if dr != 0 else (2 if dc < 0 else 3)

            if self._is_passable(obs, primary):
                return primary

            # Попробовать вторую ось (обойти препятствие)
            if dr != 0 and dc != 0:
                secondary = 2 if dc < 0 else 3
                if self._is_passable(obs, secondary):
                    return secondary

            # Цель недостижима — пропускаем её
            self._idx = (self._idx + 1) % len(self._seq)

        return 4  # STAY (окружён препятствиями — крайне маловероятно)


class GreedyIntruderAgent(EvalAgent):
    """Идёт к ближайшему видимому нарушителю.

    Если нарушителей нет в obs — фоллбек на RandomPolicy (fallback_random=True)
    или STAY (fallback_random=False).
    """

    def __init__(
        self,
        channel_map: dict[str, int],
        seed: int | None = None,
        fallback_random: bool = True,
    ) -> None:
        self._ch = channel_map.get("intruders")
        self._fallback = RandomEvalAgent(seed=seed) if fallback_random else None

    def predict(self, obs: np.ndarray) -> int:
        if self._ch is not None:
            layer = obs[self._ch]
            center_h = layer.shape[0] // 2
            center_w = layer.shape[1] // 2
            positions = np.argwhere(layer > 0.5)
            if len(positions) > 0:
                dists = np.abs(positions[:, 0] - center_h) + np.abs(positions[:, 1] - center_w)
                nearest = positions[np.argmin(dists)]
                dr = int(nearest[0]) - center_h
                dc = int(nearest[1]) - center_w
                if dr != 0 or dc != 0:
                    return _direction_to(dr, dc)
        if self._fallback is not None:
            return self._fallback.predict(obs)
        return 4  # STAY


class GreedyDamageAgent(EvalAgent):
    """Движется к ячейке с максимальным приоритетом value × idleness в obs.

    «Предполагаемая» ценная ячейка: берётся из текущего окна наблюдения.
    Если ценных ячеек нет — фоллбек на RandomPolicy (fallback_random=True)
    или STAY (fallback_random=False).
    """

    def __init__(
        self,
        channel_map: dict[str, int],
        seed: int | None = None,
        fallback_random: bool = True,
    ) -> None:
        self._ch_value = channel_map.get("value")
        self._ch_idleness = channel_map.get("idleness")
        self._fallback = RandomEvalAgent(seed=seed) if fallback_random else None

    def predict(self, obs: np.ndarray) -> int:
        if self._ch_value is not None:
            value = obs[self._ch_value]  # нормировано [0, 1]
            if self._ch_idleness is not None:
                idleness = np.clip(obs[self._ch_idleness], 0.0, None)
                priority = value * idleness
            else:
                priority = value.copy()

            center_h = priority.shape[0] // 2
            center_w = priority.shape[1] // 2
            priority[center_h, center_w] = 0.0  # игнорируем текущую позицию

            max_idx = np.unravel_index(priority.argmax(), priority.shape)
            if priority[max_idx] > 0.0:
                dr = int(max_idx[0]) - center_h
                dc = int(max_idx[1]) - center_w
                if dr != 0 or dc != 0:
                    return _direction_to(dr, dc)

        if self._fallback is not None:
            return self._fallback.predict(obs)
        return 4  # STAY


def make_agent(agent_type: str, model_path: str | None, seed: int | None = None, **kwargs) -> EvalAgent:
    """Фабрика агентов по типу.

    Args:
        agent_type: "ppo" | "dqn" | "sac" | "a2c" | "rppo" | "drqn" | "random" |
                    "greedy_intruder" | "greedy_damage"
        model_path: Путь к файлу модели (.zip для SB3, .pt для drqn). Не нужен для алгоритмических агентов.
        seed: Seed для RandomEvalAgent / фоллбека.
        **kwargs: Дополнительные параметры.
            Для drqn: observation_space, n_actions, device.
            Для greedy_*: channel_map (dict[str, int]), fallback_random (bool, default True).
    """
    t = agent_type.lower()
    if t == "random":
        return RandomEvalAgent(seed=seed)
    if t == "lawnmower":
        if "grid_size" not in kwargs or "channel_map" not in kwargs:
            raise ValueError(
                "grid_size и channel_map обязательны для LawnmowerAgent. "
                "Они инжектируются автоматически через EvaluationRunner."
            )
        return LawnmowerAgent(grid_size=kwargs["grid_size"], channel_map=kwargs["channel_map"])
    if t == "greedy_intruder":
        if "channel_map" not in kwargs:
            raise ValueError(
                "channel_map обязателен для GreedyIntruderAgent. "
                "Он инжектируется автоматически через EvaluationRunner."
            )
        return GreedyIntruderAgent(
            channel_map=kwargs["channel_map"],
            seed=seed,
            fallback_random=kwargs.get("fallback_random", True),
        )
    if t == "greedy_damage":
        if "channel_map" not in kwargs:
            raise ValueError(
                "channel_map обязателен для GreedyDamageAgent. "
                "Он инжектируется автоматически через EvaluationRunner."
            )
        return GreedyDamageAgent(
            channel_map=kwargs["channel_map"],
            seed=seed,
            fallback_random=kwargs.get("fallback_random", True),
        )
    if t in ("rppo", "recurrent_ppo"):
        if model_path is None:
            raise ValueError("model_path обязателен для RecurrentSB3EvalAgent")
        return RecurrentSB3EvalAgent(model_path)
    if t in ("drqn", "alt_drqn"):
        if model_path is None:
            raise ValueError("model_path обязателен для AltDRQNEvalAgent")
        if "observation_space" not in kwargs or "n_actions" not in kwargs:
            raise ValueError(
                "Для AltDRQNEvalAgent необходимы observation_space и n_actions. "
                "Они инжектируются автоматически через EvaluationRunner."
            )
        return AltDRQNEvalAgent(model_path, **kwargs)
    if t in SB3EvalAgent.SUPPORTED:
        if model_path is None:
            raise ValueError(f"model_path обязателен для {t.upper()}")
        return SB3EvalAgent(model_path, t)
    raise ValueError(
        f"Неизвестный тип агента: {agent_type!r}. "
        f"Доступные: ppo, dqn, sac, a2c, rppo, drqn, random, lawnmower, greedy_intruder, greedy_damage"
    )
