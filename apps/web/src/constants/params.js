// Параметры, поддерживаемые каждым алгоритмом
export const ALGO_SUPPORTED_PARAMS = {
  "PPO": [
    "learning_rate", "gamma", "n_steps", "batch_size", "n_epochs", 
    "clip_range", "ent_coef", "use_sde", "sde_sample_freq"
  ],
  "SAC": [
    "learning_rate", "gamma", "buffer_size", "batch_size", "tau", "ent_coef"
  ],
  "A2C": [
    "learning_rate", "gamma", "n_steps", "ent_coef"
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

// Функция: фильтрация параметров для алгоритма
export const filterParamsForAlgo = (params, newAlgo) => {
  const supported = ALGO_SUPPORTED_PARAMS[newAlgo] || []
  const filtered = {}
  Object.keys(params).forEach(key => {
    if (supported.includes(key)) {
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