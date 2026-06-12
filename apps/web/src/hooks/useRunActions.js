import { useCallback } from "react"
import { buildPatrolPayload, buildTerrainPayload, SLIDER_CONFIG } from "../constants/config"
import { ENV, TASK } from "../constants/envs"

const modeForTask = t =>
  t === TASK.TRAIL ? "trail" : t === TASK.REFORESTATION ? "reforestation" : "patrol"

// Функция для получения параметров из SLIDER_CONFIG
const getParamsWithDefaults = (params, activeEnv, activeTask) => {
  const sliders = SLIDER_CONFIG[activeEnv]?.[activeTask] ?? {}
  const result = { ...params }

  for (const category of Object.values(sliders)) {
    for (const slider of category) {
      if (result[slider.param] === undefined && slider.default !== undefined) {
        result[slider.param] = slider.default
      }
    }
  }
  return result
}

const stripFileName = (obj) => {
  if (!obj) return null
  const { _fileName, ...rest } = obj
  return rest
}

export function useRunActions({
  wsRef, endpoint, params, algo, activeTask, activeEnv,
  setRunning, setChartData, setValChartData, setState, jsonConfig,
  resetEpisode, mode, sourceRunTitle,
  useConfigFiles = false,
  algoConfigJson = null,
  envConfigJson = null,
  valEnvConfigJson = null,
  visualize = false,
  stepDelay = 0,
  useGeneratedForValidation = false,
}) {
  const isPatrol = activeEnv === ENV.DISCRETE && activeTask === TASK.PATROL
  const is3DSim = activeEnv === ENV.SIM_3D && activeTask === TASK.TRAIL

  const send = (action, extra = {}) => {
    if (!endpoint) { console.error("No endpoint"); return }
    if (!wsRef.current) { console.error("WebSocket not initialized"); return }
    if (wsRef.current.readyState !== WebSocket.OPEN) {
      console.error(`WebSocket not open, state=${wsRef.current.readyState}`)
      return
    }
    const message = JSON.stringify({ action, params: extra })
    wsRef.current.send(message)
  }

  const generate = useCallback(() => {
    const paramsWithDefaults = getParamsWithDefaults(params, activeEnv, activeTask)

    let generateParams
    if (isPatrol && useConfigFiles && envConfigJson) {
      // Используем JSON конфиг среды для генерации сценария
      generateParams = {
        ...stripFileName(envConfigJson),
        algorithm: algo.toLowerCase(),
        mode: modeForTask(activeTask),
      }
    } else if (isPatrol && jsonConfig) {
      const { _fileName, ...rest } = jsonConfig
      generateParams = {
        ...rest,
        algorithm: algo.toLowerCase(),
        mode: modeForTask(activeTask),
      }
    } else if (isPatrol) {
      generateParams = {
        ...buildPatrolPayload(paramsWithDefaults, algo),
        mode: modeForTask(activeTask),
      }
    } else if (is3DSim) {
      generateParams = {
        ...buildTerrainPayload(paramsWithDefaults),
        mode: modeForTask(activeTask),
      }
    } else {
      generateParams = { ...paramsWithDefaults, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) }
    }

    if (mode === "inference") {
      generateParams.mode = "inference"
      if (sourceRunTitle) generateParams.source_run_title = sourceRunTitle
    }

    send("generate", generateParams)
    resetEpisode?.()
    setChartData([])
    setValChartData?.([])
    setRunning(false)
  }, [params, algo, activeTask, activeEnv, jsonConfig, isPatrol, useConfigFiles, envConfigJson, send, resetEpisode, setChartData, setValChartData, setRunning, mode, sourceRunTitle])

  const start = useCallback((options = {}) => {
    const paramsWithDefaults = getParamsWithDefaults(params, activeEnv, activeTask)
    const resume = options.resume || false

    let payloadParams

    if (isPatrol && useConfigFiles) {
      // Гиперпараметры из вкладки «Алгоритм» — база для _build_algo_config,
      // когда algo_config.json не загружен (загруженный JSON имеет приоритет).
      // undefined-значения JSON.stringify не сериализует, поэтому лишние ключи
      // другого алгоритма отбрасываются автоматически.
      const algoParams = {
        learning_rate:          paramsWithDefaults.learning_rate,
        gamma:                  paramsWithDefaults.gamma,
        // PPO
        n_steps:                paramsWithDefaults.n_steps,
        n_epochs:               paramsWithDefaults.n_epochs,
        clip_range:             paramsWithDefaults.clip_range,
        ent_coef:               paramsWithDefaults.ent_coef,
        // DQN
        buffer_size:            paramsWithDefaults.buffer_size,
        target_update_interval: paramsWithDefaults.target_update_interval,
        exploration_fraction:   paramsWithDefaults.exploration_fraction,
        exploration_final_eps:  paramsWithDefaults.exploration_final_eps,
        // DRQN
        lstm_hidden_size:       paramsWithDefaults.lstm_hidden_size,
        unroll_length:          paramsWithDefaults.unroll_length,
        buffer_capacity:        paramsWithDefaults.buffer_capacity,
        epsilon_decay_steps:    paramsWithDefaults.epsilon_decay_steps,
        epsilon_final:          paramsWithDefaults.epsilon_final,
        // batch_size / learning_starts общие для DQN/DRQN/PPO
        batch_size:             paramsWithDefaults.batch_size,
        learning_starts:        paramsWithDefaults.learning_starts,
      }
      // Валидация: либо явно загруженный val-конфиг, либо тот же сгенерированный
      // сценарий (validate_on_generated). Настройки валидации передаём всегда —
      // бэкенд использует их только если строит ValidationConfig.
      const validateOnGenerated = useGeneratedForValidation && !valEnvConfigJson

      // Отправляем JSON-конфиги вместо или вместе с параметрами слайдеров
      payloadParams = {
        ...algoParams,
        algorithm: algo.toLowerCase(),
        resume,
        total_timesteps: params.total_timesteps ?? 3000000,
        seed: params.seed ?? 42,
        visualize,
        step_delay: stepDelay / 1000,
        validate_on_generated: validateOnGenerated,
        validation_seed: params.validation_seed ?? 2026,
        validation_n_episodes: params.validation_n_episodes ?? 20,
        validation_freq: params.validation_freq ?? 100000,
        ...(algoConfigJson    ? { algo_config_json:    stripFileName(algoConfigJson)    } : {}),
        ...(envConfigJson     ? { env_config_json:     stripFileName(envConfigJson)     } : {}),
        ...(valEnvConfigJson  ? { val_env_config_json: stripFileName(valEnvConfigJson)  } : {}),
      }
    } else if (isPatrol && jsonConfig) {
      const { _fileName, ...rest } = jsonConfig
      payloadParams = { ...rest, algorithm: algo.toLowerCase(), resume, visualize, step_delay: stepDelay / 1000 }
    } else if (isPatrol) {
      payloadParams = { ...buildPatrolPayload(paramsWithDefaults, algo), resume, visualize, step_delay: stepDelay / 1000 }
    } else if (is3DSim) {
      payloadParams = { ...buildTerrainPayload(paramsWithDefaults), resume }
    } else {
      payloadParams = { ...paramsWithDefaults, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask), resume }
    }

    send("start", payloadParams)
    resetEpisode?.()
    setChartData([])
    setValChartData?.([])
    setRunning(true)
  }, [params, algo, activeTask, activeEnv, jsonConfig, isPatrol, is3DSim, useConfigFiles, algoConfigJson, envConfigJson, valEnvConfigJson, visualize, stepDelay, useGeneratedForValidation, send, resetEpisode, setChartData, setValChartData, setRunning])

  const stop = useCallback(() => {
      send("stop", {})
      setRunning(false)
  }, [send, setRunning])

  const reset = useCallback(() => {
    const paramsWithDefaults = getParamsWithDefaults(params, activeEnv, activeTask)

    if (activeEnv === ENV.CONTINUOUS) {
      send("generate", { ...paramsWithDefaults, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) })
    } else {
      send("reset")
    }
    resetEpisode?.()
    setRunning(false)
    setState(null)
    setChartData([])
    setValChartData?.([])
  }, [activeEnv, params, algo, activeTask, send, resetEpisode, setRunning, setState, setChartData, setValChartData])

  const finish = useCallback(() => {
    send("finish", mode ? { mode } : {})
  }, [send, mode])

  return { generate, start, stop, reset, finish }
}
