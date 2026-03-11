from stable_baselines3 import SAC
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from forest_env import ForestEnv
from stable_baselines3.common.monitor import Monitor


env = DummyVecEnv([lambda: Monitor(ForestEnv())])
env = VecNormalize.load("vec_normalize.pkl", env)
env.training = True
env.norm_reward = True

model = SAC.load("sac_forest_v1", env=env)

model.learn(
    total_timesteps=20_000,
    log_interval=3,
    progress_bar=True
)

model.save("sac_forest_v2")
env.save("vec_normalize.pkl")

env.close()
