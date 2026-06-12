import { Theme } from "./colors"

export const PATROL_LEGEND = [
  [Theme.accent,           "Агент"],
  ["#dc2626",              "Нарушитель"],
  ["rgba(22,163,74,0.88)", "Ценная зона"],
  ["rgba(75,85,99,0.82)",  "Препятствие"],
]

// Собирает GridForestConfig для генерации сценария патрулирования.
// Структура соответствует актуальному конфигу среды (см. research-эталон
// services/patrol_planning/research/16x16_forest/test_configs/forest_16x16_v3.json):
//   - нарушитель типа "poacher_alt" (актуальные поля: m_plan, m_tool_power,
//     n_targets, use_idleness_targeting, use_passability_routing, incoming_moment);
//   - reward_config / metrics_config / mu_min / tau_* / continue_until_max_steps.
// Пользователю во вкладке «Генерировать сценарий» доступна курированная часть
// параметров; всё остальное берётся дефолтами из эталона. load_layers здесь не
// задаётся — карта генерируется процедурно по passability_*/value/seed.
export function buildPatrolPayload(params, algo) {
  const gridSize = params.grid_size ?? 16
  const maxSteps = params.max_steps ?? 256
  const maxValue = params.max_value ?? 100
  // «Число нарушителей» в UI = max_intruders: сколько появлений за эпизод
  // спланирует среда (расписание tau_min..tau_max). 0/пусто трактуем как 1.
  const maxIntruders = Math.max(1, params.intruder_count ?? 1)
  // 0 или пусто = случайная карта (seed выбирается генератором при каждой генерации).
  const mapSeed = (params.map_seed === 0 || params.map_seed == null) ? null : params.map_seed

  return {
    algorithm: algo.toLowerCase(),

    agent_config: {
      type: "default",
      pos: [
        Math.min(gridSize - 1, Math.max(0, params.agent_pos_x ?? 3)),
        Math.min(gridSize - 1, Math.max(0, params.agent_pos_y ?? 3)),
      ],
      is_random_spawned: params.agent_is_random_spawned ?? true,
      spawn_min_passability: params.spawn_min_passability ?? 1.0,
      m_block: 1.0,
      m_out: 1.0,
      m_stay: 0.0,
    },

    // Один шаблон-нарушитель (poacher_alt). Реальное число появлений за эпизод
    // задаёт max_intruders; среда спавнит их по расписанию из краёв карты, поэтому
    // начальная позиция и incoming_moment здесь не важны (n_targets фиксирован = 1).
    intruder_config: [{
      type: "poacher_alt",
      pos: [0, 0],
      is_random_spawned: false,
      manual_spawn: false,
      catch_reward: 1.0,
      m_plan: params.m_plan ?? 175.0,
      m_tool_power: params.m_tool_power ?? 2.0,
      n_targets: 1,
      use_idleness_targeting: false,
      use_passability_routing: false,
    }],

    obs_config: {
      type: "box",
      size: 5,
      layers_count: 7,
      max_value: maxValue,
      max_steps: maxSteps,
      grid_size: gridSize,
      exclude_layers: [],
      oob_value: -1.0,
    },

    max_steps: maxSteps,
    grid_size: gridSize,

    reward_config: {
      w_catch: 1.0,
      w_damage: 1.0,
      w_move: 1.0,
      w_idle: 0.1,
      idle_value_only: true,
      m_catch: params.m_catch ?? 350.0,
      m_exit_penalty: params.m_exit_penalty ?? -250.0,
      m_out: params.m_out ?? 1.0,
      m_stay: params.m_stay ?? 0.3,
      m_block: params.m_block ?? 0.5,
      use_passability_cost: true,
      detection_reward: 0.0,
      scale_detection_by_count: false,
      scale_detection_by_proximity: false,
      exploration_reward: params.exploration_reward ?? 0.1,
      useful_exp_reward: params.useful_exp_reward ?? 0.3,
      exploration_staleness_threshold: 10,
    },

    metrics_config: {
      w1: 1.0,
      w2: 1.0,
      w3: 1.0,
      m_stay: 0.005,
      idleness_value_only: true,
    },

    mu_min: 0.9,
    tau_min: params.tau_min ?? 25,
    tau_max: params.tau_max ?? 75,
    continue_until_max_steps: true,

    map_seed: mapSeed,
    passability_low: params.passability_low ?? 0.9,
    passability_high: params.passability_high ?? 0.9,
    impassable_prob: params.impassable_prob ?? 0.1,
    max_value: maxValue,
    value_density: params.value_density ?? 0.7,
    random_map: false,
    max_intruders: maxIntruders,
  }
}
