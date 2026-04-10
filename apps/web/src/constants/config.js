import { Theme } from "./colors"

// Среды и задачи 

export const TASKS_BY_ENV = {
  "Непрерывная 2D": ["Тропы"],
  "Дискретная":     ["Патруль", "Посадка"],
  "Трёхмерная":     ["Патруль", "Тропы"],
}

export const WS_MAP = {
  "Непрерывная 2D/Тропы":  "ws://127.0.0.1:8000/continuous/trail",
  "Дискретная/Патруль":    "ws://127.0.0.1:8000/discrete/patrol",
  "Дискретная/Посадка":    "ws://127.0.0.1:8000/discrete/reforestation",
  "Трёхмерная/Патруль":    "ws://127.0.0.1:8000/threed/patrol",
  "Трёхмерная/Тропы":      "ws://127.0.0.1:8000/threed/trail",
}

// Алгоритмы по среде

export const ALGOS_BY_ENV = {
  "Непрерывная 2D": ["PPO", "SAC", "TD3", "A2C"],
  "Дискретная":     ["PPO", "A2C"],
  "Трёхмерная":     ["PPO", "SAC", "TD3", "A2C"],
}

// Дефолтные параметры 

export const DEFAULT_PARAMS = {
  // Алгоритм
  learning_rate:    0.0003,
  gamma:            0.99,
  tau:              0.005,
  max_steps:        240,

  // Награды / штрафы общие
  goal_reward:       50.0,
  collision_penalty: 0.3,
  step_penalty:      0.0,
  terrain_penalty:   0.03,

  // Карта
  grid_size:        12,
  obstacle_density: 0.12,

  // Физика (camar / 3d)
  action_scale: 1.0,
  max_speed:    50.0,
  accel:        40.0,
  damping:      0.6,
  dt:           0.01,

  // Посадка — карта
  plantable_density:    0.7,
  min_plant_distance:   1,
  uniformity_radius:    1,
  target_density:       0.35,
  lambda_uniformity:    3.0,
  lambda_underplanting: 1.5,

  // Посадка — награды/штрафы
  alpha_plant:         4.0,
  alpha_quality:       2.0,
  beta_move:           0.08,
  beta_turn:           0.04,
  beta_fail_move:      0.25,
  beta_stay:           0.12,
  beta_invalid_plant:  0.6,

  // Посадка — робот
  initial_seedlings: 30,
}

// ── Слайдеры ────────────────────────────────────────────────────────────────
// algoOnly: ["SAC","TD3"] — только для этих алгоритмов
// taskOnly: ["Посадка"]   — только для этой задачи

