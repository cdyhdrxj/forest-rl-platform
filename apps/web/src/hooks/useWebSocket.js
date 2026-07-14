import { useState, useEffect, useRef } from "react"

export function useWebSocket(endpoint) {
  const [state, setState] = useState(null)
  const [chartData, setChartData] = useState([])
  const [valChartData, setValChartData] = useState([])
  const [running, setRunning] = useState(false)
  const [scenarioReady, setScenarioReady] = useState(false)
  const wsRef = useRef(null)
  const lastEpisodeRef = useRef(-1)
  const lastValStepRef = useRef(0)

  useEffect(() => {
    if (!endpoint) return

    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ action: "stop" }))
      wsRef.current.close()
    }

    setState(null)
    setScenarioReady(false)
    setRunning(false)
    setChartData([])
    setValChartData([])
    lastEpisodeRef.current = -1
    lastValStepRef.current = 0

    const ws = new WebSocket(endpoint)
    wsRef.current = ws

    ws.onmessage = e => {
      const data = JSON.parse(e.data)
      setState(data)
      setRunning(data?.execution_phase === "running" || Boolean(data?.running))
      setScenarioReady(Boolean(data?.scenario_generated && data?.run_id))
      
      const currentEpisode = data.episode ?? 0
      const lastEpisodeReward = data.last_episode_reward
      
      if (currentEpisode !== lastEpisodeRef.current && lastEpisodeReward !== undefined) {
        lastEpisodeRef.current = currentEpisode
        
        if (currentEpisode > 0) {
          setChartData(prev => {
            const newData = [...prev, { i: currentEpisode, r: lastEpisodeReward }]
            if (newData.length > 100) return newData.slice(-100)
            return newData
          })
        }
      }

      const vs = data.val_step ?? 0
      if (vs > 0 && vs !== lastValStepRef.current && data.val_metrics) {
        lastValStepRef.current = vs
        setValChartData(prev => {
          if (prev.length && prev[prev.length - 1].step === vs) return prev
          return [...prev.slice(-99), { step: vs, ...data.val_metrics }]
        })
      }
    }
    
    ws.onerror = e => console.error("ws error", e)
    return () => ws.close()
  }, [endpoint])

  const send = (action, extra = {}) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error("WebSocket not open")
      return
    }
    const message = JSON.stringify({ action, ...extra })
    console.log(`[WS] Sending ${action}:`, message)
    wsRef.current.send(message)
  }

  return { state, chartData, valChartData, running, scenarioReady, setRunning, setChartData, setValChartData, setState, wsRef, send }
}