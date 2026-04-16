import { useState, useEffect, useRef } from "react"
import { buildPatrolPayload } from "../constants/config"  

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

  const send = (action, params, algo, isPatrol = false) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    let payload
    if (action === "start" && isPatrol) {
      payload = { action, ...buildPatrolPayload(params, algo) }
    } else if (action === "start") {
      payload = { action, ...params, algorithm: algo?.toLowerCase() }
    } else {
      payload = { action }
    }
    wsRef.current.send(JSON.stringify(payload))
  }

  return { state, chartData, running, scenarioReady, setRunning, setChartData, setState, wsRef, send }
}