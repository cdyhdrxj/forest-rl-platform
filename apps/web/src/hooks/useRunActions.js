import { useCallback } from "react"
import { buildPatrolPayload } from "../constants/config" 
import { ENV, TASK } from "../constants/envs"

const modeForTask = t =>
  t === TASK.TRAIL ? "trail" : t === TASK.REFORESTATION ? "reforestation" : "patrol"

export function useRunActions({
  wsRef, endpoint, params, algo, activeTask, activeEnv,
  setRunning, setChartData, setState, setActiveGridSize,
  jsonConfig, resetEpisode, mode, sourceRunTitle,
}) {
  const isPatrol = activeEnv === ENV.DISCRETE && activeTask === TASK.PATROL

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
        ...buildPatrolPayload(params, algo),
        mode: modeForTask(activeTask),
      }
    } else {
      generateParams = { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) }
    }

    if (mode === "inference") {
      generateParams.mode = "inference"
      if (sourceRunTitle) generateParams.source_run_title = sourceRunTitle
    }

    send("generate", generateParams)
    resetEpisode?.()
    setChartData([])
    setRunning(false)
  }, [params, algo, activeTask, jsonConfig, isPatrol, send, resetEpisode, setChartData, setRunning, mode, sourceRunTitle])

  const start = useCallback(() => {
    let payloadParams
    
    if (isPatrol && jsonConfig) {
      const { _fileName, ...rest } = jsonConfig
      payloadParams = { ...rest, algorithm: algo.toLowerCase() }
    } else if (isPatrol) {
      payloadParams = buildPatrolPayload(params, algo)
    } else {
      payloadParams = { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) }
    }
   
    send("start", payloadParams)  
    
    const gridSize = (isPatrol && jsonConfig?.grid_size) ? jsonConfig.grid_size : params.grid_size
    setActiveGridSize(gridSize)
    resetEpisode?.()
    setChartData([])
    setRunning(true)
  }, [params, algo, activeTask, jsonConfig, send, resetEpisode, setActiveGridSize, setChartData, setRunning])

  const stop = useCallback(() => {
    send("stop")
    setRunning(false)
  }, [send, setRunning])

  const reset = useCallback(() => {
    if (activeEnv === ENV.CONTINUOUS) {
      send("generate", { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) })
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