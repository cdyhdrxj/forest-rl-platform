from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
from stable_baselines3.common.env_util import make_vec_env

from apps.api.sb3.sb3_trainer import SB3Trainer, EVAL_ROLES
from services.patrol_planning.assets.envs.forest import GridForest
from services.patrol_planning.assets.envs.models import GridForestConfig
from services.patrol_planning.service.callback import GridWorldCallback
from services.patrol_planning.service.models import GridWorldTrainState
from services.scenario_generator import extract_patrol_runtime_context
from services.scenario_generator.models import GeneratedScenario


class GridWorldService(SB3Trainer):
    """Сервис обучения для среды клеточного патрулирования."""

    def __init__(self):
        self.env: GridForest = None
        self.model = None
        self.training_state: GridWorldTrainState = self._make_state()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_config: GridForestConfig | None = None
        self.loaded_static_layers: dict[str, np.ndarray] = {}
        self.loaded_patrol_context = None
        self._algo_key: str = "ppo"
        self._execution_role: str = "train"
        self.last_error: str | None = None
        # Хэндл рабочего потока обучения — нужен, чтобы stop() мог дождаться
        # сохранения финальной модели перед тем, как диспетчер прочитает путь.
        self._training_thread: threading.Thread | None = None

    def start(self, params: dict) -> None:
        if self.training_state["running"]:
            return

        self.last_error = None
        resume = params.get("resume", False)
        self.training_state["mode"] = params.get("mode", "patrol")
        if not resume:
            self._reset_counters()

        execution_role = str(params.get("execution_role") or "train").lower()
        raw_algo = str(params.get("algorithm", "ppo")).lower()
        # Нормализуем имена от фронтенда к внутренним именам алгоритмов
        _algo_map = {"drqn": "alt_drqn"}
        self._algo_key = _algo_map.get(raw_algo, raw_algo)
        self._execution_role = execution_role

        self.training_state["running"] = True

        if execution_role in EVAL_ROLES:
            self._training_thread = None
            threading.Thread(
                target=self._run_eval_thread,
                args=(params,),
                daemon=True,
            ).start()
        else:
            self._training_thread = threading.Thread(
                target=self._run_training_thread,
                args=(params,),
                daemon=True,
            )
            self._training_thread.start()

    def stop(self) -> None:
        self.training_state["running"] = False

        if self._execution_role in EVAL_ROLES:
            if self.model and hasattr(self.model, "save"):
                checkpoint_path = self._resolve_checkpoint_save_path()
                self.model.save(str(checkpoint_path))
                p = Path(str(checkpoint_path))
                if not p.suffix:
                    p = p.with_suffix(".zip")
                self._last_checkpoint_path = str(p)
            return

        # Режим обучения: run_training() выполняется в фоновом потоке и выставляет
        # self._last_checkpoint_path только после того, как model.learn() размотается
        # и финальная модель будет записана на диск. Диспетчер читает путь сразу
        # после stop(), поэтому без ожидания возникает гонка: путь ещё None и
        # артефакт model_checkpoint не сохраняется (→ нет кнопки «Исполнить модель»).
        # Дожидаемся завершения потока. Все 4 алгоритма реагируют на running=False
        # и быстро доходят до сохранения; timeout страхует от зависания.
        t = self._training_thread
        if t is not None and t.is_alive():
            t.join(timeout=180)

    def reset(self) -> None:
        self.stop()
        self.training_state.reset_counters()
        self.training_state.running = False
        if self.loaded_scenario is not None:
            self._apply_preview_state(self.loaded_scenario)

    def _run_eval_thread(self, params: dict) -> None:
        """Исполнение обученной модели — аналог validate_checkpoint.py из research."""
        from services.patrol_planning.assets.envs.forest import GridForest
        from services.patrol_planning.learning.test.evaluation.agent import (
            SB3EvalAgent, RecurrentSB3EvalAgent, AltDRQNEvalAgent,
        )

        # Eval mode is always visual (user watches the agent execute)
        self.training_state["visualize"] = True

        algo_key = self._algo_key
        checkpoint_path = params.get("load_checkpoint_path")

        if not checkpoint_path:
            self.last_error = (
                "Для режима исполнения необходим load_checkpoint_path. "
                "Убедитесь что эксперимент был завершён через кнопку «Завершить»."
            )
            self.training_state["running"] = False
            return

        if not Path(checkpoint_path).exists():
            self.last_error = f"Чекпоинт не найден: {checkpoint_path}"
            self.training_state["running"] = False
            return

        # Собираем plain GridForest (не VecEnv) — так же как в research/validate_checkpoint.py
        config = self.loaded_config.model_copy(deep=True)
        exclude_layers = params.get("exclude_layers") or ["terrain"]
        config.obs_config.exclude_layers = exclude_layers

        env = GridForest.load(config)
        env.train_state = self.training_state  # WebSocket читает оттуда

        # Создаём агента нужного типа (по аналогии с _make_agent в validate_checkpoint.py)
        try:
            if algo_key == "alt_drqn":
                agent = AltDRQNEvalAgent(
                    model_path=checkpoint_path,
                    observation_space=env.observation_space,
                    n_actions=env.action_space.n,
                    device=params.get("device", "cpu"),
                )
            elif algo_key == "rppo":
                agent = RecurrentSB3EvalAgent(checkpoint_path)
            else:
                # ppo, dqn — оба поддерживаются SB3EvalAgent
                agent = SB3EvalAgent(checkpoint_path, algo_key)
        except Exception as exc:
            self.last_error = f"Не удалось загрузить модель: {exc}"
            self.training_state["running"] = False
            return

        # Eval loop: agent.predict + env.step
        try:
            obs, _ = env.reset()
            agent.reset()

            while self.training_state["running"]:
                action = agent.predict(obs)
                obs, _, terminated, truncated, _ = env.step(action)
                done = terminated or truncated

                if done:
                    self.training_state["new_episode"] = True
                    obs, _ = env.reset()
                    agent.reset()
                else:
                    self.training_state["new_episode"] = False

        except Exception as exc:
            self.last_error = str(exc)
            raise
        finally:
            self.training_state["running"] = False

    def _parse_algo_config_json(self, algo_key: str, json_dict: dict):
        """Validates user-uploaded algo config JSON against the Pydantic model for the given algo."""
        if algo_key == "ppo":
            from packages.rl_algorithms.patrol_planning.ppo.ppo_train_config import PPOTrainConfig
            cfg = PPOTrainConfig.model_validate(json_dict)
        elif algo_key == "dqn":
            from packages.rl_algorithms.patrol_planning.dqn.train.dqn_train_config import DQNTrainConfig
            cfg = DQNTrainConfig.model_validate(json_dict)
        elif algo_key == "alt_drqn":
            from packages.rl_algorithms.patrol_planning.alt_drqn.train.alt_drqn_train_config import AltDRQNTrainConfig
            cfg = AltDRQNTrainConfig.model_validate(json_dict)
        elif algo_key == "rppo":
            from packages.rl_algorithms.patrol_planning.rppo.train.rppo_train_config import RPPOTrainConfig
            cfg = RPPOTrainConfig.model_validate(json_dict)
        else:
            raise ValueError(f"Неизвестный алгоритм: {algo_key!r}")
        safety = {"cpu_cores_num": None}
        if hasattr(cfg, "use_torch_compile"):
            safety["use_torch_compile"] = False
        return cfg.model_copy(update=safety)

    def _run_training_thread(self, params: dict) -> None:
        import json
        import tempfile
        import glob as glob_module
        from services.patrol_planning.learning.learn_tool.run_training import run_training

        algo_key = self._algo_key

        # Algo config: from uploaded JSON or built from slider params
        algo_config_json = params.get("algo_config_json")
        if algo_config_json:
            algo_config = self._parse_algo_config_json(algo_key, algo_config_json)
        else:
            algo_config = self._build_algo_config(algo_key, params)

        # Visualize mode: force single env for step-by-step rendering
        visualize = bool(params.get("visualize", False))
        step_delay = float(params.get("step_delay", 0.0))
        if visualize:
            algo_config = algo_config.model_copy(update={"n_envs": 1})
        self.training_state["step_delay"] = step_delay
        self.training_state["visualize"] = visualize

        # Env config: from uploaded JSON or from loaded_config
        env_config_json = params.get("env_config_json")
        if env_config_json:
            config_dict = env_config_json
        else:
            config_dict = self.loaded_config.model_dump(mode="json")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(config_dict, f, ensure_ascii=False)
            temp_config_path = f.name

        # Источник конфига валидации:
        #   1) явно загруженный val_env_config_json, либо
        #   2) validate_on_generated → та же карта/конфиг, что и обучение (config_dict).
        # ValidationConfig строится только при наличии источника — иначе валидация
        # выключена (это и есть поведение «нет конфига → нет валидации»).
        val_env_config_json = params.get("val_env_config_json")
        validate_on_generated = bool(params.get("validate_on_generated", False))
        if val_env_config_json:
            val_source_dict = val_env_config_json
        elif validate_on_generated:
            val_source_dict = config_dict
        else:
            val_source_dict = None

        temp_val_config_path = None
        validation_config = None
        if val_source_dict is not None:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(val_source_dict, f, ensure_ascii=False)
                temp_val_config_path = f.name
            from services.patrol_planning.learning.validation.training_validator import ValidationConfig
            validation_config = ValidationConfig(
                config_path=temp_val_config_path,
                exclude_layers=params.get("exclude_layers") or ["terrain"],
                seed=int(params.get("validation_seed", 2026)),
                n_episodes=int(params.get("validation_n_episodes", 20)),
                freq=int(params.get("validation_freq", 100_000)),
                shared_train_state=self.training_state,
            )

        checkpoint_path = self._resolve_checkpoint_save_path()
        output_dir = str(Path(str(checkpoint_path)).parent)

        total_timesteps = int(params.get("total_timesteps", 3_000_000))

        try:
            run_training(
                algorithm=algo_key,
                algo_config=algo_config,
                config_path=temp_config_path,
                output_dir=output_dir,
                run_id=f"run_{self._run_id}",
                total_timesteps=total_timesteps,
                seed=int(params.get("seed", 42)),
                exclude_layers=params.get("exclude_layers") or ["terrain"],
                # Платформенный режим: периодические чекпоинты отключены — freq >
                # total_timesteps, поэтому CheckpointCallback ни разу не срабатывает.
                # TensorBoard выключен (use_tensorboard=False). Дисковые артефакты
                # run_training (configs/, logs/, checkpoints/) дочищаются в finally.
                # Сами функции run_training не меняются — research-скрипты сохраняют
                # всё как прежде.
                checkpoint_freq=total_timesteps + 1,
                use_tensorboard=False,
                setup_msvc=False,
                validation_config=validation_config,
                shared_train_state=self.training_state,
                step_delay=step_delay,
            )
            # Найти финальную модель в output_dir
            pattern = os.path.join(output_dir, "*", "model", "final*")
            paths = sorted(glob_module.glob(pattern))
            if paths:
                self._last_checkpoint_path = paths[-1]
        except Exception as exc:
            self.last_error = str(exc)
            raise
        finally:
            self.training_state["running"] = False
            try:
                os.unlink(temp_config_path)
            except OSError:
                pass
            if temp_val_config_path:
                try:
                    os.unlink(temp_val_config_path)
                except OSError:
                    pass
            # Платформенный режим: удаляем дисковые артефакты run_training, нужные
            # только research-запускам — TensorBoard-логи, периодические чекпоинты и
            # дампы конфигов. Финальную модель (model/) оставляем для инференса.
            # Отключение живёт здесь, в сервисе: research-скрипты вызывают
            # run_training напрямую и сохраняют всё как обычно.
            import shutil
            for _sub in ("checkpoints", "logs", "configs"):
                for _dir in glob_module.glob(os.path.join(output_dir, "*", _sub)):
                    shutil.rmtree(_dir, ignore_errors=True)
            # Force GC to free model weights, replay/rollout buffers, and numpy arrays
            # that may have cyclic references preventing immediate ref-count collection
            import gc
            gc.collect()

    def _build_algo_config(self, algo_key: str, params: dict):
        n_envs  = int(params.get("n_envs", 1))
        device  = str(params.get("device", "cpu"))
        lr      = float(params.get("learning_rate", 3e-4))
        gamma   = float(params.get("gamma", 0.999))

        if algo_key == "ppo":
            from packages.rl_algorithms.patrol_planning.ppo.ppo_train_config import PPOTrainConfig
            return PPOTrainConfig(
                lr=lr, gamma=gamma,
                n_steps=int(params.get("n_steps", 512)),
                batch_size=int(params.get("batch_size", 256)),
                n_epochs=int(params.get("n_epochs", 10)),
                clip_range=float(params.get("clip_range", 0.2)),
                ent_coef=float(params.get("ent_coef", 0.01)),
                policy_type="cnn", features_dim=64,
                n_envs=n_envs, normalize_rewards=True, device=device,
                cpu_cores_num=None,
            )
        elif algo_key == "dqn":
            from packages.rl_algorithms.patrol_planning.dqn.train.dqn_train_config import DQNTrainConfig
            # SB3 ReplayBuffer выделяет (buffer_size, n_envs, *obs_shape) сразу при создании.
            # При n_envs=8 и buffer_size=750K → ~5.8 GB. Масштабируем обратно пропорционально.
            _raw_buf = int(params.get("buffer_size", 750_000))
            _buf_size = max(1_000, _raw_buf // max(1, n_envs))
            return DQNTrainConfig(
                lr=lr, gamma=gamma,
                batch_size=int(params.get("batch_size", 256)),
                buffer_size=_buf_size,
                learning_starts=int(params.get("learning_starts", 25_000)),
                target_update_interval=int(params.get("target_update_interval", 8_000)),
                exploration_fraction=float(params.get("exploration_fraction", 0.45)),
                exploration_final_eps=float(params.get("exploration_final_eps", 0.05)),
                n_envs=n_envs, use_cnn=True, features_dim=64,
                normalize_rewards=True, device=device,
                use_torch_compile=False, cpu_cores_num=None,
            )
        elif algo_key == "alt_drqn":
            from packages.rl_algorithms.patrol_planning.alt_drqn.train.alt_drqn_train_config import AltDRQNTrainConfig
            return AltDRQNTrainConfig(
                lr=lr, gamma=gamma,
                batch_size=int(params.get("batch_size", 64)),
                lstm_hidden_size=int(params.get("lstm_hidden_size", 256)),
                unroll_length=int(params.get("unroll_length", 25)),
                # 75K episodes ≈ 75 GB RAM — заменяем на разумный дефолт ~2K episodes (~1 GB)
                buffer_capacity=int(params.get("buffer_capacity", 2_000)),
                learning_starts=int(params.get("learning_starts", 5_000)),
                target_update_freq=int(params.get("target_update_freq", 15_000)),
                epsilon_decay_steps=int(params.get("epsilon_decay_steps", 300_000)),
                epsilon_final=float(params.get("epsilon_final", 0.05)),
                train_freq=int(params.get("train_freq", 12)),
                n_envs=n_envs, use_amp=(device == "cuda"),
                normalize_rewards=True, device=device,
                cpu_cores_num=None,
            )
        elif algo_key == "rppo":
            from packages.rl_algorithms.patrol_planning.rppo.train.rppo_train_config import RPPOTrainConfig
            return RPPOTrainConfig(
                lr=lr, gamma=gamma,
                n_steps=int(params.get("n_steps", 512)),
                batch_size=int(params.get("batch_size", 256)),
                lstm_hidden_size=int(params.get("lstm_hidden_size", 256)),
                n_envs=n_envs, use_cnn=True, features_dim=64,
                device=device, use_torch_compile=False, cpu_cores_num=None,
            )
        else:
            raise ValueError(f"Неизвестный алгоритм: {algo_key!r}")

    def load_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> None:
        self.stop()
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.training_state["mode"] = scenario.task_kind.value
        self.loaded_scenario = scenario

        self.loaded_config = GridForestConfig.model_validate(runtime_config or {})

        if self.loaded_config.map_seed is None:
            self.loaded_config = self.loaded_config.model_copy(update={"map_seed": scenario.seed})

        self.loaded_patrol_context = extract_patrol_runtime_context(scenario)

        _map_config = self.loaded_config.model_copy(deep=True)
        _map_config.intruder_config = []
        _tmp_env = GridForest.load(_map_config)
        self.loaded_static_layers["passability"] = _tmp_env.world_layers["passability"].copy()
        self.loaded_static_layers["value"] = _tmp_env.world_layers["value"].copy()
        del _tmp_env

        self._apply_preview_state(scenario)

    def get_state(self) -> dict:
        s = self.training_state
        # During non-visual training, skip all visual fields — world_layers alone is 10-50KB
        # per message and causes browser GC pressure at 10Hz
        skip_visual = s.running and not s.visualize

        def _to_serializable(v):
            if hasattr(v, "tolist"):
                return v.tolist()
            return v

        base = {
            "running": s.running,
            "episode": s.episode,
            "step": s.step,
            "total_reward": float(s.total_reward),
            "total_damage": float(s.total_damage),
            "last_episode_reward": float(s.last_episode_reward),
            "new_episode": s.new_episode,
            "visualize": s.visualize,
        }

        if not skip_visual:
            base["agent_pos"] = [list(map(float, p)) for p in s.agent_pos]
            base["goal_pos"] = [list(map(float, p)) for p in s.goal_pos]
            base["world_layers"] = {
                k: _to_serializable(v)
                for k, v in (s.world_layers or {}).items()
            }
            base["i_count"] = s.i_count
            base["obs_raw"] = None
            if s.mode == "patrol":
                base["trajectory"] = [list(map(float, p)) for p in s.trajectory]

        if s.train_metrics is not None:
            base["train_metrics"] = s.train_metrics
        if s.val_metrics is not None:
            base["val_metrics"] = s.val_metrics
            base["val_step"] = s.val_step
        return base

    def _build_env(self, params: dict, resume: bool = False):
        """Строит eval VecEnv (используется super().start() в режиме eval)."""
        if self.loaded_config is None:
            raise RuntimeError("No scenario loaded")

        if resume and self.env is not None:
            return self.env

        config = self.loaded_config.model_copy(deep=True)

        if "max_steps" in params:
            config.max_steps = params["max_steps"]

        config.obs_config.exclude_layers = ["terrain"]
        static_layers = self.loaded_static_layers

        scenario_seed = None
        if self.loaded_scenario is not None:
            scenario_seed = self.loaded_scenario.runtime_context.get("seed", self.loaded_scenario.seed)

        use_random_spawn = config.agent_config.is_random_spawned

        def factory():
            env = GridForest.load(config)

            if "terrain" in static_layers:
                env.world_layers["terrain"] = static_layers["terrain"].copy()
                env.layers_backup["terrain"] = static_layers["terrain"].copy()
            if "passability" in static_layers:
                env.world_layers["passability"] = static_layers["passability"].copy()
                env.layers_backup["passability"] = static_layers["passability"].copy()
            if "value" in static_layers:
                env.world_layers["value"] = static_layers["value"].copy()
                env.layers_backup["value"] = static_layers["value"].copy()

            env.train_state = self.training_state

            if not resume:
                if use_random_spawn:
                    env.reset()
                else:
                    env.reset(seed=scenario_seed)

            return env

        return make_vec_env(factory, n_envs=1)

    def _make_callback(self) -> GridWorldCallback:
        return GridWorldCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.reset_counters()

    @staticmethod
    def _make_state() -> GridWorldTrainState:
        return GridWorldTrainState()

    def validate_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> list[str]:
        messages: list[str] = []
        if scenario.environment_kind.value != "grid":
            messages.append("GridWorld runtime can load only grid scenarios")
        if scenario.runtime_context.get("patrol") is None:
            messages.append("GridWorld runtime requires patrol runtime context")
        terrain = scenario.get_layer_data("terrain")
        if terrain is None:
            messages.append("GridWorld runtime requires a terrain layer")
        if runtime_config is None:
            messages.append("GridWorld runtime requires serialized runtime config")
        return messages

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload

        self.training_state.goal_pos = []
        self.training_state.i_count = 0

        if self.loaded_config and not self.loaded_config.agent_config.is_random_spawned:
            self.training_state.agent_pos = list(preview.get("agent_pos") or [])
        else:
            self.training_state.agent_pos = []

        self.training_state.trajectory = []
        self.training_state.new_episode = False
        self.training_state.running = False

        layers = {}
        terrain = scenario.get_layer_data("terrain")
        if terrain is not None:
            layers["terrain"] = np.asarray(terrain, dtype=np.float32).tolist()
        else:
            layers["terrain"] = preview.get("terrain_map")

        if "passability" in self.loaded_static_layers:
            layers["passability"] = self.loaded_static_layers["passability"].tolist()
        if "value" in self.loaded_static_layers:
            layers["value"] = self.loaded_static_layers["value"].tolist()

        self.training_state.world_layers = layers
