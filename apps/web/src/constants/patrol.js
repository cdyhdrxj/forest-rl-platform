import { Theme } from "./colors"

export const PATROL_LEGEND = [
  [Theme.accent,           "Агент"],
  ["#dc2626",              "Нарушитель"],
  ["rgba(22,163,74,0.88)", "Ценная зона"],
  ["rgba(75,85,99,0.82)",  "Препятствие"],
]

export function buildPatrolPayload(params, algo) {
  return {
    algorithm: algo.toLowerCase(),

    learning_rate: params.learning_rate,
    gamma: params.gamma,
    tau: params.tau,

    max_steps: params.max_steps,
    grid_size: params.grid_size,

    map_seed: params.map_seed ?? null,

    passability_low: params.passability_low,
    passability_high: params.passability_high,
    impassable_prob: params.impassable_prob,

    max_value: params.max_value,
    value_density: params.value_density,

    agent_config: {
      type: "default",
      pos: [0, 0],
      is_random_spawned: params.is_random_spawned,  
      m_block: params.m_block,
      m_out: params.m_out,
      m_stay: params.m_stay,
    },

    obs_config: {
      type: "box",
      size: params.obs_size,
      layers_count: params.layers_count,
    },

    intruder_config: Array.from(
      { length: params.intruder_count ?? 1 },
      () => ({
        type: "poacher_simple",
        pos: params.intruder_pos ?? [5, 5],
        is_random_spawned: params.intruder_is_random_spawned ?? false,  
        catch_reward: params.catch_reward,
        m_plan: params.m_plan,
        m_defence: params.m_defence,
        m_tool_power: params.m_tool_power ?? 100.0,      
        search_patience: params.search_patience ?? 50, 
        incoming: params.incoming ?? true,
        incoming_step: params.incoming_step ?? -1,
        incoming_patience: params.incoming_patience,
        felling_intensity: params.felling_intensity ?? 100.0,
      })
    ),
  }
}