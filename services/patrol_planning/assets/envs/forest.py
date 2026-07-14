"""
GridForest — лесная среда, расширяющая GridWorld.

Добавляет три слоя:
  intruders   — {0, 1} наличие нарушителя
  passability — [0, 1] проходимость ячейки (μ)
  value       — [0, 1000] ценность леса (c)
"""
from __future__ import annotations

import math
import copy
import time
import warnings
from typing import List, Optional

import numpy as np

from services.patrol_planning.assets.envs.environment import GridWorld
from services.patrol_planning.assets.envs.src import generate_intruder_schedule, sample_spawn_cell
from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.assets.intruders.wanderer import Wanderer
from services.patrol_planning.assets.intruders.controllable import Controllable
# from services.patrol_planning.assets.intruders.poacher_simple_fixed import PoacherSimple
from services.patrol_planning.assets.intruders.poacher_simple import PoacherSimple
from services.patrol_planning.assets.intruders.poacher_alt import PoacherAlt
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.patrol_planning.assets.rewards.reward_config import RewardConfig
from services.patrol_planning.assets.rewards.reward_manager import RewardManager
from services.patrol_planning.assets.rewards.events import DetectionEvent, ExplorationEvent
from services.patrol_planning.learning.metrics.idleness import IdlenessMetric
from services.patrol_planning.learning.metrics.metrics_config import MetricsConfig
from services.patrol_planning.learning.metrics.metrics_manager import MetricsManager
from services.patrol_planning.learning.metrics.catch_latency import calc_catch_latency


