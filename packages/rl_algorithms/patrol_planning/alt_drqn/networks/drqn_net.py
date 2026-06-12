"""DRQN сеть: CNNExtractor5x5 → LSTM → Q-values."""

import torch
import torch.nn as nn
from packages.rl_algorithms.patrol_planning.rppo.networks.cnn_extractor_5x5 import CNNExtractor5x5


class DRQNNet(nn.Module):
    def __init__(
        self,
        observation_space,
        n_actions: int,
        lstm_hidden_size: int = 256,
        features_dim: int = 128,
    ):
        super().__init__()
        self.lstm_hidden_size = lstm_hidden_size

        self.cnn_extractor = CNNExtractor5x5(observation_space, features_dim)

        self.lstm = nn.LSTM(
            input_size=features_dim,
            hidden_size=lstm_hidden_size,
            num_layers=1,
            batch_first=True,
        )

        self.q_head = nn.Linear(lstm_hidden_size, n_actions)

    def forward(self, obs_seq: torch.Tensor, hidden=None):
        """
        Args:
            obs_seq: (batch, time, C, H, W)
            hidden: (h, c) или None
        Returns:
            q_values: (batch, time, n_actions)
            hidden: обновлённый (h, c)
        """
        B, T, C, H, W = obs_seq.shape
        obs_flat = obs_seq.view(B * T, C, H, W)
        features = self.cnn_extractor(obs_flat)
        features = features.view(B, T, -1)

        lstm_out, hidden = self.lstm(features, hidden)
        q_values = self.q_head(lstm_out)
        return q_values, hidden

    def init_hidden(self, batch_size: int, device):
        h = torch.zeros(1, batch_size, self.lstm_hidden_size, device=device)
        c = torch.zeros(1, batch_size, self.lstm_hidden_size, device=device)
        return (h, c)
