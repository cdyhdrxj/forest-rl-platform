import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from environment import EnvParams, STEPS, OBSTACLE

class DQNNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(7, 32),  # состояние - 7 чисел
            nn.ReLU(),
            nn.Linear(32, 4)   # 4 действия
        )

    def forward(self, x):
        return self.net(x)


class DQN:
    def __init__(self, lr=0.01, gamma=0.9, epsilon=1.0):
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.model = DQNNet()
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

    def state_to_tensor(self, state):
        return torch.tensor(state, dtype=torch.float32).unsqueeze(0)

    def choose_action(self, state):
        if np.random.rand() < self.epsilon:
            return np.random.randint(0, 4)
        with torch.no_grad():
            q = self.model(self.state_to_tensor(state))
        return int(torch.argmax(q).item())

    def learn(self, env_params: EnvParams, max_episodes=500, max_steps=200):
        for ep in range(max_episodes):
            env = env_params.sample_env()
            state = env.get_state()
            for _ in range(max_steps):
                action = self.choose_action(state)
                next_state, reward = env.step(action)
                done = env.is_terminal(next_state)

                state_tensor = self.state_to_tensor(state)
                q_values = self.model(state_tensor)
                target = q_values.clone().detach()
                next_q = self.model(self.state_to_tensor(next_state))
                target[0, action] = reward + self.gamma * torch.max(next_q) * (0 if done else 1)

                loss = self.loss_fn(q_values, target)
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

                state = next_state
                if done:
                    break

            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

class DqnTrainer:
    def __init__(self, agent_class, agent_params, max_episodes, max_steps):
        self.agent = agent_class(**agent_params)
        self.max_episodes = max_episodes
        self.max_steps = max_steps

    # Обучение агента на случайных средах
    def train(self, env_params):
        self.agent.learn(env_params, self.max_episodes, self.max_steps)
        return self.agent

    # Запуск агента на конкретной среде
    def run(self, env, max_steps):
        history = []
        state = env.get_state()
        finished = False
        cnt_collisions = 0

        for _ in range(max_steps):
            action = self.agent.choose_action(state)

            i, j = env.agent_position
            di, dj = STEPS[action]
            ni, nj = i + di, j + dj

            if not (0 <= ni < env.n and 0 <= nj < env.m) or env.grid[ni][nj] == OBSTACLE:
                cnt_collisions += 1

            next_state, reward = env.step(action)
            history.append((state, env.agent_position, action, reward))
            state = next_state

            if env.is_terminal(state):
                finished = True
                break

        return history, finished, cnt_collisions