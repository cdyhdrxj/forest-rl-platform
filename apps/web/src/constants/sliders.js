export const SLIDER_CONFIG = {

  "Непрерывная 2D": {

    "Тропы": {
      "Алгоритм": [
        { param: "learning_rate",     label: "Скор. обучения",  min: 0.00001, max: 0.01,  step: 0.00001 },
        { param: "gamma",             label: "Гамма (γ)",       min: 0.9,     max: 0.999, step: 0.001   },
        { param: "max_steps",         label: "Макс. шагов",     min: 50,      max: 1000,  step: 10      },
        { param: "tau",               label: "Тау",             min: 0.001,   max: 0.1,   step: 0.001,  algoOnly: ["SAC", "TD3"] },
        { param: "goal_reward",       label: "Награда за цель", min: 10,      max: 100,   step: 5       },
        { param: "collision_penalty", label: "Штраф столкн.",   min: 0,       max: 5,     step: 0.1     },
        { param: "step_penalty",      label: "Штраф за шаг",    min: 0,       max: 1,     step: 0.01    },
        { param: "terrain_penalty",   label: "Штраф рельефа",   min: 0,       max: 1,     step: 0.01    },
      ],
      "Карта": [
        { param: "grid_size",        label: "Размер сетки", min: 5, max: 20,  step: 1    },
        { param: "obstacle_density", label: "Препятствия",  min: 0, max: 0.4, step: 0.01 },
      ],
      "Робот": [
        { param: "action_scale", label: "Масштаб действий", min: 0.1,   max: 5,    step: 0.1   },
        { param: "max_speed",    label: "Макс. скорость",   min: 1,     max: 200,  step: 1     },
        { param: "accel",        label: "Разгон",           min: 1,     max: 100,  step: 1     },
        { param: "damping",      label: "Торможение",       min: 0.01,  max: 0.99, step: 0.01  },
        { param: "dt",           label: "Шаг физики",       min: 0.001, max: 0.05, step: 0.001 },
      ],
    },
  },

  "Дискретная": {

    "Патруль": {
      "Алгоритм": [
        { param: "learning_rate", label: "Скор. обучения", min: 0.00001, max: 0.01, step: 0.00001 },
        { param: "gamma", label: "Гамма (γ)", min: 0.9, max: 0.999, step: 0.001 },

        { param: "max_steps", label: "Макс. шагов", min: 50, max: 1000, step: 10 },

        { param: "max_value", label: "Макс. ценность", min: 100, max: 5000, step: 100 },
        { param: "value_density", label: "Плотность ценности", min: 0, max: 1, step: 0.01 },

        { param: "intruder_detection_reward", label: "Обнаружение", min: 0, max: 50, step: 0.5 },
        { param: "intruder_interception_reward", label: "Перехват", min: 0, max: 100, step: 1 },
      ],

      "Агент": [
        { param: "m_block", label: "Штраф блок", min: 0, max: 20, step: 0.5 },
        { param: "m_out", label: "Штраф выход", min: 0, max: 5, step: 0.1 },
        { param: "m_stay", label: "Штраф стояния", min: 0, max: 2, step: 0.05 },
        { param: "is_random_spawned", label: "Случайный спавн", type: "bool" },
      ],

      "Наблюдение": [
        { param: "obs_size", label: "Размер обзора", min: 1, max: 9, step: 2 },
        { param: "layers_count", label: "Кол-во слоёв", min: 1, max: 8, step: 1 },
      ],

      "Карта": [
        { param: "grid_size", label: "Размер сетки", min: 5, max: 20, step: 1 },
        { param: "passability_low", label: "Мин. проходимость", min: 0, max: 0.5, step: 0.01 },
        { param: "passability_high", label: "Макс. проходимость", min: 0.5, max: 1, step: 0.01 },
        { param: "impassable_prob", label: "Непроходимость", min: 0, max: 0.5, step: 0.01 },
        { param: "map_seed", label: "Seed карты", min: 0, max: 99999999, step: 1 },
        { param: "max_value", label: "Макс. ценность", min: 100, max: 5000, step: 100 },
        { param: "value_density", label: "Плотность ценности", min: 0, max: 1, step: 0.01 },
      ],

      "Нарушитель": [
        { param: "intruder_count", label: "Кол-во нарушителей", min: 1, max: 10, step: 1 },

        { param: "catch_reward", label: "Награда за поимку", min: 0, max: 10, step: 0.5 },
        { param: "m_plan", label: "План ущерба", min: 10, max: 5000, step: 10 },
        { param: "m_defence", label: "Защита", min: 0, max: 5, step: 0.1 },

        { param: "incoming_step", label: "Момент появления", min: -1, max: 500, step: 1 },
        { param: "incoming_patience", label: "Терпение входа", min: 5, max: 200, step: 5 },

        { param: "felling_intensity", label: "Интенсивность вырубки", min: 0, max: 200, step: 1 },

        { param: "m_tool_power",      label: "Мощность инструмента", min: 0,  max: 500, step: 10 },
        { param: "search_patience",   label: "Терпение поиска",      min: 5,  max: 200, step: 5  },
                
        { param: "incoming", label: "Входящий нарушитель", type: "bool" },
        { param: "intruder_is_random_spawned", label: "Случайный спавн", type: "bool" },
      ],
    },

    "Посадка": {
      "Алгоритм": [
        { param: "learning_rate",      label: "Скор. обучения",      min: 0.00001, max: 0.01, step: 0.00001 },
        { param: "gamma",              label: "Гамма (γ)",           min: 0.9,     max: 0.999, step: 0.001  },
        { param: "max_steps",          label: "Макс. шагов",         min: 50,      max: 1000,  step: 10     },
        { param: "step_penalty",       label: "Штраф за шаг",        min: 0,       max: 1,     step: 0.01   },
        { param: "alpha_plant",        label: "Награда за посадку",  min: 0.5,     max: 10,    step: 0.1    },
        { param: "alpha_quality",      label: "Вес качества",        min: 0,       max: 5,     step: 0.1    },
        { param: "beta_move",          label: "Штраф движения",      min: 0,       max: 1,     step: 0.01   },
        { param: "beta_turn",          label: "Штраф поворота",      min: 0,       max: 1,     step: 0.01   },
        { param: "beta_invalid_plant", label: "Штраф плохой посадки",min: 0,       max: 2,     step: 0.01   },
      ],
      "Карта": [
        { param: "grid_size",            label: "Размер сетки",       min: 5,    max: 20,  step: 1    },
        { param: "obstacle_density",     label: "Препятствия",        min: 0,    max: 0.4, step: 0.01 },
        { param: "plantable_density",    label: "Засаживаемость",     min: 0.1,  max: 1,   step: 0.01 },
        { param: "min_plant_distance",   label: "Мин. расстояние",    min: 0,    max: 3,   step: 1    },
        { param: "uniformity_radius",    label: "Радиус равномерн.",  min: 0,    max: 3,   step: 1    },
        { param: "target_density",       label: "Целевая плотн.",     min: 0.05, max: 0.8, step: 0.01 },
        { param: "lambda_uniformity",    label: "Штраф равномерн.",   min: 0,    max: 10,  step: 0.1  },
        { param: "lambda_underplanting", label: "Штраф недопосадки",  min: 0,    max: 10,  step: 0.1  },
      ],
      "Робот": [
        { param: "initial_seedlings", label: "Саженцев на борту",  min: 5, max: 80, step: 1    },
        { param: "beta_stay",         label: "Штраф стояния",      min: 0, max: 1,  step: 0.01 },
        { param: "beta_fail_move",    label: "Штраф неудачи хода", min: 0, max: 2,  step: 0.01 },
      ],
    },
  },

  "3D симулятор": {
  },
}