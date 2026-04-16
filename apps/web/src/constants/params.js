export const DEFAULT_PARAMS = {
  // Алгоритм
  learning_rate: 0.0003,
  gamma:         0.99,
  tau:           0.005,
  max_steps:     240,

  // Общие награды/штрафы
  goal_reward:       50.0,
  collision_penalty: 0.3,
  step_penalty:      0.0,
  terrain_penalty:   0.03,

  // Карта
  grid_size:        12,
  obstacle_density: 0.12,

  // Физика
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

  // Посадка — награды
  alpha_plant:        4.0,
  alpha_quality:      2.0,
  beta_move:          0.08,
  beta_turn:          0.04,
  beta_fail_move:     0.25,
  beta_stay:          0.12,
  beta_invalid_plant: 0.6,

  // Посадка — робот
  initial_seedlings: 30,

  // Патруль — среда
  intruder_detection_reward:    1.0,
  intruder_interception_reward: 1.5,
  random_spawn_position:        true,
  random_spawn_time:            true,
  tau_min:          5,
  tau_max:          10,
  map_seed:         null,
  passability_low:  0.1,
  passability_high: 1.0,
  impassable_prob:  0.15,
  max_value:        1000.0,
  value_density:    0.7,

  // Патруль — агент 
  m_block:           1.0,
  m_out:             1.0,
  m_stay:            0.0,
  is_random_spawned: false,

  // Патруль — наблюдение 
  obs_size:      3,
  layers_count:  2,

  // Патруль — нарушитель 
  catch_reward:    1.0,
  m_plan:          100.0,
  m_defence:       1.5,
  m_tool_power:    100.0,
  search_patience: 50,
  incoming_moment: 10,
}