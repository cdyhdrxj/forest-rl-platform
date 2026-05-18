import threading
from pathlib import Path

from stable_baselines3 import PPO, SAC, A2C
from apps.api.sb3.model_params import ALGO_DEFAULTS

ALGORITHMS = {
    "ppo": PPO,
    "sac": SAC,
    "a2c": A2C,
}

EVAL_ROLES = {"eval", "validation", "test", "test_eval", "run"}

# Параметры которые меняют observation_space или action_space.
# При eval эти параметры ДОЛЖНЫ совпадать с теми что были при обучении —
# иначе модель просто не сможет корректно предсказывать действия.
OBS_SPACE_PARAMS = {
    "grid_size",
    "obs_size",
    "layers_count",
}


class SB3Trainer:
    """
    Базовый класс для всех RL-сервисов.

    Режим обучения (execution_role=train, по умолчанию):
      - создаёт новую модель или загружает из checkpoint для дообучения
      - запускает model.learn() в отдельном потоке

    Режим исполнения (execution_role=eval и аналоги):
      - загружает модель из load_checkpoint_path
      - проверяет совместимость obs_space с новой средой
      - запускает predict-цикл без обучения
      - состояние обновляется так же как при обучении

    Диспетчер выставляет self._run_id после load_scenario() чтобы
    чекпоинт сохранялся в data/runs/run_{id}/model.zip.
    """

    _run_id: int | None = None
    _last_checkpoint_path: str | None = None

    def start(self, params: dict) -> None:
        self.last_error = None
        if self.training_state["running"]:
            return

        self._reset_counters()
        self.env = self._build_env(params)

        algo_key     = params.get("algorithm", "ppo").lower()
        algo_class   = ALGORITHMS.get(algo_key, PPO)
        defaults     = ALGO_DEFAULTS.get(algo_key, {})
        overrides    = {k: params[k] for k in defaults if k in params}
        model_kwargs = {**defaults, **overrides}

        execution_role  = str(params.get("execution_role") or "train").lower()
        load_checkpoint = params.get("load_checkpoint_path")

        if load_checkpoint:
            checkpoint = Path(str(load_checkpoint))
            if not checkpoint.exists():
                self.last_error = (
                    f"Чекпоинт не найден: {checkpoint}. "
                    "Убедитесь что эксперимент был завершён через кнопку «Завершить»."
                )
                return

            try:
                model = algo_class.load(str(checkpoint))
            except Exception as exc:
                self.last_error = f"Не удалось загрузить модель: {exc}"
                return

            incompatible = self._check_obs_space(model, self.env)
            if incompatible:
                self.last_error = incompatible
                return

            model.set_env(self.env)
            self.model = model
            self._last_checkpoint_path = str(checkpoint)
        else:
            self.model = algo_class("MlpPolicy", self.env, verbose=1, **model_kwargs)

        self.training_state["running"] = True

        if execution_role in EVAL_ROLES:
            if not load_checkpoint:
                self.last_error = (
                    "Для режима исполнения необходим load_checkpoint_path. "
                    "Выберите завершённый эксперимент с сохранённой моделью."
                )
                self.training_state["running"] = False
                return
            deterministic = bool(params.get("deterministic", True))
            eval_episodes = max(1, int(params.get("eval_episodes") or 999_999))
            threading.Thread(
                target=self._eval_loop,
                args=(deterministic, eval_episodes),
                daemon=True,
            ).start()
        else:
            threading.Thread(target=self._training_loop, daemon=True).start()

    def stop(self) -> None:
        self.training_state["running"] = False
        if self.model and hasattr(self.model, "save"):
            checkpoint_path = self._resolve_checkpoint_save_path()
            self.model.save(str(checkpoint_path))
            p = Path(str(checkpoint_path))
            if not p.suffix:
                p = p.with_suffix(".zip")
            self._last_checkpoint_path = str(p)

    # Обучение 

    def _training_loop(self) -> None:
        try:
            self.model.learn(
                total_timesteps=10_000_000,
                callback=self._make_callback(),
                reset_num_timesteps=True,
            )
        except Exception as exc:
            self.last_error = str(exc)
            raise
        finally:
            self.training_state["running"] = False

    # Исполнение модели 

    def _eval_loop(self, deterministic: bool, eval_episodes: int) -> None:
        """
        Запускает обученную модель без обучения.

        VecEnv (GridWorldService, SeedlingPlantingService):
            Среда пишет в train_state напрямую при каждом step() —
            синхронизация не нужна.

        gym.Env (CamarService):
            Callback не работает — синхронизируем вручную через
            _sync_gym_state() после каждого step().
        """
        is_vec = hasattr(self.env, "num_envs")

        try:
            if is_vec:
                observation = self.env.reset()
            else:
                observation, _ = self.env.reset()

            completed    = 0
            episode_reward = 0.0

            while self.training_state["running"]:
                action, _ = self.model.predict(observation, deterministic=deterministic)

                if is_vec:
                    observation, rewards, dones, infos = self.env.step(action)
                    reward = float(rewards[0])
                    done   = bool(dones[0])
                    info   = infos[0] if infos else {}
                else:
                    observation, reward, terminated, truncated, info = self.env.step(action)
                    done = terminated or truncated
                    self._sync_gym_state(reward, info, episode_reward, done)

                episode_reward += reward

                if done:
                    completed += 1
                    self.training_state["episode"]             = completed
                    self.training_state["last_episode_reward"] = episode_reward
                    self.training_state["new_episode"]         = True
                    episode_reward = 0.0

                    if completed >= eval_episodes:
                        break

                    if is_vec:
                        observation = self.env.reset()
                    else:
                        observation, _ = self.env.reset()
                else:
                    self.training_state["new_episode"] = False

        except Exception as exc:
            self.last_error = str(exc)
        finally:
            self.training_state["running"] = False

    def _sync_gym_state(self, reward: float, info: dict,
                        episode_reward: float, done: bool) -> None:
        """Синхронизация training_state для gym.Env (CamarService)."""
        env = self.env
        render = {}
        if hasattr(env, "get_render_state"):
            try:
                render = env.get_render_state()
            except Exception:
                pass

        if "agent_pos" in render:
            self.training_state["agent_pos"] = render["agent_pos"]
            if render["agent_pos"] and self.training_state.get("mode") == "trail":
                traj = self.training_state.setdefault("trajectory", [])
                traj.append(render["agent_pos"][0])
        
        if "goal_pos" in render:
            self.training_state["goal_pos"] = render["goal_pos"]
        if "landmark_pos" in render:
            self.training_state["landmark_pos"] = render["landmark_pos"]

        self.training_state["is_collision"]    = bool(info.get("is_collision", False))
        self.training_state["step"]            = self.training_state.get("step", 0) + 1
        self.training_state["total_reward"]    = episode_reward + reward

        if info.get("is_collision"):
            self.training_state["collision_count"] = \
                self.training_state.get("collision_count", 0) + 1
        if info.get("on_goal"):
            self.training_state["goal_count"] = \
                self.training_state.get("goal_count", 0) + 1
        if done:
            self.training_state["trajectory"] = []

    @staticmethod
    def _check_obs_space(model, env) -> str | None:
        """
        Проверить совместимость observation_space модели и среды.
        """
        try:
            model_space = model.observation_space
            env_space = getattr(env, "observation_space", None)
            if env_space is None:
                return None  

            if model_space.shape != env_space.shape:
                return (
                    f"Несовместимое пространство наблюдений: "
                    f"модель обучена на shape {model_space.shape}, "
                    f"текущая среда даёт shape {env_space.shape}. "
                    f"Параметры obs_size/layers_count/grid_size должны совпадать с исходным экспериментом."
                )
        except Exception:
            pass  
        return None

    def _resolve_checkpoint_save_path(self) -> Path:
        if self._run_id is not None:
            try:
                from apps.api.runtime_monitor import get_runtime_storage_root
                d = get_runtime_storage_root() / f"run_{self._run_id}"
                d.mkdir(parents=True, exist_ok=True)
                return d / "model"
            except Exception:
                pass
        return Path(f"{self.__class__.__name__}_model")