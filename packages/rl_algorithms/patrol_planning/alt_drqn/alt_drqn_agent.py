import copy
import queue
import threading

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from gymnasium import spaces

from packages.rl_algorithms.patrol_planning.alt_drqn.networks.drqn_net import DRQNNet
from packages.rl_algorithms.patrol_planning.alt_drqn.replay_buffer import EpisodeReplayBuffer


class AltDRQNAgent:
    def __init__(
        self,
        observation_space: spaces.Box,
        n_actions: int,
        n_envs: int = 2,
        lr: float = 1e-4,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_final: float = 0.05,
        epsilon_decay_steps: int = 50_000,
        buffer_capacity: int = 1000,
        unroll_length: int = 10,
        batch_size: int = 32,
        target_update_freq: int = 1000,
        learning_starts: int = 500,
        lstm_hidden_size: int = 256,
        features_dim: int = 128,
        device: str = "cuda",
        use_amp: bool = True,
        normalize_rewards: bool = False,
        burn_in: int = 0,
    ):
        self.n_envs = n_envs
        self.n_actions = n_actions
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.learning_starts = learning_starts
        self.unroll_length = unroll_length
        self.burn_in = burn_in
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.use_amp = use_amp and self.device.type == "cuda"
        self.normalize_rewards = normalize_rewards

        self.epsilon = epsilon_start
        self.epsilon_final = epsilon_final
        self.epsilon_decay = (epsilon_start - epsilon_final) / epsilon_decay_steps
        self._step = 0

        self.net = DRQNNet(
            observation_space, n_actions, lstm_hidden_size, features_dim
        ).to(self.device)
        self.target_net = copy.deepcopy(self.net).to(self.device)
        self.target_net.eval()

        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        self.loss_fn = nn.SmoothL1Loss(reduction="none")

        if self.use_amp:
            self.scaler = torch.cuda.amp.GradScaler()

        self.buffer = EpisodeReplayBuffer(buffer_capacity, unroll_length, n_envs=n_envs)

        self._hiddens: list[tuple] = [
            self.net.init_hidden(1, self.device) for _ in range(n_envs)
        ]

        self._buf_lock = threading.Lock()

        self._update_queue: queue.Queue = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._update_thread: threading.Thread | None = None

        self._last_loss: float = 0.0
        self.n_updates: int = 0

    def reset_hidden(self, env_id: int) -> None:
        self._hiddens[env_id] = self.net.init_hidden(1, self.device)

    def reset_all_hiddens(self) -> None:
        for i in range(self.n_envs):
            self.reset_hidden(i)

    @torch.no_grad()
    def select_action_batch(
        self,
        obs_batch: np.ndarray,
        env_ids: list[int],
    ) -> list[int]:
        N = len(env_ids)

        obs_t = torch.from_numpy(np.ascontiguousarray(obs_batch)).to(
            dtype=torch.float32, device=self.device, non_blocking=True
        ).unsqueeze(1)

        h = torch.cat([self._hiddens[i][0] for i in env_ids], dim=1)
        c = torch.cat([self._hiddens[i][1] for i in env_ids], dim=1)

        q_values, new_hidden = self.net(obs_t, (h, c))

        for k, env_id in enumerate(env_ids):
            self._hiddens[env_id] = (
                new_hidden[0][:, k : k + 1, :],
                new_hidden[1][:, k : k + 1, :],
            )

        q_vals = q_values[:, 0, :]
        actions = []
        for k in range(N):
            if np.random.random() < self.epsilon:
                actions.append(np.random.randint(self.n_actions))
            else:
                actions.append(int(q_vals[k].argmax().item()))

        return actions

    def add_transition(
        self, env_id: int, obs, action: int, reward: float, next_obs, done: bool
    ) -> None:
        if self.normalize_rewards:
            reward = float(np.sign(reward) * np.log1p(abs(reward)))
        with self._buf_lock:
            self.buffer.add(obs, action, reward, next_obs, done, env_id=env_id)
        self._step += 1
        self.epsilon = max(self.epsilon_final, self.epsilon - self.epsilon_decay)

    def can_learn(self) -> bool:
        return self._step >= self.learning_starts and self.buffer.can_sample(self.batch_size)

    def update(self) -> float:
        with self._buf_lock:
            if not self.buffer.can_sample(self.batch_size):
                return 0.0
            episodes_snapshot = list(self.buffer.episodes)
        batch = self.buffer.sample_from(episodes_snapshot, self.batch_size, self.device, burn_in=self.burn_in)

        obs      = batch["obs"]
        actions  = batch["actions"]
        rewards  = batch["rewards"]
        next_obs = batch["next_obs"]
        dones    = batch["dones"]
        masks    = batch["masks"]

        B = obs.shape[0]
        K = self.burn_in
        hidden        = self.net.init_hidden(B, self.device)
        target_hidden = self.target_net.init_hidden(B, self.device)

        if K > 0:
            with torch.no_grad():
                _, hidden        = self.net(obs[:, :K].contiguous(),      hidden)
                _, target_hidden = self.target_net(obs[:, :K].contiguous(), target_hidden)
            hidden        = (hidden[0].detach(),        hidden[1].detach())
            target_hidden = (target_hidden[0].detach(), target_hidden[1].detach())

        obs_tr      = obs[:, K:].contiguous()
        actions_tr  = actions[:, K:].contiguous()
        rewards_tr  = rewards[:, K:].contiguous()
        next_obs_tr = next_obs[:, K:].contiguous()
        dones_tr    = dones[:, K:].contiguous()
        masks_tr    = masks[:, K:].contiguous()

        if self.use_amp:
            with torch.cuda.amp.autocast():
                q_all, _ = self.net(obs_tr, hidden)
                q_taken  = q_all.gather(2, actions_tr.unsqueeze(-1)).squeeze(-1)
                with torch.no_grad():
                    q_next, _ = self.target_net(next_obs_tr, target_hidden)
                    q_next_max = q_next.max(dim=2).values
                    targets = rewards_tr + self.gamma * q_next_max * (1.0 - dones_tr)
                loss_per_step = self.loss_fn(q_taken, targets)
                loss = (loss_per_step * masks_tr).sum() / masks_tr.sum()

            self.optimizer.zero_grad()
            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            nn.utils.clip_grad_norm_(self.net.parameters(), max_norm=10.0)
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            q_all, _ = self.net(obs_tr, hidden)
            q_taken  = q_all.gather(2, actions_tr.unsqueeze(-1)).squeeze(-1)
            with torch.no_grad():
                q_next, _ = self.target_net(next_obs_tr, target_hidden)
                q_next_max = q_next.max(dim=2).values
                targets = rewards_tr + self.gamma * q_next_max * (1.0 - dones_tr)
            loss_per_step = self.loss_fn(q_taken, targets)
            loss = (loss_per_step * masks_tr).sum() / masks_tr.sum()

            self.optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(self.net.parameters(), max_norm=10.0)
            self.optimizer.step()

        if self._step % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.net.state_dict())

        return loss

    def _update_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._update_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if self.can_learn():
                loss = self.update()
                self._last_loss = loss.item() if hasattr(loss, "item") else float(loss)
                self.n_updates += 1

    def start_update_thread(self) -> None:
        self._stop_event.clear()
        self._update_thread = threading.Thread(
            target=self._update_worker, daemon=True, name="drqn-updater"
        )
        self._update_thread.start()

    def stop_update_thread(self) -> None:
        self._stop_event.set()
        if self._update_thread is not None:
            self._update_thread.join(timeout=5.0)
            self._update_thread = None
