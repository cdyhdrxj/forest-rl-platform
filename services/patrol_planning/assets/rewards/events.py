from dataclasses import dataclass


@dataclass
class MoveEvent:
    """Агент успешно переместился в соседнюю клетку."""
    mu_from: float
    mu_to: float


@dataclass
class BlockedMoveEvent:
    """Агент попытался двинуться, но был заблокирован."""
    reason: str  # 'out_of_bounds' | 'impassable'


@dataclass
class StayEvent:
    """Агент выбрал действие STAY."""
    pass


@dataclass
class CatchEvent:
    """Нарушитель пойман агентом."""
    intruder_id: int
    m_damage: float   # нанесённый ущерб до поимки
    m_plan: float     # плановый ущерб (максимально возможный)


@dataclass
class DamageEvent:
    """Нарушитель нанёс ущерб за этот шаг."""
    delta: float


@dataclass
class IntruderExitEvent:
    """Нарушитель вышел за пределы карты, не будучи пойман."""
    intruder_id: int


@dataclass
class DetectionEvent:
    """Один или несколько нарушителей находятся в области видимости агента."""
    n_intruders: int
    min_distance: int = 0
    fov_radius: int = 7


@dataclass
class ExplorationEvent:
    """Агент наблюдает ячейки, не посещавшиеся дольше порогового времени."""
    n_cells: int
    n_valuable_cells: int = 0          # из них с value > 0
    staleness_excess: float = 0.0      # sum(staleness_i - thr) для всех stale-ячеек
    valuable_staleness_excess: float = 0.0  # sum(staleness_i - thr) для ценных stale-ячеек
