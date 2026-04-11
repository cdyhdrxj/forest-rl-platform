import { useState, useEffect, useRef } from "react"

export function useWebSocket(endpoint) {
  const [state,         setState]         = useState(null)
  const [chartData,     setChartData]     = useState([])
  const [running,       setRunning]       = useState(false)
  const [scenarioReady, setScenarioReady] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!endpoint) return

    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: "stop" }))
      wsRef.current.close()
    }

    setState(null)
    setChartData([])
    setScenarioReady(false)
    setRunning(false)

    const ws = new WebSocket(endpoint)
    wsRef.current = ws

    ws.onmessage = e => {
      const data = JSON.parse(e.data)
      setState(data)
      setRunning(data?.execution_phase === "running" || Boolean(data?.running))
      setScenarioReady(Boolean(data?.scenario_generated && data?.run_id))
      if (data.new_episode) {
        setChartData(prev => {
          const i = Math.max(0, (data.episode ?? 1) - 1)
          if (prev.length && prev[prev.length - 1].i === i) return prev
          return [...prev.slice(-99), { i, r: data.last_episode_reward ?? 0 }]
        })
      }
    }
    ws.onerror = e => console.error("ws error", e)
    return () => ws.close()
  }, [endpoint])

  return { state, chartData, running, scenarioReady, setRunning, setChartData, setState, wsRef }
}