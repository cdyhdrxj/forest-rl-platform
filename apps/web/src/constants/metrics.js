import { Theme } from "./colors"

const BASE_METRICS = {
  episode:   ["Эпизод",  s => s?.episode ?? 0,                                       null],
  step:      ["Шаг",     s => s?.step ?? 0,                                           null],
  reward:    ["Награда", s => s?.total_reward != null ? s.total_reward.toFixed(1) : "0", null],
  collision: ["Столкн.", s => s?.collision_count ?? 0,                               Theme.red],
}

export const METRICS_CONFIG = {
  "Непрерывная 2D": {
    "Тропы": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
  },

  "Дискретная": {
    "Патруль": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
    "Посадка": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Посажено",  s => s?.goal_count ?? 0,                                         Theme.green],
      BASE_METRICS.collision,
      ["Покрытие",  s => s?.coverage_ratio != null ? s.coverage_ratio.toFixed(2) : "—", null],
      ["Саженцы",   s => s?.remaining_seedlings ?? "—",                              null],
    ],
  },

  "Трёхмерная": {
    "Патруль": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
    "Тропы": [
      BASE_METRICS.episode,
      BASE_METRICS.step,
      BASE_METRICS.reward,
      ["Целей", s => s?.goal_count ?? 0, Theme.green],
      BASE_METRICS.collision,
    ],
  },
}

export function getMetrics(env, task) {
  return METRICS_CONFIG[env]?.[task]
    ?? METRICS_CONFIG[env]?.[Object.keys(METRICS_CONFIG[env])[0]]
    ?? []
}