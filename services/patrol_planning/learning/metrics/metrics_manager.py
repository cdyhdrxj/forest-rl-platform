from __future__ import annotations

from services.patrol_planning.learning.metrics.metrics_config import MetricsConfig
from services.patrol_planning.assets.rewards.events import MoveEvent, StayEvent, DamageEvent


class MetricsManager:
    """Оценивает алгоритм патрулирования как решение исходной задачи.

    Работает с теми же событиями (step_events), что и RewardManager, но вычисляет
    метрики задачи — не RL-награды. По завершении эпизода возвращает Z(π):

        Z(π) = w1·M_damage + w2·M_move + w3·M_idleness

    Z(π) — это функция минимизации (в отличие от суммарной RL-награды, которую
    алгоритм максимизирует). Чем меньше Z, тем качественнее стратегия патрулирования.

    Использование:
        # каждый шаг:
        metrics_manager.update_step(env.step_events)
        # в конце эпизода (до reset):
        metrics = metrics_manager.compute_episode(env, episode_length)
        metrics_manager.reset()
    """

    def __init__(self, config: MetricsConfig) -> None:
        self.config = config
        self._m_damage: float = 0.0
        self._m_move: float = 0.0
        self._last_episode: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_step(self, events: list) -> None:
        """Накопить метрики за один шаг из списка событий.

        Реализует формулу стоимости перемещения из концепции:
            m_move(v, v') = 0.5*(1/μ_from + 1/μ_to),  v ≠ v'  → MoveEvent
            m_move(v, v)  = m_stay,                     v = v'  → StayEvent

        Учитываются:
        - DamageEvent → M_damage (суммарный ущерб)
        - MoveEvent   → M_move  (реальный переход между ячейками)
        - StayEvent   → M_move  (агент на месте, стоимость = m_stay)
        """
        for event in events:
            if isinstance(event, DamageEvent):
                self._m_damage += event.delta
            elif isinstance(event, MoveEvent):
                # m_move(v, v') = 0.5 * (1/μ_from + 1/μ_to)
                mu_from = max(event.mu_from, 1e-6)
                mu_to = max(event.mu_to, 1e-6)
                self._m_move += 0.5 * (1.0 / mu_from + 1.0 / mu_to)
            elif isinstance(event, StayEvent):
                # m_move(v, v) = m_stay
                self._m_move += self.config.m_stay

    def compute_episode(self, env, episode_length: int) -> dict:
        """Вычислить итоговые метрики и Z(π) по завершении эпизода.

        Должен вызываться ДО reset() — чтобы IdlenessMetric ещё содержала
        данные текущего эпизода.

        Args:
            env: среда GridForest (нужен доступ к env.idleness)
            episode_length: число шагов в эпизоде (train_state.step)

        Returns:
            Словарь с ключами: M_damage, M_move, M_idleness, idleness_max, Z
        """
        cell_mask = None
        if self.config.idleness_value_only and hasattr(env, "world_layers"):
            mask = env.world_layers["value"] > 0
            if mask.any():
                cell_mask = mask
        idleness_result = env.idleness.calculate_metric(episode_length, cell_mask=cell_mask)
        m_idleness = idleness_result["mean"]

        cfg = self.config
        z = cfg.w1 * self._m_damage + cfg.w2 * self._m_move + cfg.w3 * m_idleness

        self._last_episode = {
            "M_damage": self._m_damage,
            "M_move": self._m_move,
            "M_idleness": m_idleness,
            "idleness_max": idleness_result["max"],
            "Z": z,
        }
        return dict(self._last_episode)

    def reset(self) -> None:
        """Сбросить накопители для нового эпизода."""
        self._m_damage = 0.0
        self._m_move = 0.0

    def get_step_accumulators(self) -> dict:
        """Текущие накопители внутри эпизода (для дебага)."""
        return {
            "m_damage_acc": self._m_damage,
            "m_move_acc": self._m_move,
        }

    def get_episode_metrics(self) -> dict:
        """Метрики последнего завершённого эпизода."""
        return dict(self._last_episode)
