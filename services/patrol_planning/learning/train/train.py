import sys
import os
import json

# Абсолютный путь до корня проекта (где лежит environment, observations и т.д.)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Добавляем в sys.path, если ещё нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from services.patrol_planning.assets.envs.environment import GridWorld
from services.patrol_planning.src.renderer_extended import GridWorldRendererExt

from services.patrol_planning.service.models import GridWorldTrainState
from services.patrol_planning.assets.envs.models import GridWorldConfig

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

# from services.patrol_planning.assets.envs.models import GW_DEFAULT
# with open("services/patrol_planning/learning/configs/GW_DEFAULT.json", "w", encoding="utf-8") as f:
#     f.write(GW_DEFAULT.model_dump_json(indent=2))

#Загружаем конфиг среды
with open("services/patrol_planning/learning/configs/GW_DEFAULT.json", "r", encoding="utf-8") as f:
    data = json.load(f)

config = GridWorldConfig.model_validate(data)


env = GridWorld.load(config)
# Рендер движок
renderer = GridWorldRendererExt(env)

#Для регистрации состояния
st = GridWorldTrainState()
env.train_state = st
# Для визуализации обучения - расскомментировать
env.renderer = renderer
env.render_time_sleep = 1.0


# Проверка reset
obs, _ = env.reset()

# Векторизация для SB3
vec_env = make_vec_env(lambda: env, n_envs=1)

model = PPO(
    policy="MlpPolicy",  
    env=vec_env,
    verbose=1
)

# Обучение
with renderer.live:  # чтобы видеть в реальном времени
    model.learn(total_timesteps=10000)
    
#Сохранение модели
model.save("services/patrol_planning/learning/models/ppo_gridworld_agent_1")
