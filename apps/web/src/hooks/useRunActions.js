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

export function useRunActions({
  wsRef, endpoint, params, algo, activeTask, activeEnv,
  setRunning, setChartData, setState, jsonConfig, 
  resetEpisode, mode, sourceRunTitle,
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
    if (isPatrol && jsonConfig) {
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
    setRunning(false)
  }, [params, algo, activeTask, activeEnv, jsonConfig, isPatrol, send, resetEpisode, setChartData, setRunning, mode, sourceRunTitle])

  const start = useCallback(() => {
    const paramsWithDefaults = getParamsWithDefaults(params, activeEnv, activeTask)
    
    let payloadParams
    
    if (isPatrol && jsonConfig) {
      const { _fileName, ...rest } = jsonConfig
      payloadParams = { ...rest, algorithm: algo.toLowerCase() }
    } else if (isPatrol) {
      payloadParams = buildPatrolPayload(paramsWithDefaults, algo)
    } else if (is3DSim) {
      payloadParams = buildTerrainPayload(paramsWithDefaults)
    } else {
      payloadParams = { ...paramsWithDefaults, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) }
    }
  
    send("start", payloadParams)  
    resetEpisode?.()
    setChartData([])
    setRunning(true)
  }, [params, algo, activeTask, activeEnv, jsonConfig, send, resetEpisode, setChartData, setRunning])

  const stop = useCallback(() => {
    send("stop")
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
  }, [activeEnv, params, algo, activeTask, send, resetEpisode, setRunning, setState, setChartData])
  const finish = useCallback(() => {
    send("finish", mode ? { mode } : {})
  }, [send, mode])

  return { generate, start, stop, reset, finish }
}
