"""Агент vs Человек"""

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
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.assets.intruders.controllable import Controllable
from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.src.renderer_extended import GridWorldRendererExt
from services.patrol_planning.src.pp_types import InputActions

from stable_baselines3 import PPO

import keyboard
import time
import threading

from services.patrol_planning.assets.envs.models import GridWorldConfig
#Загружаем конфиг средыaasasaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaawaawaa
with open("services/patrol_planning/learning/configs/GW_DEFAULT.json", "r", encoding="utf-8") as f:
    data = json.load(f)

config = GridWorldConfig.model_validate(data)

env = GridWorld.load(config)

#Сброс среды
obs, _ = env.reset()

#Рендер движок
renderer = GridWorldRendererExt(env)
env.renderer = renderer

#Задержку делаем в другом месте
env.render_time_sleep = 0.0

max_steps = 500  # количество шагов для просмотра


model = PPO.load("services/patrol_planning/learning/models/simple_pursuer")

next_input = InputActions.STAY
stop_thread = False

def input_listener():
    global next_input, stop_thread
    while not stop_thread:
        if keyboard.is_pressed("w"):
            next_input = InputActions.UP
        elif keyboard.is_pressed("s"):
            next_input = InputActions.DOWN
        elif keyboard.is_pressed("a"):
            next_input = InputActions.LEFT
        elif keyboard.is_pressed("d"):
            next_input = InputActions.RIGHT
        elif keyboard.is_pressed("esc"):
            stop_thread = True
        time.sleep(0.01)  # задержка обработки

# запускаем поток ввода
listener_thread = threading.Thread(target=input_listener, daemon=True)
listener_thread.start()

with renderer.live:
    while not stop_thread:
        #Действие агента
        action, _states = model.predict(obs, deterministic=True)

        #Используем последнее введённое игроком
        intruder = env.intruders[0] #Считаем что игрок всегда в начале списка
        intruder.input_action = next_input

        #Шаг среды
        obs, reward, terminated, _, _ = env.step(action)

        if terminated:
            print("Агент поймал нарушителя")
            break
        
        #Сбрасываем ввод чтобы не было залипания
        next_input = InputActions.STAY
        time.sleep(0.5)

# Завершаем поток
stop_thread = True
listener_thread.join()