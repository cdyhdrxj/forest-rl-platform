from pydantic import BaseModel, Field


class MetricsConfig(BaseModel):
    """Параметры и веса целевой функции задачи патрулирования.

    Z(π) = w1·M_damage + w2·M_move + w3·M_idleness

    Стоимость перемещения задаётся формулой:
        m_move(v, v') = 0.5*(1/μ_v + 1/μ_v'),  если v ≠ v'
        m_move(v, v)  = m_stay,                  если v = v'  (агент на месте)

    Эти параметры используются только для оценки алгоритма как решения исходной задачи,
    а не как параметры RL-сигнала (за это отвечает RewardConfig).
    """

    w1: float = Field(default=1.0, description="Вес суммарного ущерба M_damage в Z(π)")
    w2: float = Field(default=1.0, description="Вес стоимости маршрута M_move в Z(π)")
    w3: float = Field(default=1.0, description="Вес среднего простоя M_idleness в Z(π)")

    m_stay: float = Field(
        default=0.001,
        description=(
            "Стоимость пребывания на месте m_stay > 0. "
            "Используется в формуле m_move(v,v) = m_stay, когда агент не перемещается."
        ),
    )

    idleness_value_only: bool = Field(
        default=False,
        description=(
            "True — M_idleness считается только по ячейкам с value > 0. "
            "False — по всей карте (текущее поведение)."
        ),
    )

    enabled: bool = Field(
        default=True,
        description=(
            "Включить вычисление задачных метрик Z(π) = w1·M_damage + w2·M_move + w3·M_idleness. "
            "При False сбор метрик в step() и reset() пропускается — ускоряет обучение. "
            "Устанавливайте в False программно в обучающих скриптах; "
            "для EvaluationRunner оставляйте True (по умолчанию)."
        ),
    )