class GridForest(GridWorld):
    """Лесная сеточная среда с поддержкой проходимости и ценности клеток."""

    def __init__(
        self,
        agent: GridWorldAgent,
        obs_model,
        grid_world_size: int = 20,
        intruders: Optional[List] = None,
        max_steps: int = 50,
        tau_min: int = 0,
        tau_max: int = 0,
        max_intruders: int = -1,
        reward_config: Optional[RewardConfig] = None,
        metrics_config: Optional[MetricsConfig] = None,
        random_map: bool = False,
        mu_min: float = 0.5,
        continue_until_max_steps: bool = False,
    ) -> None:
        super().__init__(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=grid_world_size,
            intruders=intruders or [],
            max_steps=max_steps,
        )
        self.reward_manager = RewardManager(reward_config or RewardConfig())
        self.metrics_manager = MetricsManager(metrics_config or MetricsConfig())
        # Добавляем лесные слои поверх базовых
        self.world_layers["passability"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        self.world_layers["value"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        # Слой простоя: сколько шагов назад каждая ячейка была в поле зрения агента
        self.world_layers["idleness"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        #Словарь со слоями, которые нужно сохранять в самом начале обучения и восстанавливать каждый сброс.
        self.layers_backup =  {}
        
        self.random_map = random_map
        self.mu_min = mu_min
        self.continue_until_max_steps = continue_until_max_steps
        self.max_intruders = max_intruders
        # Параметры генерации карты — заполняются в load(), используются в reset()
        self._forest_gen_kwargs: dict = {}

        #Список ячеек, выбранных ботами для рубки
        self.poacher_targets = []
        self.intruder_exit_count = 0
        
        #Создаём расписание
        self.intruder_schedule = []
        
        #Обнуляем список с нарушителями, будем их добавлять постепенно:
        self.intruders = []
        self.remember_intruder_schedule: bool = False
        
        #Появление нарушителей (сохраняем для восстановления)
        self.intruder_schedule_start = []
        self.intruder_schedule = copy.deepcopy(self.intruder_schedule_start)
        self.tau_min = tau_min
        self.tau_max = tau_max
        
        
        #Модули для оценки патрулирования
        self.idleness = IdlenessMetric(self)

        # Последнее наблюдение, возвращённое step() / reset() — используется рендерером
        self._last_obs = None

        self._last_terminated: bool = False
        self._last_truncated: bool = False
        # Attach an RLLogger instance here to enable research logging (opt-in).
        self.rl_logger = None

        # Per-episode аккумуляторы для тепловых карт нарушителей и урона.
        # Обнуляются при каждом reset(); передаются в rl_logger.on_episode_end().
        self._ep_intruder_acc = np.zeros((grid_world_size, grid_world_size), dtype=np.float64)
        self._ep_damage_acc   = np.zeros((grid_world_size, grid_world_size), dtype=np.float64)
        
    def step(self, action):
        # Сбрасываем список событий шага
        self.step_events = []

        # 1. действие агента (пишет событие в step_events, return игнорируем)
        self.agent.step(self, action)

        # 2. СПАВН нарушителя по расписанию
        t_key = self.train_state.step
        _spawned_this_step = None
        if t_key in self.intruder_schedule:

            index: int = self.intruder_schedule[t_key][0]
            intruder = copy.deepcopy(self.intruders_start[index])
            pos = self.intruder_schedule[t_key][1]

            if pos == (-1, -1):
                # manual_spawn=False: выбираем случайную граничную ячейку
                pos = sample_spawn_cell(self, self.mu_min)
            # manual_spawn=True: pos задана в расписании из конфига, используем as-is

            if pos is None:
                # Нет свободных граничных клеток — пропускаем спавн этого нарушителя
                warnings.warn(
                    f"GridForest.step: нет свободных граничных клеток на шаге {t_key}, спавн нарушителя пропущен"
                )
                self.intruder_exit_count += 1
            else:
                intruder.x = pos[0]
                intruder.y = pos[1]
                intruder.spawn_time = self.train_state.step
                self.world_layers["intruders"][intruder.x][intruder.y] = 1
                _spawned_this_step = intruder  # добавим после шагов, чтобы не двигался в тик спавна


        terminated = False
        truncated = False

        # 3. Инкремент простоя (все ячейки +1) — запись до построения наблюдения,
        #    чтобы агент видел актуальное время простоя, а не обнулённый слой.
        self.idleness.increment_staleness()
        self.world_layers["idleness"] = self.idleness.get_staleness_layer()

        # 4. Строим наблюдение — канал idleness содержит увеличенные значения
        observation = self.obs.build_observation(self.world_layers, self.agent)
        self._last_obs = observation

        # 5. Регистрируем посещение видимых ячеек в истории (только если метрики включены)
        if self.metrics_manager.config.enabled:
            self.idleness.update(observation=observation,
                                 agent_pos=(self.agent.x, self.agent.y),
                                 step=self.train_state.step)

        # Вычисляем FOV-bounds один раз для exploration и detection
        obs_h, obs_w = observation.shape[1:3]
        ay, ax = self.agent.x, self.agent.y
        gy_start = max(0, ay - obs_h // 2)
        gy_stop  = min(self.grid_world_size, ay - obs_h // 2 + obs_h)
        gx_start = max(0, ax - obs_w // 2)
        gx_stop  = min(self.grid_world_size, ax - obs_w // 2 + obs_w)

        # 6a. Exploration reward — считаем ДО reset_visible, пока staleness актуален
        thr = self.reward_manager.config.exploration_staleness_threshold
        if (self.reward_manager.config.exploration_reward != 0.0
                or self.reward_manager.config.useful_exp_reward != 0.0) and thr > 0:
            fov_staleness = self.idleness.staleness_map[gy_start:gy_stop, gx_start:gx_stop]
            stale_mask = fov_staleness >= thr
            n_stale = int(stale_mask.sum())
            if n_stale > 0:
                fov_value = self.world_layers["value"][gy_start:gy_stop, gx_start:gx_stop]
                val_stale_mask = stale_mask & (fov_value > 0)
                n_valuable_stale = int(val_stale_mask.sum())
                staleness_excess = float((fov_staleness[stale_mask] - thr).sum())
                val_staleness_excess = float((fov_staleness[val_stale_mask] - thr).sum()) if n_valuable_stale > 0 else 0.0
                self.step_events.append(
                    ExplorationEvent(
                        n_cells=n_stale,
                        n_valuable_cells=n_valuable_stale,
                        staleness_excess=staleness_excess,
                        valuable_staleness_excess=val_staleness_excess,
                    )
                )

        # 6. Сбрасываем простой видимых ячеек в ноль (после того как агент их наблюдал)
        self.idleness.reset_visible(observation=observation,
                                    agent_pos=(self.agent.x, self.agent.y))
        self.world_layers["idleness"] = self.idleness.get_staleness_layer()

        # 6b. Detection reward — считаем ПОСЛЕ reset_visible (нарушители ещё не двигались)
        fov_intruder_layer = np.asarray(self.world_layers["intruders"])[gy_start:gy_stop, gx_start:gx_stop]
        n_det = int(fov_intruder_layer.sum())
        if n_det > 0:
            positions = np.argwhere(fov_intruder_layer > 0)
            distances = np.abs(positions[:, 0] + gy_start - ay) + np.abs(positions[:, 1] + gx_start - ax)
            fov_radius = obs_h // 2
            self.step_events.append(DetectionEvent(
                n_intruders=n_det,
                min_distance=int(distances.min()),
                fov_radius=fov_radius,
            ))

        # Снапшот слоя ценности до обновления нарушителей — для карты урона
        if self.rl_logger is not None:
            _value_snap = self.world_layers["value"].copy()

        #Обновляем нарушителей (пишут события в step_events, return игнорируем)
        for i in list(self.intruders):  # list() — копия, т.к. kill() меняет self.intruders
            try:
                i.step(self)
            except Exception as exc:
                warnings.warn(
                    f"GridForest.step: необработанная ошибка нарушителя {type(i).__name__} "
                    f"на ({i.x},{i.y}): {exc}"
                )
                if i in self.intruders:
                    if 0 <= i.x < self.grid_world_size and 0 <= i.y < self.grid_world_size:
                        self.world_layers["intruders"][i.x][i.y] = 0
                    self.intruders.remove(i)
                    self.intruder_exit_count += 1

        # Заспавненный в этом тике нарушитель начнёт двигаться только со следующего шага
        if _spawned_this_step is not None:
            self.intruders.append(_spawned_this_step)

        # Накопление per-episode карт нарушителей и урона
        if self.rl_logger is not None:
            self._ep_damage_acc   += np.clip(_value_snap - self.world_layers["value"], 0.0, None)
            self._ep_intruder_acc += self.world_layers["intruders"].astype(np.float64)

        # Единая точка начисления наград
        reward = self.reward_manager.process_events(self.step_events, self)
        # Накапливаем метрики задачи (M_damage, M_move)
        if self.metrics_manager.config.enabled:
            self.metrics_manager.update_step(self.step_events)

        if self.rl_logger is not None:
            from services.patrol_planning.assets.rewards.events import BlockedMoveEvent as _BME
            _event_names = [
                f"BlockedMoveEvent_{e.reason}" if isinstance(e, _BME) else type(e).__name__
                for e in self.step_events
            ]
            self.rl_logger.on_step(
                action=int(action),
                pos=(self.agent.x, self.agent.y),
                reward=reward,
                reward_components=self.reward_manager.get_log(),
                events=_event_names,
                total_damage=float(self.train_state.total_damage) if self.train_state else 0.0,
            )

        info = {
            "reward_components": self.reward_manager.get_log(),
            "intruders_left": len(self.intruder_schedule_start) - self.intruder_exit_count,
        }
        
        #Обновляем рендер если включено
        if self.renderer is not None:
            self.renderer.live.update(self.renderer.render())
            time.sleep(self.render_time_sleep)
        
        #Записываем слои в состояние обучения только в режиме визуализации
        if self.train_state.visualize:
            self.train_state.world_layers = self.world_layers
           
            
        #Завершаем эпизод если все нарушители вышли/были пойманы из леса
        if (not self.continue_until_max_steps
                and self.intruder_exit_count == len(self.intruder_schedule_start)):
            terminated = True
        
        
        
        self.train_state.step += 1
        #Проверяем превышение по шагам
        if self.train_state.step >= self.max_steps:
            truncated = True
        
        self._last_terminated = terminated
        self._last_truncated = truncated

        #Обновляем train_state
        super().update_train_state(truncated, terminated, reward, observation)


        return observation, reward, terminated, truncated, info

    def generate_forest(
        self,
        seed: Optional[int] = None,
        passability_low: float = 0.0,
        passability_high: float = 1.0,
        impassable_prob: float = 0.15,
        max_value: float = 1000.0,
        value_density: float = 0.7,
    ) -> None:
        """
        Случайно генерирует карту леса.

        Алгоритм:
          1. Для каждой клетки с вероятностью impassable_prob μ = 0,
             иначе μ ~ Uniform(passability_low, passability_high).
          2. Для клеток с μ > 0: с вероятностью value_density
             назначается c ~ Uniform(0, max_value), иначе c = 0.
          3. Для клеток с μ = 0: c = 0 (принудительно).

        Args:
            seed: Зерно генератора для воспроизводимости.
            passability_low: Минимальное значение проходимости (μ > 0).
            passability_high: Максимальное значение проходимости.
            impassable_prob: Вероятность того, что ячейка непроходима (μ = 0).
            max_value: Максимальная ценность ячейки.
            value_density: Доля проходимых клеток, имеющих ценность > 0.
        """
        rng = np.random.default_rng(seed)
        n = self.grid_world_size

        # --- Проходимость ---
        is_impassable = rng.random((n, n)) < impassable_prob
        passability = rng.uniform(passability_low, passability_high, (n, n)).astype(
            np.float32
        )
        passability[is_impassable] = 0.0
        self.world_layers["passability"] = passability

        # --- Ценность ---
        value = np.zeros((n, n), dtype=np.float32)
        passable_mask = passability > 0.0
        has_value_mask = rng.random((n, n)) < value_density
        # Только проходимые клетки могут иметь ценность
        assign_value = passable_mask & has_value_mask
        value[assign_value] = rng.uniform(0.0, max_value, assign_value.sum()).astype(
            np.float32
        )
        self.world_layers["value"] = value


    def load_map_from_files(self, passability_path: str, value_path: str) -> None:
        """Загружает слои passability и value из CSV-файлов.

        Формат: матрица grid_size×grid_size, разделитель — запятая.
        Строка i, столбец j → ячейка (i, j) сетки.
        """
        passability = np.loadtxt(passability_path, delimiter=",").astype(np.float32)
        value = np.loadtxt(value_path, delimiter=",").astype(np.float32)

        n = self.grid_world_size
        if passability.shape != (n, n):
            raise ValueError(
                f"passability: ожидалась форма ({n}, {n}), получена {passability.shape}"
            )
        if value.shape != (n, n):
            raise ValueError(
                f"value: ожидалась форма ({n}, {n}), получена {value.shape}"
            )

        self.world_layers["passability"] = passability
        self.world_layers["value"] = value

    def reset(self, seed=None, options=None):
        """Сбрасывает среду, сохраняя лесные слои (если уже сгенерированы)."""
        
        # Вычисляем и сохраняем метрики завершённого эпизода ДО сброса состояния
        episode_metrics = None
        if self.train_state.step > 0 and self.metrics_manager.config.enabled:
            episode_metrics = self.metrics_manager.compute_episode(self, self.train_state.step)
            self.train_state.episode_metrics = episode_metrics

        if self.rl_logger is not None and self.train_state.step > 0:
            if self.metrics_manager.config.enabled:
                _idleness_interval = self.idleness.calculate_metric(self.train_state.step)
                _idleness_map = _idleness_interval["map"]
            else:
                _idleness_map = None
            _catch_latency = list(self.train_state.catch_latency) if self.train_state else []
            self.rl_logger.on_episode_end(
                terminated=self._last_terminated,
                truncated=self._last_truncated,
                episode_metrics=episode_metrics,
                intruders_scheduled=len(self.intruder_schedule_start),
                idleness_map=self.idleness.get_staleness_layer(),
                idleness_interval_map=_idleness_map,
                intruder_acc_map=self._ep_intruder_acc.copy(),
                damage_acc_map=self._ep_damage_acc.copy(),
                catch_latency=_catch_latency,
            )
        # Сброс per-episode аккумуляторов
        self._ep_intruder_acc = np.zeros((self.grid_world_size, self.grid_world_size), dtype=np.float64)
        self._ep_damage_acc   = np.zeros((self.grid_world_size, self.grid_world_size), dtype=np.float64)
        self.metrics_manager.reset()

        self.idleness.reset()
        
        #Сбрасываем внутри-эпизодные счётчики (episode и last_episode_reward сохраняются)
        self.train_state.reset_per_episode()
        

        # Если random_map=True — генерируем новую карту и сбрасываем кеш,
        # чтобы ниже она была заново зафиксирована как текущий бэкап.
        if self.random_map and self._forest_gen_kwargs:
            self.layers_backup = {}
            self.generate_forest(seed=None, **self._forest_gen_kwargs)

        # Кешируем лесные слои до вызова super().reset(), если сохранения не было
        if not self.layers_backup:

            if self.world_layers.get("passability") is not None:
                self.layers_backup["passability"] = (
                    self.world_layers["passability"].copy()
                )

            if self.world_layers.get("value") is not None:
                self.layers_backup["value"] = (
                    self.world_layers["value"].copy()
                )

        # Получаем сохранённую информацию 
        passability_backup = (
            self.layers_backup["passability"].copy()
            if self.layers_backup.get("passability") is not None
            else None
        )

        value_backup = (
            self.layers_backup["value"].copy()
            if self.layers_backup.get("value") is not None
            else None
        )

        # reset родителя
        _observation, _info = super().reset(seed=seed, options=options)

        # GridWorld.reset() вызывает intruder.reset() для каждого intruders_start,
        # что пишет позиции в слой. В GridForest нарушители спавнятся через schedule,
        # поэтому очищаем слой сразу после вызова родителя.
        self.world_layers["intruders"] = np.zeros(
            (self.grid_world_size, self.grid_world_size), dtype=np.float32
        )

        # Восстанавливаем слои без ссылок
        if passability_backup is not None:
            self.world_layers["passability"] = passability_backup.copy()
        else:
            self.world_layers["passability"] = np.zeros(
                (self.grid_world_size, self.grid_world_size),
                dtype=np.float32
            )

        if value_backup is not None:
            self.world_layers["value"] = value_backup.copy()
        else:
            self.world_layers["value"] = np.zeros(
                (self.grid_world_size, self.grid_world_size),
                dtype=np.float32
            )

        observation = self.obs.build_observation(self.world_layers, self.agent)
        self._last_obs = observation
        info = {}

        # Убираем нарушителей и их спавн (они спавняться по событиям)
        self.intruders = []
        self.intruder_exit_count = 0

        #Сбрасываем цели
        self.poacher_targets = []

        # Сбрасываем слой простоя (IdlenessMetric уже сброшен выше)
        self.world_layers["idleness"] = np.zeros(
            (self.grid_world_size, self.grid_world_size), dtype=np.float32
        )

        #Сохраняется ли расписание для всех эпизодов
        if self.remember_intruder_schedule:
            #Если пусто => генерируем новое
            if not self.intruder_schedule_start:
                self.intruder_schedule_start = generate_intruder_schedule(
                    self.intruders_start, self.max_steps,
                    tau_min=self.tau_min, tau_max=self.tau_max,
                    K=self.max_intruders,
                )
            #берём старое
            self.intruder_schedule = copy.deepcopy(self.intruder_schedule_start)
        else:
            #генерируем новое
            self.intruder_schedule_start = generate_intruder_schedule(
                self.intruders_start, self.max_steps,
                tau_min=self.tau_min, tau_max=self.tau_max,
                K=self.max_intruders,
            )
            self.intruder_schedule = copy.deepcopy(self.intruder_schedule_start)
            
        return observation, info
    @staticmethod
    def load(config: "GridForestConfig") -> "GridForest":
        """
        Создаёт настроенный экземпляр GridForest из GridForestConfig.

        Автоматически вызывает generate_forest() с параметрами из конфига.

        Args:
            config: GridForestConfig

        Returns:
            GridForest: готовый экземпляр среды с картой
        """
        # Импорт здесь, чтобы избежать циклических зависимостей
        from services.patrol_planning.assets.envs.models import GridForestConfig
        from services.patrol_planning.assets.intruders.models import (
            WandererConfig, ControllableConfig, PoacherConfig, PoacherAltConfig,
        )

        if not isinstance(config, GridForestConfig):
            raise ValueError(
                f"Ожидался GridForestConfig, получено: {type(config)}"
            )
        # Агент
        agent = GridWorldAgent.load(config.agent_config)

        # Модель наблюдения — прокидываем параметры нормировки из конфига среды
        config.obs_config.max_value = config.max_value
        config.obs_config.max_steps = config.max_steps
        config.obs_config.grid_size = config.grid_size

        # Автоматически вычисляем число каналов с учётом исключённых слоёв,
        # чтобы форма пространства наблюдений всегда соответствовала фильтру.
        _all_forest_layers = [
            "terrain", "intruders", "rows", "cols",
            "passability", "value", "idleness",
        ]
        excluded = set(config.obs_config.exclude_layers)
        config.obs_config.layers_count = sum(
            1 for k in _all_forest_layers if k not in excluded
        )

        obs_model = ObservationBox.load(config.obs_config)

        # ПОДДЕРЖИВАЕМ ТОЛЬКО PoacherSimple
        intruders = []
        for intruder_config in config.intruder_config:
            match type(intruder_config).__name__:
                # case "WandererConfig":
                #     intruders.append(Wanderer.load(intruder_config))
                # case "ControllableConfig":
                #     intruders.append(Controllable.load(intruder_config))
                # case "PoacherConfig":
                #     intruders.append(Poacher.load(intruder_config))
                case 'PoacherSimpleConfig':
                    intruders.append(PoacherSimple.load(intruder_config))
                case 'PoacherAltConfig':
                    intruders.append(PoacherAlt.load(intruder_config))
                case _:
                    raise ValueError(
                        f"Неподдерживаемый тип нарушителя: {type(intruder_config).__name__}"
                    )

        env = GridForest(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=config.grid_size,
            intruders=intruders,
            max_steps=config.max_steps,
            tau_min=config.tau_min,
            tau_max=config.tau_max,
            max_intruders=config.max_intruders,
            reward_config=config.reward_config,
            metrics_config=config.metrics_config,
            random_map=config.random_map,
            mu_min=config.mu_min,
            continue_until_max_steps=config.continue_until_max_steps,
        )

        if config.load_layers is not None:
            # Загружаем карту из файлов; _forest_gen_kwargs остаётся пустым,
            # поэтому reset() не будет перегенерировать карту каждый эпизод.
            env.load_map_from_files(config.load_layers.passability, config.load_layers.value)
        else:
            # Параметры генерации без seed — reset() будет вызывать generate_forest(seed=None, ...)
            env._forest_gen_kwargs = dict(
                passability_low=config.passability_low,
                passability_high=config.passability_high,
                impassable_prob=config.impassable_prob,
                max_value=config.max_value,
                value_density=config.value_density,
            )

            # Генерируем начальную карту
            env.generate_forest(
                seed=config.map_seed,
                passability_low=config.passability_low,
                passability_high=config.passability_high,
                impassable_prob=config.impassable_prob,
                max_value=config.max_value,
                value_density=config.value_density,
            )
        
        env.reset()

        return env
