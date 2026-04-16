import { useCallback } from "react"
import { buildPatrolPayload } from "../constants/config" 

const modeForTask = t =>
  t === "Тропы" ? "trail" : t === "Посадка" ? "reforestation" : "patrol"

export function useRunActions({
  wsRef, endpoint, params, algo, activeTask, activeEnv,
  setRunning, setChartData, setState, setActiveGridSize,
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
    setChartData([])
    setRunning(false)
  }, [params, algo, activeTask, send, setChartData, setRunning])

  const start = useCallback(() => {
    const isPatrol = activeTask === "Патруль" && activeEnv === "Дискретная"

    const payload = isPatrol
      ? { params: buildPatrolPayload(params, algo) }      
      : { params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) } }

    send("start", payload)
    setActiveGridSize(params.grid_size)
    setChartData([])
    setRunning(true)
  }, [params, algo, activeTask, activeEnv, send, setActiveGridSize, setChartData, setRunning])

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
    setRunning(false)
    setState(null)
    setChartData([])
  }, [activeEnv, params, algo, activeTask, send, setRunning, setState, setChartData])

  return { generate, start, stop, reset }
}