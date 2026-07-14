from __future__ import annotations

import threading
from collections import deque
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
import pandas as pd
from stable_baselines3.common.logger import KVWriter

from services.patrol_planning.learning.logging.models import EpisodeRecord, StepRecord

if TYPE_CHECKING:
    pass


class RLLogger:
    """
    Research logger for GridForest.

    Attach to env before training:
        env.rl_logger = RLLogger(grid_size=20, run_id="exp_01")

    Access results after training:
        df = env.rl_logger.episodes_to_df()
        heatmap = env.rl_logger.get_heatmap()
    """

    N_ACTIONS = 5  # UP, DOWN, LEFT, RIGHT, STAY
    ACTION_NAMES = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]

    def __init__(
        self,
        grid_size: int,
        max_episodes: int = 2000,
        run_id: Optional[str] = None,
    ) -> None:
        self.grid_size = grid_size
        self.max_episodes = max_episodes
        self.run_id = run_id

        self.heatmap = np.zeros((grid_size, grid_size), dtype=np.int64)
        self.action_counts = np.zeros(self.N_ACTIONS, dtype=np.int64)

        # Накопитель карты средних интервалов простоя (из IdlenessMetric.calculate_metric).
        # Обновляется в конце каждого эпизода; get_idleness_heatmap() возвращает среднее.
        self._idleness_acc = np.zeros((grid_size, grid_size), dtype=np.float64)
        self._idleness_count: int = 0

        # Накопители тепловых карт нарушителей и урона.
        # Обновляются в конце эпизода через on_episode_end(); геттеры возвращают среднее.
        self._intruder_hm_acc = np.zeros((grid_size, grid_size), dtype=np.float64)
        self._damage_hm_acc   = np.zeros((grid_size, grid_size), dtype=np.float64)
        self._env_hm_count: int = 0

        self._episodes: deque[EpisodeRecord] = deque(maxlen=max_episodes)
        self._current_steps: List[StepRecord] = []
        self._episode_num: int = 0
        self._current_total_reward: float = 0.0
        self._current_total_damage: float = 0.0

        self._sb3_metrics: List[Dict[str, Any]] = []

        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Hooks called from GridForest
    # ------------------------------------------------------------------

    def on_step(
        self,
        action: int,
        pos: tuple,
        reward: float,
        reward_components: Dict[str, float],
        events: List[str],
        total_damage: float = 0.0,
    ) -> None:
        step_num = len(self._current_steps)
        record = StepRecord(
            step=step_num,
            action=action,
            pos=pos,
            reward=reward,
            reward_components=dict(reward_components),
            events=list(events),
        )
        self._current_steps.append(record)
        self._current_total_reward += reward
        self._current_total_damage = total_damage

        with self._lock:
            x, y = pos
            if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
                self.heatmap[x, y] += 1
            if 0 <= action < self.N_ACTIONS:
                self.action_counts[action] += 1

    def on_episode_end(
        self,
        terminated: bool,
        truncated: bool,
        episode_metrics: Optional[Dict[str, float]],
        intruders_scheduled: int = 0,
        idleness_map: Optional[np.ndarray] = None,
        idleness_interval_map: Optional[np.ndarray] = None,
        intruder_acc_map: Optional[np.ndarray] = None,
        damage_acc_map: Optional[np.ndarray] = None,
        catch_latency: Optional[List[int]] = None,
    ) -> None:
        intruders_caught = sum(
            1 for sr in self._current_steps if "CatchEvent" in sr.events
        )
        catch_rate = (intruders_caught / intruders_scheduled) if intruders_scheduled > 0 else 0.0

        # Обновляем накопитель карты средних интервалов простоя
        if idleness_interval_map is not None:
            with self._lock:
                self._idleness_acc += idleness_interval_map.astype(np.float64)
                self._idleness_count += 1

        # Обновляем накопители карт нарушителей и урона
        if intruder_acc_map is not None and damage_acc_map is not None:
            with self._lock:
                self._intruder_hm_acc += intruder_acc_map.astype(np.float64)
                self._damage_hm_acc   += damage_acc_map.astype(np.float64)
                self._env_hm_count    += 1

        idleness_percentiles: Optional[Dict[str, float]] = None
        if idleness_map is not None:
            flat = idleness_map.flatten().astype(float)
            idleness_percentiles = {
                "p50": float(np.percentile(flat, 50)),
                "p90": float(np.percentile(flat, 90)),
                "p99": float(np.percentile(flat, 99)),
            }

        latency_mean: Optional[float] = None
        if catch_latency:
            latency_mean = float(np.mean(catch_latency))

        record = EpisodeRecord(
            episode=self._episode_num,
            steps=len(self._current_steps),
            terminated=terminated,
            truncated=truncated,
            total_reward=self._current_total_reward,
            total_damage=self._current_total_damage,
            catch_rate=catch_rate,
            catch_latency_mean=latency_mean,
            step_records=list(self._current_steps),
            metrics=dict(episode_metrics) if episode_metrics else None,
            idleness_percentiles=idleness_percentiles,
        )

        with self._lock:
            self._episodes.append(record)

        self._episode_num += 1
        self._current_steps = []
        self._current_total_reward = 0.0
        self._current_total_damage = 0.0

    # ------------------------------------------------------------------
    # SB3 metrics
    # ------------------------------------------------------------------

    def record_sb3_metrics(self, timestep: int, kv: Dict[str, Any]) -> None:
        entry = {"timestep": timestep}
        entry.update({k: v for k, v in kv.items() if isinstance(v, (int, float))})
        self._sb3_metrics.append(entry)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_heatmap(self) -> np.ndarray:
        with self._lock:
            return self.heatmap.copy()

    def get_action_histogram(self, normalize: bool = True) -> np.ndarray:
        with self._lock:
            counts = self.action_counts.copy()
        if normalize:
            total = counts.sum()
            return counts / total if total > 0 else counts.astype(float)
        return counts

    def get_idleness_heatmap(self) -> np.ndarray:
        """Среднее по эпизодам значение mean-interval простоя для каждой ячейки.
        Высокое значение = ячейка редко попадала в поле зрения агента."""
        with self._lock:
            if self._idleness_count == 0:
                return np.zeros((self.grid_size, self.grid_size), dtype=np.float64)
            return self._idleness_acc / self._idleness_count

    def get_intruder_heatmap(self) -> np.ndarray:
        """Среднее по эпизодам число шагов, когда нарушитель находился в ячейке.
        Высокое значение = ячейка часто посещалась нарушителями."""
        with self._lock:
            if self._env_hm_count == 0:
                return np.zeros((self.grid_size, self.grid_size), dtype=np.float64)
            return self._intruder_hm_acc / self._env_hm_count

    def get_damage_heatmap(self) -> np.ndarray:
        """Среднее по эпизодам суммарное снижение ценности ячейки (урон от нарушителей).
        Высокое значение = ячейка понесла наибольший урон."""
        with self._lock:
            if self._env_hm_count == 0:
                return np.zeros((self.grid_size, self.grid_size), dtype=np.float64)
            return self._damage_hm_acc / self._env_hm_count

    def visit_uniformity(self) -> float:
        """Coefficient of variation of heatmap — lower means more uniform coverage."""
        hm = self.get_heatmap().astype(float)
        mean = hm.mean()
        if mean == 0:
            return 0.0
        return float(hm.std() / mean)

    # ------------------------------------------------------------------
    # Pandas exports
    # ------------------------------------------------------------------

    def episodes_to_df(self) -> pd.DataFrame:
        with self._lock:
            episodes = list(self._episodes)

        if not episodes:
            return pd.DataFrame()

        rows = []
        for ep in episodes:
            row: Dict[str, Any] = {
                "run_id": self.run_id,
                "episode": ep.episode,
                "steps": ep.steps,
                "terminated": ep.terminated,
                "truncated": ep.truncated,
                "total_reward": ep.total_reward,
                "total_damage": ep.total_damage,
                "catch_rate": ep.catch_rate,
                "catch_latency_mean": ep.catch_latency_mean,
            }
            if ep.metrics:
                for k, v in ep.metrics.items():
                    row[f"metric_{k}"] = v
            if ep.idleness_percentiles:
                for k, v in ep.idleness_percentiles.items():
                    row[f"idleness_{k}"] = v
            rows.append(row)

        df = pd.DataFrame(rows)
        if "total_reward" in df.columns:
            df["reward_rolling_50"] = df["total_reward"].rolling(50, min_periods=1).mean()
        return df

    def steps_to_df(self, episode: int) -> pd.DataFrame:
        with self._lock:
            episodes = list(self._episodes)

        target = next((ep for ep in episodes if ep.episode == episode), None)
        if target is None:
            return pd.DataFrame()

        rows = []
        for sr in target.step_records:
            row: Dict[str, Any] = {
                "episode": episode,
                "step": sr.step,
                "action": sr.action,
                "pos_x": sr.pos[0],
                "pos_y": sr.pos[1],
                "reward": sr.reward,
                "events": "|".join(sr.events),
            }
            row.update({f"r_{k}": v for k, v in sr.reward_components.items()})
            rows.append(row)

        return pd.DataFrame(rows)

    def sb3_metrics_to_df(self) -> pd.DataFrame:
        if not self._sb3_metrics:
            return pd.DataFrame()
        df = pd.DataFrame(self._sb3_metrics)
        if self.run_id is not None:
            df.insert(0, "run_id", self.run_id)
        return df

    def all_steps_to_df(self) -> pd.DataFrame:
        """Все шаги всех записанных эпизодов в одном DataFrame.

        Колонки: run_id, episode, step, action, action_name, pos_x, pos_y,
                 reward, reward_cumsum, events, n_events,
                 <reward_components> (r_move, r_catch, r_damage, …).
        """
        with self._lock:
            episodes = list(self._episodes)

        if not episodes:
            return pd.DataFrame()

        rows: List[Dict[str, Any]] = []
        for ep in episodes:
            cumsum = 0.0
            for sr in ep.step_records:
                cumsum += sr.reward
                action_name = (
                    self.ACTION_NAMES[sr.action]
                    if 0 <= sr.action < len(self.ACTION_NAMES)
                    else str(sr.action)
                )
                row: Dict[str, Any] = {
                    "run_id": self.run_id,
                    "episode": ep.episode,
                    "step": sr.step,
                    "action": sr.action,
                    "action_name": action_name,
                    "pos_x": sr.pos[0],
                    "pos_y": sr.pos[1],
                    "reward": sr.reward,
                    "reward_cumsum": round(cumsum, 6),
                    "events": "|".join(sr.events),
                    "n_events": len(sr.events),
                }
                row.update(sr.reward_components)
                rows.append(row)

        return pd.DataFrame(rows)

    def episode_actions_to_df(self) -> pd.DataFrame:
        """Распределение действий по эпизодам.

        Колонки: run_id, episode, steps,
                 n_up/down/left/right/stay (абс. кол-во),
                 p_up/down/left/right/stay (доля).
        Позволяет отследить, как меняется политика агента от эпизода к эпизоду.
        """
        with self._lock:
            episodes = list(self._episodes)

        if not episodes:
            return pd.DataFrame()

        rows: List[Dict[str, Any]] = []
        for ep in episodes:
            counts = [0] * self.N_ACTIONS
            for sr in ep.step_records:
                if 0 <= sr.action < self.N_ACTIONS:
                    counts[sr.action] += 1
            total = sum(counts)
            row: Dict[str, Any] = {
                "run_id": self.run_id,
                "episode": ep.episode,
                "steps": ep.steps,
            }
            for i, name in enumerate(self.ACTION_NAMES):
                key = name.lower()
                row[f"n_{key}"] = counts[i]
                row[f"p_{key}"] = counts[i] / total if total > 0 else 0.0
            rows.append(row)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_full_data(self, path: str) -> None:
        """Сохраняет полный набор данных в path (Parquet + numpy heatmaps).

        Файлы:
            episodes.parquet       — сводка по эпизодам
            all_steps.parquet      — каждый шаг каждого эпизода
            episode_actions.parquet— распределение действий по эпизодам
            sb3_metrics.parquet    — метрики SB3 (только если есть)
            heatmap_visits.npy     — тепловая карта посещений (grid×grid, int64)
            heatmap_idleness.npy   — тепловая карта простоя (grid×grid, float64)
        """
        import os
        os.makedirs(path, exist_ok=True)

        _frames: Dict[str, pd.DataFrame] = {
            "episodes.parquet": self.episodes_to_df(),
            "all_steps.parquet": self.all_steps_to_df(),
            "episode_actions.parquet": self.episode_actions_to_df(),
            "sb3_metrics.parquet": self.sb3_metrics_to_df(),
        }
        for fname, df in _frames.items():
            if not df.empty:
                df.to_parquet(os.path.join(path, fname), index=False)

        np.save(os.path.join(path, "heatmap_visits.npy"), self.get_heatmap())
        np.save(os.path.join(path, "heatmap_idleness.npy"), self.get_idleness_heatmap())
        np.save(os.path.join(path, "heatmap_intruders.npy"), self.get_intruder_heatmap())
        np.save(os.path.join(path, "heatmap_damage.npy"), self.get_damage_heatmap())

        df_ep_csv = self.episodes_to_df()
        if not df_ep_csv.empty:
            df_ep_csv.to_csv(os.path.join(path, "episodes.csv"), index=False)

    def save_parquet(self, path: str) -> None:
        """Краткое сохранение: только episodes + sb3_metrics."""
        import os
        os.makedirs(path, exist_ok=True)
        df_ep = self.episodes_to_df()
        df_sb3 = self.sb3_metrics_to_df()
        if not df_ep.empty:
            df_ep.to_parquet(os.path.join(path, "episodes.parquet"), index=False)
        if not df_sb3.empty:
            df_sb3.to_parquet(os.path.join(path, "sb3_metrics.parquet"), index=False)

    def save_csv(self, path: str) -> None:
        """Краткое сохранение: только episodes + sb3_metrics в CSV."""
        import os
        os.makedirs(path, exist_ok=True)
        df_ep = self.episodes_to_df()
        df_sb3 = self.sb3_metrics_to_df()
        if not df_ep.empty:
            df_ep.to_csv(os.path.join(path, "episodes.csv"), index=False)
        if not df_sb3.empty:
            df_sb3.to_csv(os.path.join(path, "sb3_metrics.csv"), index=False)

    @property
    def episode_count(self) -> int:
        return self._episode_num


class RLLoggerKVWriter(KVWriter):
    """SB3 KVWriter that forwards logged metrics to RLLogger."""

    def __init__(self, rl_logger: RLLogger) -> None:
        self.rl_logger = rl_logger

    def write(
        self,
        key_values: Dict[str, Any],
        key_excluded: Dict[str, Any],
        step: int = 0,
    ) -> None:
        self.rl_logger.record_sb3_metrics(step, key_values)

    def close(self) -> None:
        pass
