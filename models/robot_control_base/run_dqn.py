from environment import EnvParams
from dqn import DQN, DqnTrainer

env_params = EnvParams(
    n_range=(5, 8),
    m_range=(5, 8),
    p_walk_range=(0.2, 0.5),
    p_obstacle_range=(0.1, 0.3),
    mud_range=(1, 3),
    step_reward=-1,
    finish_reward=50,
    seed=13
)

trainer = DqnTrainer(
    agent_class=DQN,
    agent_params=dict(
        lr=0.001,
        gamma=0.95,
        epsilon=1.0
    ),
    max_episodes=10000,
    max_steps=200
)

print("training...")

agent = trainer.train(env_params)

print("training finished")

env = env_params.sample_env()

history, finished, collisions = trainer.run(env, 200)

print("finished:", finished)
print("collisions:", collisions)
print("steps:", len(history))