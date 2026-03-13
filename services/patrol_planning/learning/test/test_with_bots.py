"""Агент vs Бот"""

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
from services.patrol_planning.src.pp_types import InputActions

from stable_baselines3 import PPO

import keyboard
import time



#Агент
agent = GridWorldAgent(4,4)

#Нарушители
intruder = Wanderer(0, 0, True)
intruder_1 = Wanderer(6, 6, True)
intruder_2 = Wanderer(0, 7, True)

#Модель наблюдения
obs_m = ObservationBox(4)

#Модель среды
env = GridWorld(
    agent=agent,
    obs_model=obs_m,
    grid_world_size=8,
    intruders=[intruder,intruder_1, intruder_2],
    max_steps= 150
)

#Данные
obs, _ = env.reset()

#Рендер движок
renderer = GridWorldRendererExt(env)
env.renderer = renderer
env.render_time_sleep = 0.5


#Случайное управление
# with renderer.live:  # открываем live-сессию
#     for step in range(50):
#         #Выбираем действие
#         action = env.action_space.sample()
        
#         # делаем шаг среды
#         obs, reward, done, trunc, info = env.step(action)


##Обученное  + боты
model = PPO.load("services/patrol_planning/learning/models/ppo_gridworld_agent_1")

with renderer.live:
    while True:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, _, _ = env.step(action)  # можно игнорировать done/trunc
        
        if terminated:
            print("Агент поймал всех нарушителей")
            break
