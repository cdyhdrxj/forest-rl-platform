export function buildPatrolPayload(params, algo) {
  return {
    algorithm: algo.toLowerCase(),

    learning_rate: params.learning_rate,
    gamma:         params.gamma,
    tau:           params.tau,

    max_steps:                    params.max_steps,
    grid_size:                    params.grid_size,
    random_spawn_position:        params.random_spawn_position ?? true,
    random_spawn_time:            params.random_spawn_time     ?? true,
    tau_min:                      params.tau_min,
    tau_max:                      params.tau_max,
    map_seed:                     params.map_seed ?? null,
    passability_low:              params.passability_low,
    passability_high:             params.passability_high,
    impassable_prob:              params.impassable_prob,
    max_value:                    params.max_value,
    value_density:                params.value_density,
    intruder_detection_reward:    params.intruder_detection_reward,
    intruder_interception_reward: params.intruder_interception_reward,

    agent_config: {
      type:              "default",
      pos:               [0, 0],
      is_random_spawned: params.is_random_spawned,
      m_block:           params.m_block,
      m_out:             params.m_out,
      m_stay:            params.m_stay,
    },

    obs_config: {
      type:         "box",
      size:         params.obs_size,
      layers_count: params.layers_count,
    },

    intruder_config: [{
      type:              "poacher_simple",
      pos:               [6, 6],
      is_random_spawned: true,
      catch_reward:      params.catch_reward,
      m_plan:            params.m_plan,
      m_defence:         params.m_defence,
      m_tool_power:      params.m_tool_power,
      search_patience:   params.search_patience,
      incoming_moment:   params.incoming_moment,
    }],
  }
}