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
  "DQN": [
    { param: "learning_rate",          label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,  step: 0.00001 },
    { param: "gamma",                  label: "Гамма (γ)",       default: 0.999,  min: 0.9,     max: 0.9999, step: 0.0001 },
    { param: "batch_size",             label: "Батч",            default: 256,    min: 32,      max: 512,    step: 32,   type: "int" },
    { param: "buffer_size",            label: "Размер буфера",   default: 750000, min: 10000,   max: 2000000,step: 10000, type: "int" },
    { param: "learning_starts",        label: "Старт обучения",  default: 25000,  min: 1000,   max: 100000, step: 1000,  type: "int" },
    { param: "target_update_interval", label: "Обновл. цели",    default: 8000,   min: 500,    max: 20000,  step: 500,   type: "int" },
    { param: "exploration_fraction",   label: "Доля исследования", default: 0.45, min: 0.05,  max: 0.9,    step: 0.05 },
    { param: "exploration_final_eps",  label: "Финал. ε",        default: 0.05,   min: 0.01,   max: 0.2,    step: 0.01 },
  ],
  "DRQN": [
    { param: "learning_rate",        label: "Скор. обучения",  default: 0.0003, min: 0.00001, max: 0.01,   step: 0.00001 },
    { param: "gamma",                label: "Гамма (γ)",       default: 0.999,  min: 0.9,     max: 0.9999, step: 0.0001 },
    { param: "batch_size",           label: "Батч",            default: 64,     min: 16,      max: 256,    step: 16,   type: "int" },
    { param: "lstm_hidden_size",     label: "LSTM размер",     default: 256,    min: 64,      max: 512,    step: 64,   type: "int" },
    { param: "unroll_length",        label: "Длина BPTT",      default: 25,     min: 5,       max: 100,    step: 5,    type: "int" },
    { param: "buffer_capacity",      label: "Ёмкость буфера",  default: 75000,  min: 5000,    max: 300000, step: 5000,  type: "int" },
    { param: "learning_starts",      label: "Старт обучения",  default: 5000,   min: 500,     max: 50000,  step: 500,   type: "int" },
    { param: "epsilon_decay_steps",  label: "Затух. ε (шагов)", default: 300000, min: 50000,  max: 1000000,step: 50000, type: "int" },
    { param: "epsilon_final",        label: "Финал. ε",        default: 0.05,   min: 0.01,    max: 0.2,    step: 0.01 },
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