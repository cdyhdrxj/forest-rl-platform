import sys
import os

# Абсолютный путь до корня проекта (где лежит environment, observations и т.д.)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Добавляем в sys.path, если ещё нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from services.patrol_planning.assets.envs.environment import GridWorld
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.assets.intruders.wanderer import Wanderer
from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.src.renderer_simple import GridWorldRenderer
from services.patrol_planning.src.renderer_extended import GridWorldRendererExt

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env




# =============================
# Настройка среды
# =============================

# Агент
agent = GridWorldAgent(4, 4, False)

# Нарушитель
intruder = Wanderer(0, 0, True)

# Модель наблюдения
obs_m = ObservationBox(4)

# Среда
env = GridWorld(
    agent=agent,
    obs_model=obs_m,
    grid_world_size=8,
    intruders=[intruder],
    max_steps= 150
)

# Рендер движок
renderer = GridWorldRendererExt(env)
# Для визуализации обучения - расскомментировать
# env.renderer = renderer
# env.render_time_sleep = 0.4

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
