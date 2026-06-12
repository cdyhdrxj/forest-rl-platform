import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class CNNExtractor5x5(BaseFeaturesExtractor):
    """CNN feature extractor для POMDP наблюдений формы (C, H, W).

    Архитектура:
        Conv2d(C→32, 3×3, pad=1) → ReLU
        Conv2d(32→64, 3×3, pad=1) → ReLU
        Flatten → Linear(64·H·W → features_dim) → ReLU

    С padding=1 и kernel=3 пространственные размеры сохраняются на каждом conv,
    поэтому размер flat слоя = 64 * H * W (для 5×5 → 1600).
    """

    def __init__(self, observation_space, features_dim: int = 128):
        super().__init__(observation_space, features_dim)

        n_ch = observation_space.shape[0]
        h, w = observation_space.shape[1], observation_space.shape[2]

        self.cnn = nn.Sequential(
            nn.Conv2d(n_ch, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        self.linear = nn.Sequential(
            nn.Linear(64 * h * w, features_dim),
            nn.ReLU(),
        )

    def forward(self, observations):
        return self.linear(self.cnn(observations))
