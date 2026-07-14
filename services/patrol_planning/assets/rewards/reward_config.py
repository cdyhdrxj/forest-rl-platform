from pydantic import BaseModel, Field


class RewardConfig(BaseModel):
    """Конфигурация системы наград для GridForest.
    """

    # --- Веса компонентов ---
    w_catch: float = Field(default=1.0, description="Вес компонента поимки R_catch")
    w_damage: float = Field(default=1.0, description="Вес компонента ущерба R_damage")
    w_move: float = Field(default=1.0, description="Вес компонента движения R_move")
    w_idle: float = Field(default=0.0, description="Вес компонента простоя R_idle (0 = выключен)")

    # --- Параметры поимки ---
    m_catch: float = Field(default=10.0, description="Базовая награда за поимку нарушителя")
    m_exit_penalty: float = Field(default=0.0, description="Штраф за выход нарушителя (отрицательное значение)")

    # --- Параметры движения ---
    m_out: float = Field(default=1.0, description="Штраф за попытку выйти за границу карты")
    m_stay: float = Field(
        default=0.001,
        description=(
            "Стоимость пребывания на месте m_stay > 0 (из формулы m_move(v,v) = m_stay). "
            "Применяется как RL-штраф за действие STAY."
        ),
    )
    m_block: float = Field(default=1.0, description="Штраф за движение в непроходимую клетку")
    use_passability_cost: bool = Field(
        default=True,
        description=(
            "Использовать формулу стоимости движения из концепции: "
            "m_move = w_move * 0.5 * (1/μ_from + 1/μ_to). "
            "False — движение бесплатно (только штрафы за STAY/блок)."
        ),
    )

    # --- Shaping ---
    detection_reward: float = Field(
        default=0.0,
        description="Награда за обнаружение нарушителя в области видимости (0 = выключено)",
    )
    scale_detection_by_count: bool = Field(
        default=False,
        description=(
            "True — награда = k * detection_reward, где k = кол-во нарушителей в FOV. "
            "False — фиксированная награда detection_reward при k >= 1."
        ),
    )
    scale_detection_by_proximity: bool = Field(
        default=False,
        description=(
            "True — detection_reward масштабируется по близости к ближайшему нарушителю: "
            "reward *= (fov_radius + 1 - min_distance) / (fov_radius + 1). "
            "Создаёт градиент награды: чем ближе нарушитель внутри FOV, тем выше награда."
        ),
    )
    exploration_reward: float = Field(
        default=0.0,
        description="Награда за обнаружение застоявшихся ячеек в FOV (0 = выключено)",
    )
    exploration_staleness_threshold: int = Field(
        default=10,
        description="Минимальный простой ячейки (в шагах) для получения exploration-награды",
    )
    useful_exp_reward: float = Field(
        default=0.0,
        description=(
            "Награда за ценные (value > 0) stale-ячейки: "
            "useful_exp_reward * mean(staleness_i - thr) по ценным stale-ячейкам. "
            "0 = выключено."
        ),
    )
    idle_value_only: bool = Field(
        default=False,
        description=(
            "True — при расчёте r_idle среднее берётся только по ячейкам с value > 0. "
            "False — среднее по всей карте (текущее поведение)."
        ),
    )
