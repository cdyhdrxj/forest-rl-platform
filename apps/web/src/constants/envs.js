export const API_PROTOCOL =
  import.meta.env.VITE_API_PROTOCOL || "http://";

export const API_WS_PROTOCOL =
  import.meta.env.VITE_API_WS_PROTOCOL || "ws://";

export const API_PORT =
  import.meta.env.VITE_API_PORT || "8000";

export const API_ADDRESS =
  import.meta.env.VITE_API_ADDRESS || "127.0.0.1";

export const ENV = {
  CONTINUOUS: "Непрерывная 2D",
  DISCRETE:   "Дискретная",
  SIM_3D:     "3D симулятор",
}

export const TASK = {
  TRAIL:         "Тропы",
  PATROL:        "Патруль",
  REFORESTATION: "Посадка",
  COVERAGE:      "Покрытие",  
}

// Задачи по среде
export const TASKS_BY_ENV = {
  [ENV.CONTINUOUS]: [TASK.TRAIL, TASK.COVERAGE],
  [ENV.DISCRETE]:   [TASK.PATROL, TASK.REFORESTATION],
  [ENV.SIM_3D]:     [TASK.TRAIL],
}

export const HTTP_MAP = {
  "WebrtcConfig":    `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}/webrtc/config`,
  "WebrtcSignaling": `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}/webrtc/signaling`,
}

export const WS_MAP = {
  [`${ENV.CONTINUOUS}/${TASK.TRAIL}`]:        `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/continuous/trail`,
  [`${ENV.CONTINUOUS}/${TASK.COVERAGE}`]:     `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/continuous/coverage`,
  [`${ENV.DISCRETE}/${TASK.PATROL}`]:         `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/discrete/patrol`,
  [`${ENV.DISCRETE}/${TASK.REFORESTATION}`]:  `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/discrete/reforestation`,
  [`${ENV.SIM_3D}/${TASK.PATROL}`]:           `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/threed/patrol`,
  [`${ENV.SIM_3D}/${TASK.TRAIL}`]:            `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/threed/trail`,
  "WebrtcWs":                                 `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/ws`,
}


export const ALGOS_BY_ROUTE = {
  [`${ENV.CONTINUOUS}/${TASK.TRAIL}`]:        ["PPO", "SAC", "A2C"],
  [`${ENV.CONTINUOUS}/${TASK.COVERAGE}`]:     ["greedy_nearest", "greedy_two_step", "PPO", "SAC", "A2C"],
  [`${ENV.DISCRETE}/${TASK.PATROL}`]:         ["PPO", "A2C"],
  [`${ENV.DISCRETE}/${TASK.REFORESTATION}`]:  ["PPO", "A2C"],
  [`${ENV.SIM_3D}/${TASK.PATROL}`]:           ["PPO", "SAC", "A2C"],
  [`${ENV.SIM_3D}/${TASK.TRAIL}`]:            ["PPO", "SAC", "A2C"],
}

export const ALGOS_BY_ENV = {
  [ENV.CONTINUOUS]: ["PPO", "SAC", "A2C"],
  [ENV.DISCRETE]:   ["PPO", "A2C"],
  [ENV.SIM_3D]:     ["PPO", "SAC", "A2C"],
}

export const CLASSIC_ALGOS = new Set(["greedy_nearest", "greedy_two_step"])