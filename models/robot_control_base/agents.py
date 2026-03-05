import numpy as np
from environment import Environment, EnvParams

class QLearning:
    def __init__(self, alpha, epsilon, gamma):
        self.alpha = alpha
        self.epsilon = epsilon
        self.gamma = gamma
        # Аргумент Q-функции: (state, action)
        self.Q = dict()

    # Возвращает текущее значение Q-функции для состояния state и действия action
    # Для терминального состояния - 0
    # Для неинициализированного состояния - 0
    def _get_q_value(self, state, action):
        if Environment.is_terminal(state):
            return 0
        return self.Q.get((state, action), 0)

    # Возвращает максимум Q-функции по всем действиям из состояния state
    def _best_action_value(self, state):
        if Environment.is_terminal(state):
            return 0
        return max(self._get_q_value(state, a) for a in range(4))

    # Выбор действия в состоянии state
    def _choose_action(self, state):
        # С вероятностью epsilon - равновероятно случайное действие
        if np.random.uniform() < self.epsilon:
            return np.random.randint(0, 4)
        # Иначе - аргмаксимум Q-функции по всем действиям из состояния state
        qs = [self._get_q_value(state, a) for a in range(4)]
        return int(np.argmax(qs))

    def learn(self, env_params: EnvParams, max_episodes, max_steps):
        for _ in range(max_episodes):
            env = env_params.sample_env()
            state = env.get_state()

            self.epsilon = max(0.01, self.epsilon * 0.999)

            for _ in range(max_steps):
                if env.is_terminal(state):
                    break

                action = self._choose_action(state)
                next_state, reward = env.step(action)

                old_q = self._get_q_value(state, action)
                target = reward + self.gamma * self._best_action_value(next_state)

                self.Q[(state, action)] = old_q + self.alpha * (target - old_q)
                state = next_state
  

class Sarsa:
    def __init__(self, alpha, epsilon, gamma):
        self.alpha = alpha
        self.epsilon = epsilon
        self.gamma = gamma
        # Аргумент Q-функции: (state, action)
        self.Q = dict()

    # Возвращает текущее значение Q-функции для состояния state и действия action
    # Для терминального состояния - 0
    # Для неинициализированного состояния - 0
    def _get_q_value(self, state, action):
        if Environment.is_terminal(state):
            return 0
        return self.Q.get((state, action), 0)

    # Выбор действия в состоянии state
    def _choose_action(self, state):
        # С вероятностью epsilon - равновероятно случайное действие
        if np.random.uniform() < self.epsilon:
            return np.random.randint(0, 4)
        # Иначе - аргмаксимум Q-функции по всем действиям из состояния state
        qs = [self._get_q_value(state, a) for a in range(4)]
        return int(np.argmax(qs))

    def learn(self, env_params: EnvParams, max_episodes, max_steps):
        for _ in range(max_episodes):
            env = env_params.sample_env()
            state = env.get_state()
            action = self._choose_action(state)

            self.epsilon = max(0.01, self.epsilon * 0.999)

            for _ in range(max_steps):
                if env.is_terminal(state):
                    break

                next_state, reward = env.step(action)
                next_action = self._choose_action(next_state)

                old_q = self._get_q_value(state, action)
                target = reward + self.gamma *  self._get_q_value(next_state, next_action)

                self.Q[(state, action)] = old_q + self.alpha * (target - old_q)
                state = next_state
                action = next_action
