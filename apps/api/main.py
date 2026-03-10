from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import math
import threading
import orjson
import random
import time
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from camar_wrapper import CamarGymWrapper

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints для вебсокета (пока единая реализация)
@app.websocket("/threed/patrol")
@app.websocket("/threed/trail")
@app.websocket("/continuous/patrol")
@app.websocket("/continuous/trail")
@app.websocket("/discrete/patrol")
@app.websocket("/discrete/trail")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Отправка состояния клиенту
    async def send_loop():
        while True:
            try:
                await websocket.send_text(
                    orjson.dumps(clean(training_state)).decode()
                )
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f"Send error: {e}")
                break

    send_task = asyncio.create_task(send_loop())

    # start / stop / reset
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "start":
                print("Starting training...")
                handle_start(data.get("params", {}))
            elif action == "stop":
                print("Stopping training...")
                handle_stop()
            elif action == "reset":
                print("Resetting environment...")
                handle_reset()
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        send_task.cancel()
        if training_state["running"]:
            handle_stop()


training_state = {
    "running": False,
    "episode": 0,
    "step": 0,
    "total_reward": 0.0,
    "new_episode": False,
    "last_episode_reward": 0.0,
    "agent_pos": [],
    "goal_pos": [],
    "landmark_pos": [],
    "is_collision": False,
    "goal_count": 0,
    "collision_count": 0,
    "trajectory": [],
    "terrain_map": None,
}

TRAJECTORY_MAX_LEN = 200

env = None
model = None

# Очистка nan/inf
def clean(obj):
    if isinstance(obj, float):
        return 0.0 if not math.isfinite(obj) else obj
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    return obj

# Сброс счётчиков и буферов между запусками
def reset_training_counters():
    training_state["episode"] = 0
    training_state["step"] = 0
    training_state["total_reward"] = 0.0
    training_state["new_episode"] = False
    training_state["last_episode_reward"] = 0.0
    training_state["goal_count"] = 0
    training_state["collision_count"] = 0
    training_state["trajectory"] = []
    training_state["terrain_map"] = None

class VisCallback(BaseCallback):
    """Запись в training_state параметров среды"""
    def __init__(self):
        super().__init__()
        self.episode_reward = 0.0
        self.sent_terrain = False

    def _on_step(self) -> bool:
        if not training_state["running"]:
            return False

        # Задержка скорости обучения
        time.sleep(0.01)

        # Получение состояния среды
        render = self.training_env.env_method("get_render_state")[0]

        # Берем информацию о событиях
        infos = self.locals["infos"][0]
        on_goal = infos.get("on_goal", False)
        is_collision = infos.get("is_collision", False)

        # Обновление счётчиков событий
        if is_collision:
            training_state["collision_count"] += 1
        if on_goal:
            training_state["goal_count"] += 1

        # Обновление позиций для отрисовки
        training_state["agent_pos"] = render.get("agent_pos", [])
        training_state["goal_pos"] = render.get("goal_pos", [])
        training_state["landmark_pos"] = render.get("landmark_pos", [])
        training_state["is_collision"] = is_collision

        # Запись точки траектории
        if render.get("agent_pos"):
            training_state["trajectory"].append(render["agent_pos"][0])
        # Накопление награды за эпизод
        reward = self.locals["rewards"][0]
        self.episode_reward += float(reward)
        training_state["step"] += 1
        training_state["total_reward"] = self.episode_reward
        training_state["new_episode"] = False

        # Отправка карты рельефа
        if not self.sent_terrain:
            terrain = self.training_env.env_method("get_terrain_map")[0]
            if terrain is not None:
                training_state["terrain_map"] = terrain
                self.sent_terrain = True

        # Обработка конца эпизода
        done = self.locals["dones"][0]
        if done:
            training_state["episode"] += 1
            training_state["new_episode"] = True
            training_state["last_episode_reward"] = self.episode_reward
            self.episode_reward = 0.0
            training_state["trajectory"] = []

        return True

def training_loop():
    callback = VisCallback()
    model.learn(
        total_timesteps=10_000_000,
        callback=callback,
        reset_num_timesteps=True
    )

def handle_start(params):
    """Создание среды и модели алгоритма, запуск обучения"""
    global model, env
    if training_state["running"]:
        return

    new_seed = random.randint(0, 100000)
    env = CamarGymWrapper(
        seed=new_seed,
        obstacle_density=params.get("obstacle_density", 0.2),
        action_scale=params.get("action_scale", 1.0),
        goal_reward=params.get("goal_reward", 1.0),
        collision_penalty=params.get("collision_penalty", 0.3),
        grid_size=params.get("grid_size", 10),
        max_steps=params.get("max_steps", 200),
        frameskip=params.get("frameskip", 5),
        max_speed=params.get("max_speed", 50.0),
        accel=params.get("accel", 40.0),
        damping=params.get("damping", 0.6),
        dt=params.get("dt", 0.01),
        terrain_penalty=params.get("terrain_penalty", 0.3),
    )
    model = PPO(
        "MlpPolicy", env,
        verbose=1,
        learning_rate=params.get("lr", 0.0003),
        gamma=params.get("gamma", 0.99),
        n_steps=1024
    )

    training_state["running"] = True
    reset_training_counters()
    training_state["terrain_map"] = env.terrain_map

    t = threading.Thread(target=training_loop, daemon=True)
    t.start()

def handle_stop():
    """Остановка обучения и сохранение модели"""
    training_state["running"] = False
    if model:
        model.save("ppo_camar")

def handle_reset():
    """Сброс среды и модели к изначальным параметрам"""
    global env, model
    training_state["running"] = False
    if model:
        model.save("ppo_camar")

    new_seed = random.randint(0, 100000)
    env = CamarGymWrapper(
        seed=new_seed,
        obstacle_density=0.2,
        action_scale=1.0,
        goal_reward=1.0,
        collision_penalty=0.3
    )
    model = PPO("MlpPolicy", env, verbose=1)

    reset_training_counters()