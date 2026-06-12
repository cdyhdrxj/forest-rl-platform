// Параметры, поддерживаемые каждым алгоритмом
export const ALGO_SUPPORTED_PARAMS = {
  "PPO": [
    "learning_rate", "gamma", "total_timesteps", "n_envs",
    "n_steps", "batch_size", "n_epochs", "clip_range", "ent_coef",
    "use_sde", "sde_sample_freq",
  ],
  "SAC": [
    "learning_rate", "gamma", "buffer_size", "batch_size", "tau", "ent_coef",
  ],
  "A2C": [
    "learning_rate", "gamma", "n_steps", "ent_coef",
  ],
  "DQN": [
    "learning_rate", "gamma", "total_timesteps", "n_envs",
    "batch_size", "buffer_size", "learning_starts",
    "target_update_interval", "exploration_fraction", "exploration_final_eps",
  ],
  "DRQN": [
    "learning_rate", "gamma", "total_timesteps", "n_envs",
    "batch_size", "lstm_hidden_size", "unroll_length", "buffer_capacity",
    "learning_starts", "epsilon_decay_steps", "epsilon_final",
  ],
  "greedy_nearest": [],
  "greedy_two_step": [],
}

// Параметры, которые нельзя менять в режиме исполнения модели
export const LOCKED_PARAMS_FOR_INFERENCE = {
  always: ["algorithm"],
  observation: ["obs_size", "layers_count"],
  discrete: ["grid_size"],
}

// Объединение параметров всех алгоритмов — всё, что НЕ входит сюда, считается
// не-алгоритмическим (генерация сценария, среда, валидация, run-настройки) и
// сохраняется при смене алгоритма.
const ALL_ALGO_PARAMS = new Set(Object.values(ALGO_SUPPORTED_PARAMS).flat())

// Функция: фильтрация параметров при смене алгоритма.
// Отбрасываем только алго-специфичные параметры ДРУГИХ алгоритмов
// (например n_steps у PPO при переходе на DQN). Параметры генерации сценария
// и среды (grid_size, m_catch, map_seed, validation_* и т.п.) сохраняются.
export const filterParamsForAlgo = (params, newAlgo) => {
  const supported = new Set(ALGO_SUPPORTED_PARAMS[newAlgo] || [])
  const filtered = {}
  Object.keys(params).forEach(key => {
    if (supported.has(key) || !ALL_ALGO_PARAMS.has(key)) {
      filtered[key] = params[key]
    }
  })
  return filtered
}

// Функция: проверка, заблокирован ли параметр в режиме inference
export const isParamLockedForInference = (param, activeEnv, isInference) => {
  if (!isInference) return false
  
  if (LOCKED_PARAMS_FOR_INFERENCE.always.includes(param)) return true
  if (LOCKED_PARAMS_FOR_INFERENCE.observation.includes(param)) return true
  
  if (activeEnv === "Дискретная" && param === "grid_size") return true
  
  return false
}