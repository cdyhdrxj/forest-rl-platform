import { useCallback } from "react"

const modeForTask = t =>
  t === "Тропы" ? "trail" : t === "Посадка" ? "reforestation" : "patrol"

export function useRunActions({
  wsRef, endpoint, params, algo, activeTask, activeEnv,
  setRunning, setChartData, setState, setActiveGridSize,
}) {
  const send = (action, extra = {}) => {
    if (!endpoint) return
    wsRef.current?.send(JSON.stringify({ action, ...extra }))
  }

  const generate = useCallback(() => {
    send("generate", {
      params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) },
    })
    setChartData([])
    setRunning(false)
  }, [endpoint, params, algo, activeTask])

  const start = useCallback(() => {
    send("start", {
      params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) },
    })
    setActiveGridSize(params.grid_size)
    setChartData([])
    setRunning(true)
  }, [endpoint, params, algo, activeTask])

  const stop = useCallback(() => {
    send("stop")
    setRunning(false)
  }, [endpoint])

  const reset = useCallback(() => {
    if (activeEnv === "Непрерывная 2D") {
      // для CAMAR сброс = новая карта с новым seed
      send("generate", {
        params: { ...params, algorithm: algo.toLowerCase(), mode: modeForTask(activeTask) },
      })
    } else {
      send("reset")
    }
    setRunning(false)
    setState(null)
    setChartData([])
  }, [activeEnv, endpoint, params, algo, activeTask])

  return { generate, start, stop, reset }
}