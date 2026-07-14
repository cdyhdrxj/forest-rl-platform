// Параметры, поддерживаемые каждым алгоритмом
export const ALGO_SLIDER_PARAMS = {
  "PPO": [
    { param: "learning_rate", label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,  step: 0.00001 },
    { param: "gamma",         label: "Гамма (γ)",       default: 0.99,   min: 0.9,     max: 0.999, step: 0.001   },
    { param: "n_steps",       label: "Шагов на обновл.",default: 1024,   min: 64,      max: 4096,  step: 64      },
    { param: "batch_size",    label: "Размер батча",    default: 64,     min: 16,      max: 512,   step: 16      },
    { param: "n_epochs",      label: "Эпох обновления", default: 10,     min: 1,       max: 30,    step: 1       },
    { param: "clip_range",    label: "Клиппинг",        default: 0.2,    min: 0.05,    max: 0.5,   step: 0.05    },
  ],
  "SAC": [
    { param: "learning_rate", label: "Скор. обучения",  default: 0.0003,  min: 0.00001, max: 0.01,    step: 0.00001 },
    { param: "gamma",         label: "Гамма (γ)",       default: 0.99,    min: 0.9,     max: 0.999,   step: 0.001   },
    { param: "buffer_size",   label: "Размер буфера",   default: 1000000, min: 10000,   max: 2000000, step: 10000   },
    { param: "batch_size",    label: "Размер батча",    default: 256,     min: 64,      max: 1024,    step: 64      },
    { param: "tau",           label: "Тау",             default: 0.005,   min: 0.001,   max: 0.1,     step: 0.001   },
  ],
  "A2C": [
    { param: "learning_rate", label: "Скор. обучения",  default: 0.0007, min: 0.00001, max: 0.01,  step: 0.00001 },
    { param: "gamma",         label: "Гамма (γ)",       default: 0.99,   min: 0.9,     max: 0.999, step: 0.001   },
    { param: "n_steps",       label: "Шагов на обновл.",default: 5,      min: 1,       max: 50,    step: 1       },
  ],
}

// Параметры, которые нельзя менять в режиме исполнения модели
export const LOCKED_PARAMS = {
  always: ["algorithm"],
  observation: ["obs_size", "layers_count"],
  discrete: ["grid_size"],
}

// Функция: фильтрация параметров для алгоритма
export const filterParamsForAlgo = (params, newAlgo) => {
  const supported = new Set((ALGO_SLIDER_PARAMS[newAlgo] ?? []).map(s => s.param))
  return Object.fromEntries(Object.entries(params).filter(([k]) => supported.has(k)))
}

// Функция: проверка, заблокирован ли параметр в режиме inference
export const isParamLocked = (param, activeEnv) => {
  if (LOCKED_PARAMS.always.includes(param)) return true
  if (LOCKED_PARAMS.observation.includes(param)) return true
  if (activeEnv === "Дискретная" && LOCKED_PARAMS.discrete.includes(param)) return true
  return false
}