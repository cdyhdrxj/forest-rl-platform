export const DEFAULT_PARAMS = {
  // Алгоритм
  learning_rate: 0.0003,
  gamma: 0.99,
  tau: 0.005,
  max_steps: 240,

  // Общие награды/штрафы
  goal_reward: 50.0,
  collision_penalty: 0.3,
  step_penalty: 0.0,
  terrain_penalty: 0.03,

  // Карта
  grid_size: 12,
  obstacle_density: 0.12,

  // Физика
  action_scale: 1.0,
  max_speed: 50.0,
  accel: 40.0,
  damping: 0.6,
  dt: 0.01,

  // Посадка
  plantable_density: 0.7,
  min_plant_distance: 1,
  uniformity_radius: 1,
  target_density: 0.35,
  lambda_uniformity: 3.0,
  lambda_underplanting: 1.5,
  alpha_plant: 4.0,
  alpha_quality: 2.0,
  beta_move: 0.08,
  beta_turn: 0.04,
  beta_fail_move: 0.25,
  beta_stay: 0.12,
  beta_invalid_plant: 0.6,
  initial_seedlings: 30,

  // Патруль — карта
  map_seed: null,
  passability_low: 0.1,
  passability_high: 1.0,
  impassable_prob: 0.15,
  max_value: 1000.0,
  value_density: 0.7,

  // Патруль — агент
  m_block: 10.0,
  m_out: 1.0,
  m_stay: 0.0,
  is_random_spawned: true,

  // Патруль — наблюдение
  obs_size: 7,
  layers_count: 4,

  // Патруль — нарушитель
  intruder_is_random_spawned: false,
  m_tool_power: 100.0,
  search_patience: 50,
  intruder_count: 1,
  catch_reward: 1.0,
  m_plan: 1000.0,
  m_defence: 1.5,
  felling_intensity: 100.0,
  incoming_patience: 15,
  incoming_step: -1,
  incoming: true,
  intruder_is_random_spawned: false,
  intruder_pos: [5, 5],
}

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