from stable_baselines3 import SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor

from forest_env import ForestEnv


env = DummyVecEnv([lambda: Monitor(ForestEnv())])

env = VecNormalize(
    env,
    norm_obs=True,
    norm_reward=True
)

model = SAC(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    buffer_size=300000,
    batch_size=256,
    gamma=0.99,
    tau=0.005,
    train_freq=1,
    gradient_steps=1,
    verbose=1,
    tensorboard_log="./tensorboard/"
)

model.learn(
    total_timesteps=100000,
    log_interval=3,
    progress_bar=True
)

model.save("sac_forest_v1")

env.save("vec_normalize.pkl")

env.close()
