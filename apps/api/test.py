import sys
import os
import numpy as np
import time

# Добавляем корневую папку проекта в путь поиска
project_root = r"F:\unity_docker_proj\forest-rl-platform"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from services.trail_robot.wrapper import TrailRobotGymWrapper
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

print("\n" + "="*80)
print("🚀 ОБУЧЕНИЕ РОБОТА С ПРАВИЛЬНЫМИ ШАГАМИ")
print("="*80)

# ============================================
# 1. СОЗДАНИЕ СРЕДЫ
# ============================================
print("\n🔄 Создание среды...")

def make_env():
    """Функция создания среды для VecEnv"""
    env = TrailRobotGymWrapper(
        ros_url="ws://localhost:9090",
        max_steps=500,                    # максимум шагов в эпизоде
        goal_reward=20.0,                  # награда за цель
        collision_penalty=10.0,             # штраф за столкновение
        step_penalty=0.01,                  # штраф за шаг
        goal_distance_threshold=0.5         # радиус цели
    )
    return Monitor(env)  # оборачиваем для мониторинга

# Создаем векторизованную среду (нужно для SB3)
env = DummyVecEnv([make_env])

# ============================================
# 2. НАСТРОЙКА ОБУЧЕНИЯ
# ============================================
print("\n🤖 НАСТРОЙКА МОДЕЛИ PPO")

model = PPO(
    "MlpPolicy",
    env,
    verbose=1,                           # вывод прогресса
    learning_rate=0.0003,                  # скорость обучения
    n_steps=2048,                          # шагов на обновление
    batch_size=64,                         # размер батча
    gamma=0.99,                            # дисконт фактор
    gae_lambda=0.95,                       # параметр GAE
    clip_range=0.2,                         # клиппинг
    ent_coef=0.01,                          # энтропия (исследование)
)

print("✅ Модель создана")

# ============================================
# 3. КАЛБЭК ДЛЯ МОНИТОРИНГА
# ============================================
class TrainingMonitor(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.current_reward = 0
        self.current_length = 0
        self.best_reward = -float('inf')
        
    def _on_step(self) -> bool:
        # Получаем информацию с текущего шага
        reward = self.locals['rewards'][0]
        done = self.locals['dones'][0]
        info = self.locals['infos'][0]
        
        self.current_reward += reward
        self.current_length += 1
        
        # Выводим прогресс каждые 1000 шагов
        if self.num_timesteps % 1000 == 0:
            print(f"\n📊 ПРОГРЕСС: {self.num_timesteps} шагов")
            print(f"   Средняя награда за последние эпизоды: {np.mean(self.episode_rewards[-10:]):.2f}")
            print(f"   Средняя длина эпизода: {np.mean(self.episode_lengths[-10:]):.1f}")
        
        # Если эпизод завершен
        if done:
            self.episode_rewards.append(self.current_reward)
            self.episode_lengths.append(self.current_length)
            
            # Проверяем рекорд
            if self.current_reward > self.best_reward:
                self.best_reward = self.current_reward
                print(f"\n🏆 НОВЫЙ РЕКОРД! Награда: {self.current_reward:.2f}")
            
            # Детальная информация об эпизоде
            print(f"\n📊 ЭПИЗОД {len(self.episode_rewards)} ЗАВЕРШЕН:")
            print(f"   Награда: {self.current_reward:.2f}")
            print(f"   Длина: {self.current_length} шагов")
            print(f"   Цель достигнута: {info.get('goal_reached', False)}")
            print(f"   Коллизия: {info.get('collision', False)}")
            
            if info.get('goal_position') is not None:
                dist = info.get('distance_to_goal', 0)
                print(f"   Расстояние до цели: {dist:.2f} м")
            
            print(f"   Средняя награда (10 эп): {np.mean(self.episode_rewards[-10:]):.2f}")
            print("-" * 50)
            
            self.current_reward = 0
            self.current_length = 0
        
        return True

# ============================================
# 4. ЗАПУСК ОБУЧЕНИЯ
# ============================================
print("\n" + "="*80)
print("🚀 ЗАПУСК ОБУЧЕНИЯ")
print("="*80)

# Параметры обучения
TOTAL_TIMESTEPS = 100000  # общее количество шагов
SAVE_FREQUENCY = 10000    # сохранять модель каждые N шагов

try:
    # Обучаем с калбэком
    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=TrainingMonitor(),
        reset_num_timesteps=True,
    )
    
    print("\n✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
    
    # Сохраняем финальную модель
    model.save("trail_robot_final")
    print("💾 Финальная модель сохранена в trail_robot_final.zip")
    
except KeyboardInterrupt:
    print("\n\n🛑 ОБУЧЕНИЕ ПРЕРВАНО ПОЛЬЗОВАТЕЛЕМ!")
    
    # Сохраняем модель при прерывании
    model.save("trail_robot_interrupted")
    print("💾 Модель сохранена в trail_robot_interrupted.zip")

# ============================================
# 5. СТАТИСТИКА ОБУЧЕНИЯ
# ============================================
print("\n" + "="*80)
print("📊 ИТОГОВАЯ СТАТИСТИКА")
print("="*80)

# Получаем данные из монитора
import pandas as pd
try:
    log_data = pd.read_csv("trail_robot_monitor.csv")
    print(f"   Всего эпизодов: {len(log_data)}")
    print(f"   Средняя награда: {log_data['r'].mean():.2f}")
    print(f"   Макс награда: {log_data['r'].max():.2f}")
    print(f"   Средняя длина: {log_data['l'].mean():.1f}")
except:
    print("   Нет данных монитора")

print("\n" + "="*80)
print("🏁 ОБУЧЕНИЕ ЗАВЕРШЕНО!")
print("="*80)

env.close()