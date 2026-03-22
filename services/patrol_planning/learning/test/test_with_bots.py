"""Агент vs Бот"""

import sys
import os, json

# Абсолютный путь до корня проекта (где лежит environment, observations и т.д.)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Добавляем в sys.path, если ещё нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.patrol_planning.assets.envs.environment import GridWorld

from services.patrol_planning.src.renderer_extended import GridWorldRendererExt

from services.patrol_planning.assets.envs.models import GridWorldConfig
#Загружаем конфиг среды
with open("services/patrol_planning/learning/configs/GW_DEFAULT.json", "r", encoding="utf-8") as f:
    data = json.load(f)

config = GridWorldConfig.model_validate(data)

env = GridWorld.load(config)


from stable_baselines3 import PPO



#Сброс среды 
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
