"""
Episode-based Replay Buffer для alt_drqn (multi-env).

Отличие от оригинала: поддержка n_envs — каждая среда ведёт свой
аккумулятор текущего эпизода. Общая очередь episodes остаётся одна.

Bootstrapped Random Updates: сэмплируем случайные отрезки длиной
unroll_length из случайных эпизодов — как в Hausknecht & Stone 2015.

Оптимизации (из оригинала):
  - эпизоды хранятся как dict предстекованных numpy-массивов
  - срез ep["obs"][start:start+T] — numpy view без копирования
  - torch.from_numpy + non_blocking=True — без лишней копии при GPU-трансфере
"""

import numpy as np
import torch
from collections import deque


class EpisodeReplayBuffer:
    def __init__(self, capacity: int, unroll_length: int, n_envs: int = 1):
        self.capacity = capacity
        self.unroll_length = unroll_length
        self.n_envs = n_envs
        self.episodes: deque = deque(maxlen=capacity)

        self._cur_obs:      list[list] = [[] for _ in range(n_envs)]
        self._cur_actions:  list[list] = [[] for _ in range(n_envs)]
        self._cur_rewards:  list[list] = [[] for _ in range(n_envs)]
        self._cur_next_obs: list[list] = [[] for _ in range(n_envs)]
        self._cur_dones:    list[list] = [[] for _ in range(n_envs)]

    def add(self, obs, action: int, reward: float, next_obs, done: bool, env_id: int = 0) -> None:
        self._cur_obs[env_id].append(np.asarray(obs, dtype=np.float32))
        self._cur_actions[env_id].append(action)
        self._cur_rewards[env_id].append(reward)
        self._cur_next_obs[env_id].append(np.asarray(next_obs, dtype=np.float32))
        self._cur_dones[env_id].append(done)
        if done:
            self._commit_episode(env_id)

    def _commit_episode(self, env_id: int = 0) -> None:
        self.episodes.append({
            "obs":      np.stack(self._cur_obs[env_id]),
            "actions":  np.array(self._cur_actions[env_id],  dtype=np.int64),
            "rewards":  np.array(self._cur_rewards[env_id],  dtype=np.float32),
            "next_obs": np.stack(self._cur_next_obs[env_id]),
            "dones":    np.array(self._cur_dones[env_id],    dtype=np.float32),
        })
        self._cur_obs[env_id].clear()
        self._cur_actions[env_id].clear()
        self._cur_rewards[env_id].clear()
        self._cur_next_obs[env_id].clear()
        self._cur_dones[env_id].clear()

    def flush_episode(self, env_id: int | None = None) -> None:
        """Принудительно сохранить незавершённые эпизоды (конец обучения).

        env_id=None → flush для всех сред.
        """
        if env_id is None:
            for i in range(self.n_envs):
                if self._cur_obs[i]:
                    self._commit_episode(i)
        else:
            if self._cur_obs[env_id]:
                self._commit_episode(env_id)

    def can_sample(self, batch_size: int) -> bool:
        return len(self.episodes) >= batch_size

    def sample(self, batch_size: int, device, burn_in: int = 0) -> dict:
        return self.sample_from(list(self.episodes), batch_size, device, burn_in)

    def sample_from(self, episodes: list, batch_size: int, device, burn_in: int = 0) -> dict:
        """Сэмплировать batch_size отрезков из переданного снапшота эпизодов (без лока)."""
        n = len(episodes)
        T = self.unroll_length
        K = burn_in
        total_len = K + T
        idxs = np.random.randint(0, n, size=batch_size)

        obs_list, act_list, rew_list, nobs_list, done_list, mask_list = \
            [], [], [], [], [], []

        for idx in idxs:
            ep = episodes[idx]
            ep_len = ep["obs"].shape[0]
            obs_shape = ep["obs"].shape[1:]

            if ep_len >= total_len:
                start = np.random.randint(0, ep_len - total_len + 1)
                obs_list.append(ep["obs"][start: start + total_len])
                act_list.append(ep["actions"][start: start + total_len])
                rew_list.append(ep["rewards"][start: start + total_len])
                nobs_list.append(ep["next_obs"][start: start + total_len])
                done_list.append(ep["dones"][start: start + total_len])
                mask_list.append(np.array([0.0] * K + [1.0] * T, dtype=np.float32))
            else:
                pad = total_len - ep_len
                train_valid = max(0, ep_len - K)
                train_pad   = T - train_valid

                obs_list.append(np.concatenate([
                    ep["obs"],
                    np.zeros((pad, *obs_shape), dtype=np.float32)
                ]))
                act_list.append(np.concatenate([ep["actions"],  np.zeros(pad, dtype=np.int64)]))
                rew_list.append(np.concatenate([ep["rewards"],  np.zeros(pad, dtype=np.float32)]))
                nobs_list.append(np.concatenate([
                    ep["next_obs"],
                    np.zeros((pad, *obs_shape), dtype=np.float32)
                ]))
                done_list.append(np.concatenate([ep["dones"], np.ones(pad, dtype=np.float32)]))
                mask_list.append(np.array(
                    [0.0] * K + [1.0] * train_valid + [0.0] * train_pad,
                    dtype=np.float32
                ))

        def to_tensor(lst, dtype=torch.float32):
            arr = np.stack(lst)
            return torch.from_numpy(arr).to(dtype=dtype, device=device, non_blocking=True)

        return {
            "obs":      to_tensor(obs_list),
            "actions":  to_tensor(act_list, torch.int64),
            "rewards":  to_tensor(rew_list),
            "next_obs": to_tensor(nobs_list),
            "dones":    to_tensor(done_list),
            "masks":    to_tensor(mask_list),
        }

    def __len__(self) -> int:
        return len(self.episodes)