export const SLIDER_CONFIG = {

  "Непрерывная 2D": {
    "Алгоритм": [
      { param: "learning_rate",    label: "Скор. обучения",  min: 0.00001, max: 0.01,  step: 0.00001 },
      { param: "gamma",            label: "Гамма (γ)",       min: 0.9,     max: 0.999, step: 0.001   },
      { param: "max_steps",        label: "Макс. шагов",     min: 50,      max: 1000,  step: 10      },
      { param: "tau",              label: "Тау",             min: 0.001,   max: 0.1,   step: 0.001,  algoOnly: ["SAC", "TD3"] },
      { param: "goal_reward",      label: "Награда за цель", min: 10,      max: 100,   step: 5       },
      { param: "collision_penalty",label: "Штраф столкн.",   min: 0,       max: 5,     step: 0.1     },
      { param: "step_penalty",     label: "Штраф за шаг",    min: 0,       max: 1,     step: 0.01    },
      { param: "terrain_penalty",  label: "Штраф рельефа",   min: 0,       max: 1,     step: 0.01    },
    ],
    "Карта": [
      { param: "grid_size",        label: "Размер сетки", min: 5,  max: 20,  step: 1    },
      { param: "obstacle_density", label: "Препятствия",  min: 0,  max: 0.4, step: 0.01 },
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
      { param: "learning_rate",     label: "Скор. обучения",       min: 0.00001, max: 0.01,  step: 0.00001 },
      { param: "gamma",             label: "Гамма (γ)",            min: 0.9,     max: 0.999, step: 0.001   },
      { param: "max_steps",         label: "Макс. шагов",          min: 50,      max: 1000,  step: 10      },
      { param: "step_penalty",      label: "Штраф за шаг",         min: 0,       max: 1,     step: 0.01    },
      { param: "goal_reward",       label: "Награда за цель",      min: 10,      max: 100,   step: 5,      taskOnly: ["Патруль"] },
      { param: "collision_penalty", label: "Штраф столкн.",        min: 0,       max: 5,     step: 0.1,    taskOnly: ["Патруль"] },
      { param: "alpha_plant",       label: "Награда за посадку",   min: 0.5,     max: 10,    step: 0.1,    taskOnly: ["Посадка"] },
      { param: "alpha_quality",     label: "Вес качества",         min: 0,       max: 5,     step: 0.1,    taskOnly: ["Посадка"] },
      { param: "beta_move",         label: "Штраф движения",       min: 0,       max: 1,     step: 0.01,   taskOnly: ["Посадка"] },
      { param: "beta_turn",         label: "Штраф поворота",       min: 0,       max: 1,     step: 0.01,   taskOnly: ["Посадка"] },
      { param: "beta_invalid_plant",label: "Штраф плохой посадки", min: 0,       max: 2,     step: 0.01,   taskOnly: ["Посадка"] },
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
    "Робот": [
      { param: "initial_seedlings", label: "Саженцев на борту", min: 5, max: 80, step: 1,    taskOnly: ["Посадка"] },
      { param: "beta_stay",         label: "Штраф стояния",     min: 0, max: 1,  step: 0.01, taskOnly: ["Посадка"] },
      { param: "beta_fail_move",    label: "Штраф неудачи хода",min: 0, max: 2,  step: 0.01, taskOnly: ["Посадка"] },
    ],
  },

  "Трёхмерная": {
    "Алгоритм": [
      { param: "learning_rate",    label: "Скор. обучения",  min: 0.00001, max: 0.01,  step: 0.00001 },
      { param: "gamma",            label: "Гамма (γ)",       min: 0.9,     max: 0.999, step: 0.001   },
      { param: "max_steps",        label: "Макс. шагов",     min: 50,      max: 1000,  step: 10      },
      { param: "tau",              label: "Тау",             min: 0.001,   max: 0.1,   step: 0.001,  algoOnly: ["SAC", "TD3"] },
      { param: "goal_reward",      label: "Награда за цель", min: 10,      max: 100,   step: 5       },
      { param: "collision_penalty",label: "Штраф столкн.",   min: 0,       max: 5,     step: 0.1     },
      { param: "step_penalty",     label: "Штраф за шаг",    min: 0,       max: 1,     step: 0.01    },
    ],
    "Карта": [
      { param: "grid_size",        label: "Размер сетки", min: 5,  max: 20,  step: 1    },
      { param: "obstacle_density", label: "Препятствия",  min: 0,  max: 0.4, step: 0.01 },
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

// Метрики 
const BASE_METRICS = {
  episode: ["Эпизод", s => s?.episode ?? 0, null],
  step: ["Шаг", s => s?.step ?? 0, null],
  reward: ["Награда", s => s?.total_reward != null ? s.total_reward.toFixed(1) : "0", null],
  collision: ["Столкн.", s => s?.collision_count ?? 0, Theme.red],
}

export const METRICS_CONFIG = {
  "Непрерывная 2D": {
    "Тропы": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
  },
  
  "Дискретная": {
    "Патруль": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
    "Посадка": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Посажено", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
      ["Покрытие", s => s?.coverage_ratio != null ? s.coverage_ratio.toFixed(2) : "—", null],
      ["Саженцы", s => s?.remaining_seedlings ?? "—", null],
    ],
  },
  
  "Трёхмерная": {
    "Патруль": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
    "Тропы": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
  },
}

// Получение метрик по среде и задаче
export function getMetrics(env, task) {
  return METRICS_CONFIG[env]?.[task] ?? METRICS_CONFIG[env]?.[Object.keys(METRICS_CONFIG[env])[0]] ?? []
}