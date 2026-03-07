import numpy as np
from environment import STEPS, OBSTACLE

class Trainer:
    def __init__(self, agent_class, agent_params, max_episodes, max_steps):
        self.agent_class = agent_class
        self.agent_params = agent_params
        self.max_episodes = max_episodes
        self.max_steps = max_steps
        self.agent = agent_class(**agent_params)

    def train(self, env_params):
        self.agent.learn(env_params, self.max_episodes, self.max_steps)
        return self.agent.Q

    def run(self, env, max_steps):
        history = []
        state = env.get_state()
        cnt_collision = 0
        finished = False

        for _ in range(max_steps):
            if env.is_terminal(state):
                finished = True
                break

            qs = [self.agent.Q.get((state, a), 0) for a in range(4)]
            action = int(np.argmax(qs))

            # Проверяем, если ли препятствие в целевой клетке
            i, j = env.agent_position
            di, dj = STEPS[action]
            ni, nj = i + di, j + dj
            if not (0 <= ni < env.n and 0 <= nj < env.m) or env.grid[ni][nj] == OBSTACLE:
                cnt_collision += 1

            next_state, reward = env.step(action)
            history.append((state, env.agent_position, action, reward))
            state = next_state

        if env.agent_position == env.finish:
            finished = True

        return history, finished, cnt_collision
