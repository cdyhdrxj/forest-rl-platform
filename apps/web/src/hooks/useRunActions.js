import { useCallback } from "react"
import { buildPatrolPayload } from "../constants/config" 

const modeForTask = t =>
  t === "Тропы" ? "trail" : t === "Посадка" ? "reforestation" : "patrol"

export function useRunActions({
  wsRef, endpoint, params, algo, activeTask, activeEnv,
  setRunning, setChartData, setState, setActiveGridSize,
  jsonConfig, resetEpisode,
}) {
  const send = (action, extra = {}) => {
    if (!endpoint) { console.error("No endpoint"); return }
    if (!wsRef.current) { console.error("WebSocket not initialized"); return }
    if (wsRef.current.readyState !== WebSocket.OPEN) {
      console.error(`WebSocket not open, state=${wsRef.current.readyState}`); return
    }
    const message = JSON.stringify({ action, ...extra })
    console.log(`Sending ${action}:`, message)
    wsRef.current.send(message)
  }

  const generate = useCallback(() => {
    send("generate", {
      params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) },
    })
    resetEpisode?.()
    setChartData([])
    setRunning(false)
  }, [params, algo, activeTask, send, resetEpisode, setChartData, setRunning])

  const start = useCallback(() => {
    const isPatrol = activeTask === "Патруль" && activeEnv === "Дискретная"

    let payload
    if (isPatrol && jsonConfig) {
      const { _fileName, ...cleanConfig } = jsonConfig
      payload = { params: cleanConfig }
    } else if (isPatrol) {
      payload = { params: buildPatrolPayload(params, algo) }
    } else {
      payload = { params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) } }
    }

    send("start", payload)
    const gridSize = (isPatrol && jsonConfig?.grid_size) ? jsonConfig.grid_size : params.grid_size
    setActiveGridSize(gridSize)
    resetEpisode?.()
    setChartData([])
    setRunning(true)
  }, [params, algo, activeTask, activeEnv, jsonConfig, send, resetEpisode, setActiveGridSize, setChartData, setRunning])

  const stop = useCallback(() => {
    send("stop")
    setRunning(false)
  }, [send, setRunning])

  const reset = useCallback(() => {
    if (activeEnv === "Непрерывная 2D") {
      send("generate", {
        params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) },
      })
    } else {
      send("reset")
    }
    resetEpisode?.()
    setRunning(false)
    setState(null)
    setChartData([])
  }, [activeEnv, params, algo, activeTask, send, resetEpisode, setRunning, setState, setChartData])

  return { generate, start, stop, reset }
}