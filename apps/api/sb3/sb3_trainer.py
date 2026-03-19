import threading
from stable_baselines3 import PPO, SAC, A2C
from apps.api.sb3.model_params import ALGO_DEFAULTS

ALGORITHMS = {
    "ppo": PPO,
    "sac": SAC,
    "a2c": A2C,
}


class SB3Trainer:
    """
    Класс для управления алгоритмами обучения из библиотеки Stable Baselines3. 

    Требует от класса:
      - self.training_state: dict  (с ключом "running")
      - self.env: gym.Env | None
      - self.model: SB3 model | None
      - self._build_env(params) -> gym.Env
      - self._make_callback() -> BaseCallback
      - self._reset_counters() -> None
    """

    def start(self, params: dict) -> None:
        if self.training_state["running"]:
            return

        self._reset_counters()
        self.env = self._build_env(params)

        # Выбор алгоритма, по умолчанию PPO
        algo_key = params.get("algorithm", "ppo").lower()
        algo_class = ALGORITHMS.get(algo_key, PPO)
        
        # Параметры модели: берём начальные настройки алгоритмов и перезаписываем с фронта
        defaults = ALGO_DEFAULTS.get(algo_key, {})
        overrides = {k: params[k] for k in defaults if k in params}
        model_kwargs = {**defaults, **overrides}

        self.model = algo_class("MlpPolicy", self.env, verbose=1, **model_kwargs)
        self.training_state["running"] = True
        threading.Thread(target=self._training_loop, daemon=True).start()

    def stop(self) -> None:
        self.training_state["running"] = False
        if self.model:
            self.model.save(f"{self.__class__.__name__}_model")

    def _training_loop(self) -> None:
        self.model.learn(
            total_timesteps=10_000_000,
            callback=self._make_callback(),
            reset_num_timesteps=True,
        )