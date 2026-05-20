export const SLIDER_CONFIG = {

  "Непрерывная 2D": {

    "Тропы": {
      "Алгоритм": [
        { param: "learning_rate",     label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,  step: 0.00001 },
        { param: "gamma",             label: "Гамма (γ)",       default: 0.99,   min: 0.9,     max: 0.999, step: 0.001   },
        { param: "max_steps",         label: "Макс. шагов",     default: 240,    min: 50,      max: 1000,  step: 10      },
        { param: "tau",               label: "Тау",             default: 0.005,  min: 0.001,   max: 0.1,   step: 0.001,  algoOnly: ["SAC"] },
        { param: "goal_reward",       label: "Награда за цель", default: 50,     min: 10,      max: 100,   step: 5       },
        { param: "collision_penalty", label: "Штраф столкн.",   default: 0.3,    min: 0,       max: 5,     step: 0.1     },
        { param: "step_penalty",      label: "Штраф за шаг",    default: 0,      min: 0,       max: 1,     step: 0.01    },
        { param: "terrain_penalty",   label: "Штраф рельефа",   default: 0.03,   min: 0,       max: 1,     step: 0.01    },
      ],
      "Карта": [
        { param: "grid_size",        label: "Размер сетки", default: 12, min: 5, max: 20,  step: 1    },
        { param: "obstacle_density", label: "Препятствия",  default: 0.12, min: 0, max: 0.4, step: 0.01 },
      ],
      "Робот": [
        { param: "action_scale", default: 1.0, min: 0.1,   max: 5,    step: 0.1,   label: "Масштаб действий" },
        { param: "max_speed",    default: 50,  min: 1,     max: 200,  step: 1,     label: "Макс. скорость" },
        { param: "accel",        default: 40,  min: 1,     max: 100,  step: 1,     label: "Разгон" },
        { param: "damping",      default: 0.6, min: 0.01,  max: 0.99, step: 0.01,  label: "Торможение" },
        { param: "dt",           default: 0.01,min: 0.001, max: 0.05, step: 0.001, label: "Шаг физики" },
      ],
    },
  },

  "Дискретная": {

    "Патруль": {
      "Алгоритм": [
        { param: "learning_rate", label: "Скор. обучения", default: 0.0003, min: 0.00001, max: 0.01, step: 0.00001 },
        { param: "gamma", label: "Гамма (γ)", default: 0.99, min: 0.9, max: 0.999, step: 0.001 },
        { param: "max_steps", label: "Макс. шагов", default: 240, min: 50, max: 1000, step: 10 },
        { param: "max_value", label: "Макс. ценность", default: 1000, min: 100, max: 5000, step: 100 },
        { param: "value_density", label: "Плотность ценности", default: 0.7, min: 0, max: 1, step: 0.01 },
        { param: "intruder_detection_reward", label: "Обнаружение", default: 10, min: 0, max: 50, step: 0.5 },
        { param: "intruder_interception_reward", label: "Перехват", default: 20, min: 0, max: 100, step: 1 },
      ],

      "Агент": [
        { param: "m_block", label: "Штраф блок", default: 10, min: 0, max: 20, step: 0.5 },
        { param: "m_out", label: "Штраф выход", default: 1, min: 0, max: 5, step: 0.1 },
        { param: "m_stay", label: "Штраф стояния", default: 0, min: 0, max: 2, step: 0.05 },
        { param: "is_random_spawned", label: "Случайный спавн", default: true, type: "bool" },
      ],

      "Наблюдение": [
        { param: "obs_size", label: "Размер обзора", default: 7, min: 1, max: 9, step: 2 },
        { param: "layers_count", label: "Кол-во слоёв", default: 4, min: 1, max: 8, step: 1 },
      ],

      "Карта": [
        { param: "grid_size", label: "Размер сетки", default: 12, min: 5, max: 20, step: 1 },
        { param: "passability_low", label: "Мин. проходимость", default: 0.1, min: 0, max: 0.5, step: 0.01 },
        { param: "passability_high", label: "Макс. проходимость", default: 1.0, min: 0.5, max: 1, step: 0.01 },
        { param: "impassable_prob", label: "Непроходимость", default: 0.15, min: 0, max: 0.5, step: 0.01 },
        { param: "map_seed", label: "Seed карты", default: null, min: 0, max: 99999999, step: 1 },
        { param: "max_value", label: "Макс. ценность", default: 1000, min: 100, max: 5000, step: 100 },
        { param: "value_density", label: "Плотность ценности", default: 0.7, min: 0, max: 1, step: 0.01 },
      ],

      "Нарушитель": [
        { param: "intruder_count", label: "Кол-во нарушителей", default: 1, min: 1, max: 10, step: 1 },
        { param: "catch_reward", label: "Награда за поимку", default: 1, min: 0, max: 10, step: 0.5 },
        { param: "m_plan", label: "План ущерба", default: 1000, min: 10, max: 5000, step: 10 },
        { param: "m_defence", label: "Защита", default: 1.5, min: 0, max: 5, step: 0.1 },
        { param: "incoming_step", label: "Момент появления", default: -1, min: -1, max: 500, step: 1 },
        { param: "incoming_patience", label: "Терпение входа", default: 15, min: 5, max: 200, step: 5 },
        { param: "felling_intensity", label: "Интенсивность вырубки", default: 100, min: 0, max: 200, step: 1 },
        { param: "m_tool_power",      label: "Мощность инструмента", default: 100, min: 0,  max: 500, step: 10 },
        { param: "search_patience",   label: "Терпение поиска",      default: 50,  min: 5,  max: 200, step: 5  },
        { param: "incoming", label: "Входящий нарушитель", default: true, type: "bool" },
        { param: "intruder_is_random_spawned", label: "Случайный спавн", default: false, type: "bool" },
      ],
    },

    "Посадка": {
      "Алгоритм": [
        { param: "learning_rate",      label: "Скор. обучения",      default: 0.0003, min: 0.00001, max: 0.01, step: 0.00001 },
        { param: "gamma",              label: "Гамма (γ)",           default: 0.99,   min: 0.9,     max: 0.999, step: 0.001  },
        { param: "max_steps",          label: "Макс. шагов",         default: 240,    min: 50,      max: 1000,  step: 10     },
        { param: "step_penalty",       label: "Штраф за шаг",        default: 0,      min: 0,       max: 1,     step: 0.01   },
        { param: "alpha_plant",        label: "Награда за посадку",  default: 4.0,    min: 0.5,     max: 10,    step: 0.1    },
        { param: "alpha_quality",      label: "Вес качества",        default: 2.0,    min: 0,       max: 5,     step: 0.1    },
        { param: "beta_move",          label: "Штраф движения",      default: 0.08,   min: 0,       max: 1,     step: 0.01   },
        { param: "beta_turn",          label: "Штраф поворота",      default: 0.04,   min: 0,       max: 1,     step: 0.01   },
        { param: "beta_invalid_plant", label: "Штраф плохой посадки",default: 0.6,    min: 0,       max: 2,     step: 0.01   },
      ],
      "Карта": [
        { param: "grid_size",            label: "Размер сетки",       default: 12, min: 5,    max: 20,  step: 1    },
        { param: "obstacle_density",     label: "Препятствия",        default: 0.12,min: 0,    max: 0.4, step: 0.01 },
        { param: "plantable_density",    label: "Засаживаемость",     default: 0.7, min: 0.1,  max: 1,   step: 0.01 },
        { param: "min_plant_distance",   label: "Мин. расстояние",    default: 1,   min: 0,    max: 3,   step: 1    },
        { param: "uniformity_radius",    label: "Радиус равномерн.",  default: 1,   min: 0,    max: 3,   step: 1    },
        { param: "target_density",       label: "Целевая плотн.",     default: 0.35, min: 0.05, max: 0.8, step: 0.01 },
        { param: "lambda_uniformity",    label: "Штраф равномерн.",   default: 3.0, min: 0,    max: 10,  step: 0.1  },
        { param: "lambda_underplanting", label: "Штраф недопосадки",  default: 1.5, min: 0,    max: 10,  step: 0.1  },
      ],
      "Робот": [
        { param: "initial_seedlings", label: "Саженцев на борту", default: 30, min: 5, max: 80, step: 1    },
        { param: "beta_stay",         label: "Штраф стояния",     default: 0.12,min: 0, max: 1,  step: 0.01 },
        { param: "beta_fail_move",    label: "Штраф неудачи хода",default: 0.25,min: 0, max: 2,  step: 0.01 },
      ],
    },
  },

  "3D симулятор": {
    "Тропы": {
      "Ландшафт": [
        { param: "mesh_height_multiplayer", label: "Множитель высоты", default: 1.0, min: 0.5, max: 5, step: 0.1, type: "number" },
        { param: "noise_scale",             label: "Масштаб шума",    default: 1.0, min: 0.5, max: 5, step: 0.1, type: "number" },
        { param: "seed",                    label: "Seed ландшафта",  default: 42,  min: 0,   max: 999999, step: 1, type: "number" },
        { param: "octaves",                 label: "Октавы",           default: 4,   min: 1,   max: 8,   step: 1, type: "int" },
        { param: "lacunarity",              label: "Лакунарность",     default: 2.0, min: 1.5, max: 3.5, step: 0.1 },
        { param: "max_view_dst",            label: "Макс. дистанция обзора", default: 200, min: 50, max: 500, step: 10, type: "int" },
      ],
      "Робот": [
        { param: "robot_type",          label: "Тип робота",      type: "select", options: ["wheeled", "tracked", "legged"], default: "wheeled" },
        { param: "robot_position",      label: "Позиция робота",  type: "coordinates" }, 
        { param: "robot_rotation_y",    label: "Поворот (Y)",     default: 0, min: 0,   max: 360, step: 15, type: "int" },
      ],
      "Цель": [
        { param: "target_position",     label: "Позиция цели",    type: "coordinates" },
      ],
      "Алгоритм": [
        { param: "learning_rate",       label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,  step: 0.00001 },
        { param: "gamma",               label: "Гамма (γ)",       default: 0.99,   min: 0.9,     max: 0.999, step: 0.001 },
        { param: "max_steps",           label: "Макс. шагов",     default: 240,    min: 50,      max: 1000,  step: 10, type: "int" },
        { param: "goal_reward",         label: "Награда за цель", default: 50,     min: 10,      max: 100,   step: 5 },
        { param: "collision_penalty",   label: "Штраф столкн.",   default: 0.3,    min: 0,       max: 10,    step: 0.5 },
        { param: "step_penalty",        label: "Штраф за шаг",    default: 0,      min: 0,       max: 2,     step: 0.05 },
        { param: "terrain_penalty",     label: "Штраф рельефа",   default: 0.03,   min: 0,       max: 2,     step: 0.05 },
      ],
    },
  },
}