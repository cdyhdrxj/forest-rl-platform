import { Theme } from "./colors"

export const SLIDER_CONFIG = {

  "Непрерывная 2D": {
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
      { param: "grid_size",         label: "Размер сетки", min: 5, max: 20,  step: 1    },
      { param: "obstacle_density",  label: "Препятствия",  min: 0, max: 0.4, step: 0.01 },
    ],
    "Робот": [
      { param: "action_scale", label: "Масштаб действий", min: 0.1,   max: 5,    step: 0.1   },
      { param: "max_speed",    label: "Макс. скорость",   min: 1,     max: 200,  step: 1     },
      { param: "accel",        label: "Разгон",           min: 1,     max: 100,  step: 1     },
      { param: "damping",      label: "Торможение",       min: 0.01,  max: 0.99, step: 0.01  },
      { param: "dt",           label: "Шаг физики",       min: 0.001, max: 0.05, step: 0.001 },
    ],
  },

  "Дискретная": {
    "Алгоритм": [
      { param: "learning_rate",      label: "Скор. обучения",       min: 0.00001, max: 0.01,  step: 0.00001 },
      { param: "gamma",              label: "Гамма (γ)",            min: 0.9,     max: 0.999, step: 0.001   },
      { param: "max_steps",          label: "Макс. шагов",          min: 50,      max: 1000,  step: 10      },
      { param: "step_penalty",       label: "Штраф за шаг",         min: 0,       max: 1,     step: 0.01    },
      { param: "goal_reward",        label: "Награда за цель",      min: 10,      max: 100,   step: 5,      taskOnly: ["Патруль"] },
      { param: "collision_penalty",  label: "Штраф столкн.",        min: 0,       max: 5,     step: 0.1,    taskOnly: ["Патруль"] },
      { param: "alpha_plant",        label: "Награда за посадку",   min: 0.5,     max: 10,    step: 0.1,    taskOnly: ["Посадка"] },
      { param: "alpha_quality",      label: "Вес качества",         min: 0,       max: 5,     step: 0.1,    taskOnly: ["Посадка"] },
      { param: "beta_move",          label: "Штраф движения",       min: 0,       max: 1,     step: 0.01,   taskOnly: ["Посадка"] },
      { param: "beta_turn",          label: "Штраф поворота",       min: 0,       max: 1,     step: 0.01,   taskOnly: ["Посадка"] },
      { param: "beta_invalid_plant", label: "Штраф плохой посадки", min: 0,       max: 2,     step: 0.01,   taskOnly: ["Посадка"] },
    ],
    "Агент": [
      { param: "m_block",           label: "Штраф за блок",    min: 0, max: 5, step: 0.1,  taskOnly: ["Патруль"] },
      { param: "m_out",             label: "Штраф за выход",   min: 0, max: 5, step: 0.1,  taskOnly: ["Патруль"] },
      { param: "m_stay",            label: "Штраф за простой", min: 0, max: 2, step: 0.05, taskOnly: ["Патруль"] },
      { param: "is_random_spawned", label: "Случайный спавн",  type: "bool",               taskOnly: ["Патруль"] },
    ],
    "Наблюдение": [
      { param: "obs_size",      label: "Размер обзора", min: 1, max: 7, step: 1, taskOnly: ["Патруль"] },
      { param: "layers_count",  label: "Кол-во слоёв",  min: 1, max: 8, step: 1, taskOnly: ["Патруль"] },
    ],
    "Карта": [
      { param: "grid_size",            label: "Размер сетки",      min: 5,    max: 20,  step: 1    },
      { param: "obstacle_density",     label: "Препятствия",       min: 0,    max: 0.4, step: 0.01 },
      { param: "plantable_density",    label: "Засаживаемость",    min: 0.1,  max: 1,   step: 0.01, taskOnly: ["Посадка"] },
      { param: "min_plant_distance",   label: "Мин. расстояние",   min: 0,    max: 3,   step: 1,    taskOnly: ["Посадка"] },
      { param: "uniformity_radius",    label: "Радиус равномерн.", min: 0,    max: 3,   step: 1,    taskOnly: ["Посадка"] },
      { param: "target_density",       label: "Целевая плотн.",    min: 0.05, max: 0.8, step: 0.01, taskOnly: ["Посадка"] },
      { param: "lambda_uniformity",    label: "Штраф равномерн.",  min: 0,    max: 10,  step: 0.1,  taskOnly: ["Посадка"] },
      { param: "lambda_underplanting", label: "Штраф недопосадки", min: 0,    max: 10,  step: 0.1,  taskOnly: ["Посадка"] },
    ],
    "Нарушитель": [
      { param: "catch_reward",    label: "Награда за поимку",       min: 0,  max: 10,  step: 0.5,  taskOnly: ["Патруль"] },
      { param: "m_plan",          label: "Потенциальный ущерб",     min: 10, max: 500, step: 10,   taskOnly: ["Патруль"] },
      { param: "m_defence",       label: "Множитель защиты",        min: 0,  max: 5,   step: 0.1,  taskOnly: ["Патруль"] },
      { param: "search_patience", label: "Терпение поиска",         min: 10, max: 200, step: 10,   taskOnly: ["Патруль"] },
      { param: "incoming_moment", label: "Момент появления",        min: 0,  max: 50,  step: 1,    taskOnly: ["Патруль"] },
      { param: "tau_min",         label: "Мин. интервал появления", min: 1,  max: 20,  step: 1,    taskOnly: ["Патруль"] },
      { param: "tau_max",         label: "Макс. интервал появления",min: 5,  max: 50,  step: 1,    taskOnly: ["Патруль"] },
    ],
    "Робот": [
      { param: "initial_seedlings", label: "Саженцев на борту",  min: 5, max: 80, step: 1,    taskOnly: ["Посадка"] },
      { param: "beta_stay",         label: "Штраф стояния",      min: 0, max: 1,  step: 0.01, taskOnly: ["Посадка"] },
      { param: "beta_fail_move",    label: "Штраф неудачи хода", min: 0, max: 2,  step: 0.01, taskOnly: ["Посадка"] },
    ],
  },

  "Трёхмерная": {
    "Алгоритм": [
      { param: "learning_rate",     label: "Скор. обучения",  min: 0.00001, max: 0.01,  step: 0.00001 },
      { param: "gamma",             label: "Гамма (γ)",       min: 0.9,     max: 0.999, step: 0.001   },
      { param: "max_steps",         label: "Макс. шагов",     min: 50,      max: 1000,  step: 10      },
      { param: "tau",               label: "Тау",             min: 0.001,   max: 0.1,   step: 0.001,  algoOnly: ["SAC", "TD3"] },
      { param: "goal_reward",       label: "Награда за цель", min: 10,      max: 100,   step: 5       },
      { param: "collision_penalty", label: "Штраф столкн.",   min: 0,       max: 5,     step: 0.1     },
      { param: "step_penalty",      label: "Штраф за шаг",    min: 0,       max: 1,     step: 0.01    },
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
}