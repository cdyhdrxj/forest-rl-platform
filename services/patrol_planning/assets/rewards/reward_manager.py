from __future__ import annotations

from services.patrol_planning.assets.rewards.reward_config import RewardConfig
from services.patrol_planning.assets.rewards.events import (
    MoveEvent,
    BlockedMoveEvent,
    StayEvent,
    CatchEvent,
    DamageEvent,
    IntruderExitEvent,
    DetectionEvent,
    ExplorationEvent,
)


class RewardManager:
    """Единая точка начисления наград для GridForest.
    """

    def __init__(self, config: RewardConfig) -> None:
        self.config = config
        self._log: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_events(self, events: list, env) -> float:
        """Обработать события шага и вернуть суммарную награду."""
        total = 0.0
        self._log.clear()

        for event in events:
            if isinstance(event, MoveEvent):
                r = self._move_reward(event)
                self._log["r_move"] = self._log.get("r_move", 0.0) + r
                total += r
            elif isinstance(event, BlockedMoveEvent):
                r = self._blocked_reward(event)
                self._log["r_blocked"] = self._log.get("r_blocked", 0.0) + r
                total += r
            elif isinstance(event, StayEvent):
                r = -self.config.m_stay
                self._log["r_stay"] = self._log.get("r_stay", 0.0) + r
                total += r
            elif isinstance(event, CatchEvent):
                r = self._catch_reward(event)
                self._log["r_catch"] = self._log.get("r_catch", 0.0) + r
                total += r
            elif isinstance(event, DamageEvent):
                r = self._damage_reward(event)
                self._log["r_damage"] = self._log.get("r_damage", 0.0) + r
                total += r
            elif isinstance(event, IntruderExitEvent):
                r = self.config.m_exit_penalty
                self._log["r_exit"] = self._log.get("r_exit", 0.0) + r
                total += r
            elif isinstance(event, DetectionEvent):
                r = self._detection_reward(event)
                self._log["r_detection"] = self._log.get("r_detection", 0.0) + r
                total += r
            elif isinstance(event, ExplorationEvent):
                r = self._exploration_reward(event)
                self._log["r_exploration"] = self._log.get("r_exploration", 0.0) + r
                total += r

        r_idle = self._idle_reward(env)
        self._log["r_idle"] = r_idle
        total += r_idle

        return total

    def get_log(self) -> dict[str, float]:
        """Компонентный лог последнего шага (для info и TensorBoard)."""
        return dict(self._log)

    # ------------------------------------------------------------------
    # Component reward helpers
    # ------------------------------------------------------------------

    def _move_reward(self, event: MoveEvent) -> float:
        cfg = self.config
        if not cfg.use_passability_cost:
            return 0.0
        mu_from = max(event.mu_from, 1e-6)
        mu_to = max(event.mu_to, 1e-6)
        return -cfg.w_move * 0.5 * (1.0 / mu_from + 1.0 / mu_to)

    def _blocked_reward(self, event: BlockedMoveEvent) -> float:
        if event.reason == "out_of_bounds":
            return -self.config.m_out
        return -self.config.m_block  # 'impassable'

    #Старый вариант начисления. Оставить
    def _catch_reward_legacy(self, event: CatchEvent) -> float:
        cfg = self.config
        prevented = max(0.0, event.m_plan - event.m_damage)
        return cfg.w_catch * (cfg.m_catch + prevented)
    
    def _catch_reward(self, event: CatchEvent) -> float:
        cfg = self.config
        #prevented = max(0.0, event.m_plan - event.m_damage)
        return cfg.w_catch * (cfg.m_catch)

    def _damage_reward(self, event: DamageEvent) -> float:
        return -self.config.w_damage * event.delta

    def _exploration_reward(self, event: ExplorationEvent) -> float:
        cfg = self.config
        if cfg.exploration_reward == 0.0 and cfg.useful_exp_reward == 0.0:
            return 0.0
        n_plain = event.n_cells - event.n_valuable_cells
        plain_excess = event.staleness_excess - event.valuable_staleness_excess

        r_plain = cfg.exploration_reward * (plain_excess / n_plain) if n_plain > 0 else 0.0
        r_valuable = cfg.useful_exp_reward * (event.valuable_staleness_excess / event.n_valuable_cells) if event.n_valuable_cells > 0 else 0.0

        return r_plain + r_valuable

    def _detection_reward(self, event: DetectionEvent) -> float:
        cfg = self.config
        if cfg.detection_reward == 0.0:
            return 0.0
        k = event.n_intruders if cfg.scale_detection_by_count else 1
        if cfg.scale_detection_by_proximity:
            r = event.fov_radius + 1
            proximity = (r - event.min_distance) / r
            return k * cfg.detection_reward * proximity
        return k * cfg.detection_reward

    def _idle_reward(self, env) -> float:
        if self.config.w_idle == 0.0 or not hasattr(env, "idleness"):
            return 0.0
        staleness = env.idleness.staleness_map
        if self.config.idle_value_only:
            value_mask = env.world_layers["value"] > 0
            if not value_mask.any():
                return 0.0
            staleness = staleness[value_mask]
        return -self.config.w_idle * float(staleness.mean())
