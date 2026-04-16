export const API_PROTOCOL =
  import.meta.env.VITE_API_PROTOCOL ||
  "http://";

export const API_WS_PROTOCOL =
  import.meta.env.VITE_API_WS_PROTOCOL ||
  "ws://";

export const API_PORT = 
  import.meta.env.VITE_API_PORT ||
  "8000";

export const API_ADDRESS =
  import.meta.env.VITE_API_ADDRESS ||
  "127.0.0.1";

// Среды и задачи 
export const TASKS_BY_ENV = {
  "Непрерывная 2D": ["Тропы"],
  "Дискретная":     ["Патруль", "Посадка"],
  "Трёхмерная":     ["Патруль", "Тропы"],
}

export const HTTP_MAP = {
  "WebrtcConfig": `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}/webrtc/config`,
  "WebrtcSignaling": `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}/webrtc/signaling`
}

export const WS_MAP = {
  "Непрерывная 2D/Тропы":  `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/continuous/trail`,
  "Дискретная/Патруль":    `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/discrete/patrol`,
  "Дискретная/Посадка":    `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/discrete/reforestation`,
  "Трёхмерная/Патруль":    `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/threed/patrol`,
  "Трёхмерная/Тропы":      `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/threed/trail`,

  "WebrtcWs":      `${API_WS_PROTOCOL}${API_ADDRESS}:${API_PORT}/ws`,
}

// Алгоритмы по среде

export const ALGOS_BY_ENV = {
  "Непрерывная 2D": ["PPO", "SAC", "A2C"],
  "Дискретная":     ["PPO", "A2C"],
  "Трёхмерная":     ["PPO", "SAC", "A2C"],
}
